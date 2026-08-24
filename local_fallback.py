def summarize_locally(text: str, max_chars: int = 500) -> str:
    """
    Prosty fallback bez AI.
    Nie interpretuje medycznie danych — jedynie skraca tekst technicznie.
    """
    cleaned = " ".join((text or "").split())
    if len(cleaned) <= max_chars:
        return cleaned
    return cleaned[:max_chars].rstrip() + "…"

def classify_record_locally(record: dict) -> str:
    """
    Regułowa klasyfikacja bez AI.
    """
    record_id = str(record.get("id", "")).upper()

    if record_id.startswith("MED-"):
        return "medication"
    if record_id.startswith("VIS-"):
        return "appointment"
    if record_id.startswith("BAD-"):
        return "test"
    if record_id.startswith("REC-"):
        return "prescription"

    return "other"
