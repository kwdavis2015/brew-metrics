def parse_nonneg_int(value: str | None) -> int | None:
    """Parse a non-negative whole number from form input.

    Returns None for anything that isn't a clean non-negative integer
    (empty, blank, decimals, negatives, letters, stray symbols), so callers
    can reject typos instead of letting FastAPI raise a raw 422.
    """
    value = (value or "").strip()
    return int(value) if value.isdigit() else None
