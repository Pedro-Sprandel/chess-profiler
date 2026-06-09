def format_root_cause(diagnosis: dict) -> dict:
    """Extract root cause fields for display."""
    rc = diagnosis.get("root_cause", {})
    return {
        "name": rc.get("name", ""),
        "description": rc.get("description", ""),
        "confidence": diagnosis.get("confidence", "LOW"),
    }


def format_weakness_table(diagnosis: dict) -> list:
    """Return a list of dicts suitable for st.dataframe."""
    rows = []
    for item in diagnosis.get("weakness_classification", []):
        rows.append({
            "Concept": item.get("concept", "").replace("_", " ").title(),
            "Classification": item.get("classification", ""),
            "Reasoning": item.get("reasoning", ""),
        })
    return rows


def format_study_priority(diagnosis: dict) -> list:
    """Return a ranked list of study items for display."""
    items = []
    for item in sorted(diagnosis.get("study_priority", []), key=lambda x: x.get("priority_rank", 99)):
        items.append({
            "rank": item.get("priority_rank"),
            "concept": item.get("concept", "").replace("_", " ").title(),
            "chapter": item.get("silman_chapter", "?"),
            "page": item.get("silman_page", "?"),
            "reason": item.get("reason", ""),
        })
    return items
