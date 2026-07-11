import plotly.graph_objects as go
from ui.i18n import t
from ui.concepts import concept_label, concept_category, category_label, CATEGORY_LABELS


def build_error_count_chart(weaknesses: list) -> go.Figure:
    """Bar chart of error occurrences per concept, sorted descending."""
    sorted_w = sorted(weaknesses, key=lambda x: x["error_occurrences"], reverse=True)
    concepts = [concept_label(w["concept"]) for w in sorted_w]
    counts = [w["error_occurrences"] for w in sorted_w]
    fig = go.Figure(go.Bar(x=concepts, y=counts, marker_color="crimson"))
    fig.update_layout(
        title=t("chart.count.title"),
        xaxis_title=t("chart.x_concept"),
        yaxis_title=t("chart.count.y"),
        height=400,
    )
    return fig


def build_error_magnitude_chart(weaknesses: list) -> go.Figure:
    """Bar chart of average error magnitude (centipawns) per concept."""
    sorted_w = sorted(weaknesses, key=lambda x: x["avg_error_magnitude_cp"], reverse=True)
    concepts = [concept_label(w["concept"]) for w in sorted_w]
    magnitudes = [w["avg_error_magnitude_cp"] for w in sorted_w]
    fig = go.Figure(go.Bar(x=concepts, y=magnitudes, marker_color="steelblue"))
    fig.update_layout(
        title=t("chart.magnitude.title"),
        xaxis_title=t("chart.x_concept"),
        yaxis_title=t("chart.magnitude.y"),
        height=400,
    )
    return fig


def build_category_radar(weaknesses: list) -> go.Figure:
    """Radar (polar) chart of error occurrences aggregated by Silman category."""
    totals = {category: 0 for category in CATEGORY_LABELS}
    for w in weaknesses:
        category = concept_category(w["concept"])
        if category in totals:
            totals[category] += w["error_occurrences"]

    categories = [category_label(c) for c in totals]
    values = list(totals.values())
    # Fecha o polígono repetindo o primeiro ponto
    fig = go.Figure(go.Scatterpolar(
        r=values + values[:1],
        theta=categories + categories[:1],
        fill="toself",
        marker_color="crimson",
    ))
    fig.update_layout(
        title=t("chart.radar.title"),
        polar=dict(radialaxis=dict(visible=True, rangemode="tozero")),
        showlegend=False,
        height=400,
    )
    return fig


def build_comparison_chart(profiles: list[tuple[str, list]]) -> go.Figure:
    """
    Grouped bar chart comparing error rate (%) per concept across profiles.

    profiles: lista de (label, weaknesses) — um grupo de barras por perfil.
    """
    all_concepts: list[str] = []
    for _, weaknesses in profiles:
        for w in weaknesses:
            if w["concept"] not in all_concepts:
                all_concepts.append(w["concept"])

    fig = go.Figure()
    for label, weaknesses in profiles:
        rates = {w["concept"]: w["error_rate"] * 100 for w in weaknesses}
        fig.add_trace(go.Bar(
            name=label,
            x=[concept_label(c) for c in all_concepts],
            y=[round(rates.get(c, 0), 1) for c in all_concepts],
        ))
    fig.update_layout(
        title=t("chart.compare.title"),
        xaxis_title=t("chart.x_concept"),
        yaxis_title=t("chart.compare.y"),
        barmode="group",
        height=420,
    )
    return fig
