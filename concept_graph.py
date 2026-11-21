"""Class 10 Physics - Electricity concept graph.

The graph is not decoration: PREREQUISITES drive question selection (learner_model.plan_next_concept)
and the graph view colours every node by the student's mastery.
"""
import networkx as nx

CONCEPTS = [
    "Electric Charge",
    "Electric Current",
    "Potential Difference",
    "Resistance",
    "Ohm's Law",
    "Electric Power",
    "Series and Parallel Circuits",
]

# (prerequisite, concept)
CONNECTIONS = [
    ("Electric Charge", "Electric Current"),
    ("Electric Current", "Ohm's Law"),
    ("Potential Difference", "Ohm's Law"),
    ("Resistance", "Ohm's Law"),
    ("Ohm's Law", "Electric Power"),
    ("Ohm's Law", "Series and Parallel Circuits"),
    ("Resistance", "Series and Parallel Circuits"),
]


def create_graph():
    g = nx.DiGraph()
    g.add_nodes_from(CONCEPTS)
    g.add_edges_from(CONNECTIONS)
    return g


def get_prerequisites(concept):
    return list(create_graph().predecessors(concept))


def get_dependents(concept):
    return list(create_graph().successors(concept))


def layered_positions(graph):
    """Left-to-right layout by dependency depth (foundations on the left)."""
    pos = {}
    for x, layer in enumerate(nx.topological_generations(graph)):
        layer = sorted(layer)
        for i, node in enumerate(layer):
            pos[node] = (x, (len(layer) - 1) / 2 - i)
    return pos


def show_graph(mastery=None):
    """Plotly figure. `mastery` = {concept: score}; nodes coloured red->green."""
    import plotly.graph_objects as go  # lazy import keeps backend testable without plotly

    graph = create_graph()
    pos = layered_positions(graph)
    mastery = mastery or {}

    fig = go.Figure()
    for a, b in graph.edges():
        (x0, y0), (x1, y1) = pos[a], pos[b]
        fig.add_annotation(
            x=x1, y=y1, ax=x0, ay=y0, xref="x", yref="y", axref="x", ayref="y",
            showarrow=True, arrowhead=3, arrowsize=1.3, arrowwidth=1.6,
            arrowcolor="#8a8f98", standoff=26, startstandoff=26,
        )

    nodes = list(graph.nodes())
    scores = [mastery.get(n) for n in nodes]
    colors = [s if s is not None else 50 for s in scores]
    hover = []
    for n, s in zip(nodes, scores):
        pre = ", ".join(get_prerequisites(n)) or "none (foundation)"
        hover.append(f"<b>{n}</b><br>Mastery: {'n/a' if s is None else f'{s:.0f}%'}"
                     f"<br>Needs first: {pre}")

    fig.add_trace(go.Scatter(
        x=[pos[n][0] for n in nodes], y=[pos[n][1] for n in nodes],
        mode="markers+text", text=[n.replace(" and ", " &<br>") for n in nodes],
        textposition="bottom center", hovertext=hover, hoverinfo="text",
        marker=dict(size=46, color=colors, colorscale="RdYlGn", cmin=0, cmax=100,
                    line=dict(width=2, color="white"),
                    colorbar=dict(title="Mastery %")),
    ))
    fig.update_layout(
        title="Physics Concept Graph (arrows = 'must understand first')",
        showlegend=False, height=560, margin=dict(l=20, r=20, t=60, b=20),
        xaxis=dict(visible=False, range=[-0.5, 3.5]),
        yaxis=dict(visible=False, range=[-2, 1.6]),
    )
    return fig
