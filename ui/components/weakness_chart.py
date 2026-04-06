import plotly.graph_objects as go


def build_error_count_chart(weaknesses: list) -> go.Figure:
    """Bar chart of error occurrences per concept, sorted descending."""
    sorted_w = sorted(weaknesses, key=lambda x: x["error_occurrences"], reverse=True)
    concepts = [w["concept"].replace("_", " ").title() for w in sorted_w]
    counts = [w["error_occurrences"] for w in sorted_w]
    fig = go.Figure(go.Bar(x=concepts, y=counts, marker_color="crimson"))
    fig.update_layout(
        title="Error Occurrences per Concept",
        xaxis_title="Concept",
        yaxis_title="Error Count",
        height=400,
    )
    return fig


def build_error_magnitude_chart(weaknesses: list) -> go.Figure:
    """Bar chart of average error magnitude (centipawns) per concept."""
    sorted_w = sorted(weaknesses, key=lambda x: x["avg_error_magnitude_cp"], reverse=True)
    concepts = [w["concept"].replace("_", " ").title() for w in sorted_w]
    magnitudes = [w["avg_error_magnitude_cp"] for w in sorted_w]
    fig = go.Figure(go.Bar(x=concepts, y=magnitudes, marker_color="steelblue"))
    fig.update_layout(
        title="Average Error Magnitude per Concept (centipawns)",
        xaxis_title="Concept",
        yaxis_title="Avg Error (cp)",
        height=400,
    )
    return fig
