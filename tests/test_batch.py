from io import StringIO
from rich.console import Console
from efm.batch import BatchSummary, SummaryCategory


def test_batch_summary_with_custom_categories():
    """Test BatchSummary with custom categories including success and error cases."""
    # Create custom categories
    Processed = SummaryCategory(name="processed", color="green", icon="✅")
    Failed = SummaryCategory(name="failed", color="red", icon="❌", is_error=True)
    Skipped = SummaryCategory(name="skipped", color="yellow", icon="⏭")

    # Create summary with custom categories
    summary = BatchSummary(categories=[Processed, Failed, Skipped])

    # Add some results
    summary.add_result("book1.pdf", category=Processed, result={"title": "Book One"})
    summary.add_result("book2.epub", category=Failed, error="Corrupt file header")
    summary.add_result("book3.mobi", category=Failed, error="DRM protected")
    summary.add_result("book4.azw", category=Skipped, result=None)
    summary.add_result("book5.pdf", category=Processed, result={"title": "Book Five"})

    # Capture print output without ANSI codes
    output = StringIO()
    console = Console(file=output, force_terminal=False, width=80)
    summary.print(console)

    actual = output.getvalue()

    expected = """
Total: 5
  ✅ 2 processed
  ❌ 2 failed
  ⏭ 1 skipped

failed:
  - book2.epub: Corrupt file header
  - book3.mobi: DRM protected
"""

    assert actual == expected


def test_batch_summary_no_errors():
    """Test BatchSummary when there are no error results."""
    Success = SummaryCategory(name="success", color="green", icon="✓")
    Warning = SummaryCategory(name="warning", color="yellow", icon="⚠")

    summary = BatchSummary(categories=[Success, Warning])

    summary.add_result("file1.txt", category=Success, result="processed")
    summary.add_result("file2.txt", category=Warning, result="processed with warnings")

    # Capture print output without ANSI codes
    output = StringIO()
    console = Console(file=output, force_terminal=False, width=80)
    summary.print(console)

    actual = output.getvalue()

    expected = """
Total: 2
  ✓ 1 success
  ⚠ 1 warning
"""

    assert actual == expected


def test_batch_summary_iteration():
    """Test iterating over results and filtering by category."""
    Success = SummaryCategory(name="success", color="green", icon="✓")
    Failed = SummaryCategory(name="failed", color="red", icon="✗", is_error=True)

    summary = BatchSummary(categories=[Success, Failed])

    # Add results
    summary.add_result("file1.txt", category=Success, result="result1")
    summary.add_result("file2.txt", category=Failed, result=None, error="Error message")
    summary.add_result("file3.txt", category=Success, result="result3")

    # Test iteration
    all_results = list(summary)
    assert len(all_results) == 3
    assert all_results[0].name == "file1.txt"
    assert all_results[0].result == "result1"
    assert all_results[1].name == "file2.txt"
    assert all_results[1].error == "Error message"

    # Test filtering
    success_results = summary.filter_by_category(Success)
    assert len(success_results) == 2
    assert success_results[0].name == "file1.txt"
    assert success_results[1].name == "file3.txt"

    failed_results = summary.filter_by_category(Failed)
    assert len(failed_results) == 1
    assert failed_results[0].name == "file2.txt"
    assert failed_results[0].error == "Error message"
