import plotly.graph_objects as go
from ui.i18n import t
from ui.concepts import concept_label, concept_category, category_label, CATEGORY_LABELS
from ui.style import ACCENT, ACCENT_FILL, ACCENT_SOFT, BORDER, CARD, ERROR, GOOD, GRID, INK, MUTED, SUBTLE, WARN

_FONT = dict(family="Inter, -apple-system, Segoe UI, Roboto, sans-serif", size=12, color=MUTED)
# Ordered series colors for multi-profile comparison (desaturated, distinguishable).
SERIES_COLORS = [ACCENT, ERROR, GOOD, WARN, "#A78BCA", SUBTLE]


def _style(fig: go.Figure, title: str, height: int) -> go.Figure:
    fig.update_layout(
        title=dict(text=title, x=0, xanchor="left", font=dict(size=14, color=INK)),
        font=_FONT,
        height=height,
        margin=dict(l=10, r=20, t=48, b=10),
        plot_bgcolor="rgba(0,0,0,0)",
        paper_bgcolor="rgba(0,0,0,0)",
        hoverlabel=dict(bgcolor=CARD, bordercolor=BORDER, font=dict(color=INK)),
        bargap=0.35,
    )
    fig.update_xaxes(showgrid=True, gridcolor=GRID, zeroline=False, linecolor=BORDER)
    fig.update_yaxes(showgrid=False, zeroline=False, linecolor=BORDER)
    return fig


def _hbar(labels, values, color, title, x_title, fmt) -> go.Figure:
    fig = go.Figure(go.Bar(
        x=values, y=labels, orientation="h", marker_color=color,
        text=[fmt(v) for v in values], textposition="outside", cliponaxis=False,
        hovertemplate="%{y}: %{x}<extra></extra>",
    ))
    _style(fig, title, height=max(260, 46 * len(values) + 90))
    # Largest value on top.
    fig.update_yaxes(autorange="reversed", ticks="", color=INK)
    fig.update_xaxes(title_text=x_title, title_font=dict(size=11))
    return fig


def build_error_count_chart(weaknesses: list) -> go.Figure:
    """Horizontal bars of error occurrences per concept, sorted descending."""
    sorted_w = sorted(weaknesses, key=lambda x: x["error_occurrences"], reverse=True)
    return _hbar(
        [concept_label(w["concept"]) for w in sorted_w],
        [w["error_occurrences"] for w in sorted_w],
        ACCENT, t("chart.count.title"), t("chart.count.y"), lambda v: f"{v}",
    )


def build_error_magnitude_chart(weaknesses: list) -> go.Figure:
    """Horizontal bars of average error magnitude (centipawns) per concept."""
    sorted_w = sorted(weaknesses, key=lambda x: x["avg_error_magnitude_cp"], reverse=True)
    return _hbar(
        [concept_label(w["concept"]) for w in sorted_w],
        [w["avg_error_magnitude_cp"] for w in sorted_w],
        ACCENT_SOFT, t("chart.magnitude.title"), t("chart.magnitude.y"), lambda v: f"{v:.0f}",
    )


def build_category_radar(weaknesses: list) -> go.Figure:
    """Radar (polar) chart of error occurrences aggregated by Silman category."""
    totals = {category: 0 for category in CATEGORY_LABELS}
    for w in weaknesses:
        category = concept_category(w["concept"])
        if category in totals:
            totals[category] += w["error_occurrences"]

    # Wrap long names ("Desequilíbrios estáticos") so they don't clip at the sides.
    categories = [category_label(c).replace(" ", "<br>", 1) if len(category_label(c)) > 14
                  else category_label(c) for c in totals]
    values = list(totals.values())
    # Fecha o polígono repetindo o primeiro ponto
    fig = go.Figure(go.Scatterpolar(
        r=values + values[:1],
        theta=categories + categories[:1],
        fill="toself",
        fillcolor=ACCENT_FILL,
        line=dict(color=ACCENT, width=2),
        marker=dict(size=5, color=ACCENT),
        hovertemplate="%{theta}: %{r}<extra></extra>",
    ))
    _style(fig, t("chart.radar.title"), height=380)
    fig.update_layout(
        polar=dict(
            bgcolor="rgba(0,0,0,0)",
            radialaxis=dict(visible=True, rangemode="tozero", gridcolor=GRID,
                            linecolor=BORDER, tickfont=dict(size=10, color=SUBTLE)),
            angularaxis=dict(gridcolor=GRID, linecolor=BORDER, tickfont=dict(color=INK)),
        ),
        showlegend=False,
        margin=dict(l=95, r=95, t=56, b=30),
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
    for i, (label, weaknesses) in enumerate(profiles):
        rates = {w["concept"]: w["error_rate"] * 100 for w in weaknesses}
        fig.add_trace(go.Bar(
            name=label,
            x=[concept_label(c) for c in all_concepts],
            y=[round(rates.get(c, 0), 1) for c in all_concepts],
            marker_color=SERIES_COLORS[i % len(SERIES_COLORS)],
            hovertemplate="%{x}: %{y}%<extra>" + label + "</extra>",
        ))
    _style(fig, t("chart.compare.title"), height=420)
    fig.update_layout(
        barmode="group",
        legend=dict(orientation="h", yanchor="bottom", y=1.02, x=0, font=dict(color=INK)),
        margin=dict(l=10, r=20, t=80, b=10),
    )
    fig.update_xaxes(showgrid=False)
    fig.update_yaxes(showgrid=True, gridcolor=GRID, title_text=t("chart.compare.y"))
    return fig
