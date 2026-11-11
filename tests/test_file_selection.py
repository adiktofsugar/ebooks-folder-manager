import tempfile
from pathlib import Path

from efm.file_selection import get_files_from_dir, matches_filter


class TestMatchesFilter:
    def test_literal_match(self):
        file = Path("/home/user/test.txt")
        assert matches_filter(file, "test") is True
        assert matches_filter(file, "notfound") is False

    def test_regex_match(self):
        file = Path("/home/user/test123.txt")
        assert matches_filter(file, r"test\d+") is True
        assert matches_filter(file, r"test\d{4}") is False

    def test_glob_pattern(self):
        file = Path("/home/user/test.txt")
        assert matches_filter(file, "*.txt") is True
        assert matches_filter(file, "*.pdf") is False
        assert matches_filter(file, "test.*") is True

    def test_negative_filter_with_exclamation(self):
        file = Path("/home/user/test.txt")
        assert matches_filter(file, "!*.pdf") is True
        assert matches_filter(file, "!*.txt") is False
        assert matches_filter(file, "!test") is False

    def test_negative_filter_with_dash(self):
        file = Path("/home/user/test.txt")
        assert matches_filter(file, "-*.pdf") is True
        assert matches_filter(file, "-*.txt") is False
        assert matches_filter(file, "-test") is False

    def test_invalid_regex_falls_back_to_literal(self):
        file = Path("/home/user/[test].txt")
        # Invalid regex "[test" should fall back to literal string match
        assert matches_filter(file, "[test") is True
        assert matches_filter(file, "[notfound") is False


class TestMatchesFilterWithRegexFirst:
    """Test with use_regex_first=True to see different behavior"""

    def test_glob_vs_regex_priority(self):
        # Test regex patterns that don't match as substring but do as regex
        file = Path("/home/user/test123.txt")

        # Pattern with regex metacharacters
        assert (
            matches_filter(file, r"test\d+", use_regex_first=False) is True
        )  # no substring, no glob, tries regex
        assert (
            matches_filter(file, r"test\d+", use_regex_first=True) is True
        )  # regex first

        # Pattern where order actually matters - using ^ anchor
        filepath2 = Path("/home/user/readme.txt")
        # ^/home matches at start of string only
        assert (
            matches_filter(filepath2, "^/home", use_regex_first=False) is True
        )  # tries regex eventually
        assert (
            matches_filter(filepath2, "^/home", use_regex_first=True) is True
        )  # regex first

    def test_common_patterns(self):
        # For patterns where glob and regex differ significantly
        # Let's use a case where the pattern is NOT a substring

        # Pattern with glob magic (*) that Python glob.match needs full pattern
        file = Path("/home/user/test_file.txt")
        # This has glob magic so tries glob.match which fails, then tries regex which succeeds
        assert (
            matches_filter(file, r"test.*\.txt$", use_regex_first=False) is True
        )  # glob fails, then regex succeeds
        assert (
            matches_filter(file, r"test.*\.txt$", use_regex_first=True) is True
        )  # regex succeeds first

        # Better example - valid regex pattern
        filepath2 = Path("/home/user/test_file.txt")
        assert (
            matches_filter(filepath2, r"test.*file", use_regex_first=False) is True
        )  # no substring, eventually tries regex
        assert (
            matches_filter(filepath2, r"test.*file", use_regex_first=True) is True
        )  # regex first

        # Pattern where glob has magic but regex would match differently
        # Using a file where "*.py" is NOT a substring
        filepath3 = Path("/home/user/script.py")
        assert (
            matches_filter(filepath3, "*.py", use_regex_first=False) is True
        )  # glob match (ends with .py)
        # When use_regex_first=True, "*.py" as regex means "any char followed by 'py'"
        # But it fails as regex due to invalid syntax, then tries glob
        assert matches_filter(filepath3, "*.py", use_regex_first=True) is True

    def test_character_class_differences(self):
        # Test where substring doesn't match but patterns do
        file = Path("/home/user/b_file.txt")

        # Pattern that works as regex but not glob (glob needs full match)
        assert (
            matches_filter(file, "[abc]_file", use_regex_first=False) is True
        )  # glob fails, tries regex
        assert (
            matches_filter(file, "[abc]_file", use_regex_first=True) is True
        )  # regex matches


