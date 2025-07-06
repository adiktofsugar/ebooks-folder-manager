from dataclasses import asdict, dataclass, field
import hashlib
import logging
from pathlib import Path
import shutil
import tempfile
from typing import List
import yaml
from efm.action import ALL_ACTIONS
from efm.config import Config, get_closest_config
from efm.metadata import Metadata, get_metadata

logger = logging.getLogger(__name__)


@dataclass
class TransactionResult:
    """Base class for transaction results"""
    
    @classmethod
    def from_file(cls, filepath: Path):
        return cls.from_dict(yaml.safe_load(filepath.read_text()))
    @classmethod
    def from_dict(cls, d: dict):
        # Determine which subclass to use based on presence of error field
        if d.get("error", False):
            # Remove the error field before passing to constructor
            d.pop("error")
            if "original_filepath" in d:
                d["original_filepath"] = Path(d["original_filepath"])
            if "temp_directory" in d and d["temp_directory"]:
                d["temp_directory"] = Path(d["temp_directory"])
            return TransactionError(**d)
        else:
            # Remove the error field if present
            d.pop("error", None)
            # Handle path conversions
            if "filename" in d:
                d["filename"] = Path(d["filename"])
            if "original_filepath" in d:
                d["original_filepath"] = Path(d["original_filepath"])
            return TransactionSuccess(**d)
    
    def to_dict(self):
        return asdict(self)
    
    def to_file(self, filepath: Path):
        filepath.parent.mkdir(parents=True, exist_ok=True)
        filepath.write_text(yaml.safe_dump(self.to_dict()))


@dataclass
class TransactionSuccess(TransactionResult):
    # filename is the relative path to the output (book) file
    filename: Path
    metadata: Metadata | None
    hash: str
    original_filepath: Path
    messages: List[str] = field(default_factory=list)
    
    def to_dict(self):
        d = super().to_dict()
        d["filename"] = str(self.filename)
        d["original_filepath"] = str(self.original_filepath)
        d["error"] = False
        return d


@dataclass
class TransactionError(TransactionResult):
    error_message: str
    original_filepath: Path
    temp_directory: Path | None = None
    messages: List[str] = field(default_factory=list)
    
    def to_dict(self):
        d = super().to_dict()
        d["error"] = True
        d["original_filepath"] = str(self.original_filepath)
        if self.temp_directory:
            d["temp_directory"] = str(self.temp_directory)
        return d


class TransactionLogHandler(logging.Handler):
    def __init__(self):
        super().__init__()
        self.messages: List[str] = []
    
    def emit(self, record):
        msg = self.format(record)
        self.messages.append(msg)

    def clear(self):
        self.messages = []


class Transaction:
    config: Config | None
    original_filepath: Path
    site_dirpath: Path
    messages: List[str]

    def __init__(
        self,
        original_filepath: Path,
        site_dir: Path,
    ):
        self.config = get_closest_config(original_filepath.parent)
        self.original_filepath = original_filepath
        self.site_dirpath = site_dir
        self.messages = []

    def perform(self) -> TransactionResult:
        
        log_handler = TransactionLogHandler()
        log_formatter = logging.Formatter(
            '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
        )
        log_handler.setFormatter(log_formatter)
        log_handler.setLevel(0)
        root_logger = logging.getLogger()
        root_level = root_logger.level
        root_handler_to_level = dict()
        for h in root_logger.handlers:
            root_handler_to_level[h] = h.level
            h.setLevel(root_level)
        root_logger.addHandler(log_handler)
        root_logger.setLevel(logging.DEBUG)

    
        cache_dirpath = self.site_dirpath / "_cache"
        
        with open(self.original_filepath, "rb") as f:
            hash = hashlib.blake2b(f.read(), digest_size=20).hexdigest()
        cached_result_filepath = cache_dirpath / f"{hash}.yaml"
        if cached_result_filepath.exists():
            logger.debug(
                f"Skipping {self.original_filepath} because metadata has already been processed."
            )
            result = TransactionResult.from_file(cached_result_filepath)
            # Add any log messages that were captured
            result.messages = log_handler.messages
            return result
        books_output_dirpath = self.site_dirpath / "books"
        temp_dirpath = Path(tempfile.mkdtemp(prefix=hash))
        try:
            filepath = Path(shutil.copy(self.original_filepath, temp_dirpath))
            metadata = get_metadata(filepath)
            
            logger.debug(f"Processing {self.original_filepath} in {temp_dirpath}")
            for ActionKlass in ALL_ACTIONS:
                action = ActionKlass(
                    self.config,
                    metadata,
                    filepath,
                    temp_dirpath,
                )

                logger.debug(f"Performing action {action.id} on {filepath}")
                filepath = action.perform()
                metadata = action.metadata  # sometimes actions update metadata

            output_filename = f"{self.original_filepath.stem}{filepath.suffix}"
            if metadata:
                output_filename = f"{metadata.author}-{metadata.title}{filepath.suffix}"

            books_output_dirpath.mkdir(parents=True, exist_ok=True)
            book_output_filepath = books_output_dirpath / output_filename
            shutil.copy(filepath, book_output_filepath)
            shutil.rmtree(temp_dirpath)
            logger.debug(
                f"Finished processing '{self.original_filepath}'. Output file is '{book_output_filepath}'"
            )

            result = TransactionSuccess(
                filename=book_output_filepath.relative_to(self.site_dirpath),
                metadata=metadata,
                hash=hash,
                original_filepath=self.original_filepath,
                messages=log_handler.messages
            )
            result.to_file(cached_result_filepath)
            return result
        except Exception as e:
            logger.exception(e)
            logger.error(
                f"Failed to process {self.original_filepath}. Intermediate files are in {temp_dirpath}"
            )
            
            # Return an error result instead of raising
            result = TransactionError(
                error_message=str(e),
                original_filepath=self.original_filepath,
                temp_directory=temp_dirpath,
                messages=log_handler.messages
            )
            
            # Still save the error result to cache so we don't retry failed conversions
            result.to_file(cached_result_filepath)
                
            return result
        finally:
            root_logger.removeHandler(log_handler)
            for h in root_logger.handlers:
                h.setLevel(root_handler_to_level.get(h, root_level))
            root_logger.setLevel(root_level)
