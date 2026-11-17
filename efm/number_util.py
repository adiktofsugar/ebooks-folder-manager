"""Human-readable numbers for output and logs."""


def format_bytes(size: int) -> str:
    # Decimal units, matching what file managers and drive labels show.
    if size < 1000:
        return f"{size} B"
    n = size / 1000
    for unit in ("KB", "MB"):
        if n < 1000:
            return f"{n:.1f} {unit}"
        n /= 1000
    return f"{n:.1f} GB"