class TestGetFilesFromDir:
    def test_no_filters_returns_all_files(self):
        with tempfile.TemporaryDirectory() as tmp_dirpath:
            tmp_dir = Path(tmp_dirpath)

            # Create test files
            (tmp_dir / "file1.txt").write_text("content1")
            (tmp_dir / "file2.pdf").write_text("content2")

            # Create subdirectory with files
            sub_dir = tmp_dir / "subdir"
            sub_dir.mkdir()
            (sub_dir / "file3.doc").write_text("content3")

            files = get_files_from_dir(tmp_dir, None)
            assert len(files) == 3
            assert all(file.is_file() for file in files)

    def test_single_include_filter(self):
        with tempfile.TemporaryDirectory() as tmp_dirpath:
            tmp_dir = Path(tmp_dirpath)

            (tmp_dir / "test1.txt").write_text("content")
            (tmp_dir / "test2.pdf").write_text("content")
            (tmp_dir / "other.txt").write_text("content")

            files = get_files_from_dir(tmp_dir, ["test"])
            assert len(files) == 2
            assert all("test" in file.name for file in files)

    def test_glob_filter(self):
        with tempfile.TemporaryDirectory() as tmp_dirpath:
            tmp_dir = Path(tmp_dirpath)

            (tmp_dir / "file1.txt").write_text("content")
            (tmp_dir / "file2.txt").write_text("content")
            (tmp_dir / "file3.pdf").write_text("content")

            files = get_files_from_dir(tmp_dir, ["*.txt"])
            assert len(files) == 2
            assert all(file.suffix == ".txt" for file in files)

    def test_negative_filter(self):
        with tempfile.TemporaryDirectory() as tmp_dirpath:
            tmp_dir = Path(tmp_dirpath)

            (tmp_dir / "file1.txt").write_text("content")
            (tmp_dir / "file2.pdf").write_text("content")
            (tmp_dir / "file3.doc").write_text("content")

            files = get_files_from_dir(tmp_dir, ["!*.txt"])
            assert len(files) == 2
            assert all(file.suffix != ".txt" for file in files)

    def test_multiple_filters_applied_in_order(self):
        with tempfile.TemporaryDirectory() as tmp_dirpath:
            tmp_dir = Path(tmp_dirpath)

            (tmp_dir / "test1.js").write_text("content")
            (tmp_dir / "test2.txt").write_text("content")
            (tmp_dir / "dogs.js").write_text("content")
            (tmp_dir / "dogs.txt").write_text("content")
            (tmp_dir / "cats.txt").write_text("content")

            # Example from docstring: ["!*.js", "dogs"]
            files = get_files_from_dir(tmp_dir, ["!*.js", "dogs"])
            assert len(files) == 1
            assert files[0].name == "dogs.txt"

    def test_regex_filter(self):
        with tempfile.TemporaryDirectory() as tmp_dirpath:
            tmp_dir = Path(tmp_dirpath)

            (tmp_dir / "test123.txt").write_text("content")
            (tmp_dir / "test456.txt").write_text("content")
            (tmp_dir / "test.txt").write_text("content")
            (tmp_dir / "other789.txt").write_text("content")

            files = get_files_from_dir(tmp_dir, [r"test\d+"])
            assert len(files) == 2
            assert all(
                "test" in file.name and any(c.isdigit() for c in file.name)
                for file in files
            )

    def test_nested_directories(self):
        with tempfile.TemporaryDirectory() as tmp_dirpath:
            tmp_dir = Path(tmp_dirpath)

            # Create nested structure
            (tmp_dir / "file1.txt").write_text("content")

            sub1_dir = tmp_dir / "subdir1"
            sub1_dir.mkdir()
            (sub1_dir / "file2.txt").write_text("content")

            sub2_dir = sub1_dir / "subdir2"
            sub2_dir.mkdir()
            (sub2_dir / "file3.txt").write_text("content")
            (sub2_dir / "file4.pdf").write_text("content")

            files = get_files_from_dir(tmp_dir, ["*.txt"])
            assert len(files) == 3
            assert all(file.suffix == ".txt" for file in files)

    def test_empty_directory(self):
        with tempfile.TemporaryDirectory() as tmp_dirpath:
            tmp_dir = Path(tmp_dirpath)
            files = get_files_from_dir(tmp_dir, None)
            assert files == []

    def test_empty_filters_list_returns_all(self):
        with tempfile.TemporaryDirectory() as tmp_dirpath:
            tmp_dir = Path(tmp_dirpath)
            (tmp_dir / "file1.txt").write_text("content")
            (tmp_dir / "file2.pdf").write_text("content")

            files = get_files_from_dir(tmp_dir, [])
            assert len(files) == 2

    def test_complex_filter_combination(self):
        with tempfile.TemporaryDirectory() as tmp_dirpath:
            tmp_dir = Path(tmp_dirpath)

            (tmp_dir / "report_2023.pdf").write_text("content")
            (tmp_dir / "report_2024.pdf").write_text("content")
            (tmp_dir / "report_2024.txt").write_text("content")
            (tmp_dir / "summary_2024.pdf").write_text("content")
            (tmp_dir / "data.csv").write_text("content")

            # Want: PDF files with "report" in name but not from 2023
            files = get_files_from_dir(tmp_dir, ["*.pdf", "report", "!2023"])
            assert len(files) == 1
            assert files[0].name == "report_2024.pdf"
