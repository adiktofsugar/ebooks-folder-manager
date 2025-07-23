from typing import Iterator
from dataclasses import dataclass, field
from rich.console import Console


@dataclass(frozen=True)
class SummaryCategory:
    """Defines a category with its display properties."""

    name: str
    color: str = ""
    icon: str = "•"
    is_error: bool = False


# Pre-defined common categories
Success = SummaryCategory(name="success", color="green", icon="✓")
Failed = SummaryCategory(name="failed", color="red", icon="✗", is_error=True)
Error = SummaryCategory(name="error", color="red", icon="✗", is_error=True)
Warning = SummaryCategory(name="warning", color="yellow", icon="⚠")
Skipped = SummaryCategory(name="skipped", color="dim", icon="⊘")
Duplicated = SummaryCategory(name="duplicated", color="yellow", icon="≡")


@dataclass
class BatchSummaryResult[Result]:
    """Represents a single result with its categories."""

    name: str
    result: Result
    categories: dict[SummaryCategory, bool] = field(default_factory=dict)
    error: str | None = None

    def has_category(self, category: SummaryCategory) -> bool:
        """Check if this result belongs to a category."""
        return self.categories.get(category, False)


class BatchSummary[Result]:
    """Tracks results and statistics for batch processing operations."""

    def __init__(self, categories: list[SummaryCategory]):
        self.categories = categories
        self.results: list[BatchSummaryResult[Result]] = []
        self._category_counts: dict[SummaryCategory, int] = {
            cat: 0 for cat in categories
        }

    def add_result(
        self,
        name: str,
        category: SummaryCategory,
        result: Result = None,
        error: str | None = None,
    ):
        """Add a result with its category.

        Args:
            name: Identifier for this item
            category: The SummaryCategory this result belongs to
            result: The actual processing result
            error: Optional error message
        """
        # Ensure category is one of the configured categories
        if category not in self.categories:
            raise ValueError(
                f"Category '{category.name}' not configured for this BatchSummary"
            )

        # Create categories dict with only the specified category set to True
        categories = {cat: (cat == category) for cat in self.categories}

        # Update count for the specified category
        self._category_counts[category] += 1

        self.results.append(
            BatchSummaryResult(
                name=name, result=result, categories=categories, error=error
            )
        )

    def count(self, category: SummaryCategory) -> int:
        """Get count for a specific category."""
        return self._category_counts.get(category, 0)

    @property
    def total(self) -> int:
        """Total number of processed items."""
        return len(self.results)

    def __iter__(self) -> Iterator[BatchSummaryResult]:
        """Iterate over all results."""
        return iter(self.results)

    def filter_by_category(self, category: SummaryCategory) -> list[BatchSummaryResult]:
        """Get all results that belong to a specific category."""
        return [r for r in self.results if r.has_category(category)]

    def print(self, console: Console | None = None):
        """Print summary to console."""
        if console is None:
            console = Console()

        console.print()
        console.print(f"[bold]Total: {self.total}[/bold]")

        # Print counts for each category
        for category in self.categories:
            count = self.count(category)
            if count > 0:
                if category.color:
                    console.print(
                        f"  [{category.color}]{category.icon} {count} {category.name}[/{category.color}]"
                    )
                else:
                    console.print(f"  {category.icon} {count} {category.name}")

        # Print errors if any
        error_categories = [cat for cat in self.categories if cat.is_error]
        for error_cat in error_categories:
            if self.count(error_cat) > 0:
                console.print()
                console.print(
                    f"[bold {error_cat.color}]{error_cat.name}:[/bold {error_cat.color}]"
                )
                for result in self.filter_by_category(error_cat):
                    if result.error:
                        console.print(
                            f"  [{error_cat.color}]- {result.name}: {result.error}[/{error_cat.color}]"
                        )
                    else:
                        console.print(
                            f"  [{error_cat.color}]- {result.name}[/{error_cat.color}]"
                        )
                break
