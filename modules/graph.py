
from shiny import App, ui, render, reactive
import plotly.graph_objects as go
import networkx as nx
import pandas as pd


from graphCode import G, pos, deg_stats, comm_id, G_viz, communities


deg_map = dict(G.degree())
in_deg_map = dict(G.in_degree())
out_deg_map = dict(G.out_degree())


eig = nx.eigenvector_centrality(G_viz, max_iter=1000)
clust = nx.clustering(G_viz)
community_of = comm_id

#  DataFrame
df = pd.DataFrame(
    {
        "node": list(G.nodes()),
        "degree": [deg_map[n] for n in G.nodes()],
        "in_degree": [in_deg_map[n] for n in G.nodes()],
        "out_degree": [out_deg_map[n] for n in G.nodes()],
        "eigenvector": [eig.get(n, 0.0) for n in G.nodes()],
        "clustering": [clust.get(n, 0.0) for n in G.nodes()],
        "community": [community_of.get(n, -1) for n in G.nodes()],
    }
)

edges_x, edges_y = [], []
for u, v in G.edges():
    ux, uy = pos[u]
    vx, vy = pos[v]
    edges_x += [ux, vx, None]
    edges_y += [uy, vy, None]

# Slider
_stats = deg_stats(G)
max_deg = int(_stats.get("max_deg", _stats.get("max_degrees", max(deg_map.values()) if deg_map else 0)))

# -----------------------------
# 2) Define the Shiny UI
# -----------------------------
app_ui = ui.page_fluid(
    ui.navset_tab(
        ui.nav_panel("Home",
        ui.div(
            ui.h1("Math Topics", class_="text-center", style="font-size: 4rem; font-weight: bold; margin-top: 10rem; margin-bottom: 3rem;"),
        )
    ),
    ui.nav_panel("Graph",
        ui.layout_sidebar(
            ui.sidebar(
                ui.h5("Graph Visualization"),
                ui.input_slider(
                    "min_deg", "Min degree filter",
                    min=0, max=max_deg, value=0, step=1,
                ),
                ui.input_select(
                    "color_by", "Color nodes by",
                    choices={
                        "degree": "Degree",
                        "eigenvector": "Eigenvector Centrality",
                        "community": "Community",
                    },
                    selected="community",
                ),
                ui.input_checkbox("show_labels", "Show node labels", False),
                ui.input_checkbox("fix_aspect", "Fix aspect ratio (1:1)", True),
            ),
            ui.h3("Interactive Network Visualization"),
            ui.output_ui("graph_ui"),
            ui.p("Use your mouse to zoom and pan. Adjust filters and color options in the sidebar."),
        )
    ),
    ui.nav_panel("Selection Menu",
        ui.layout_sidebar(
            ui.sidebar(
                ui.h5("Selection Menu"),
                ui.input_radio_buttons(
                    "choice_type",
                    "I want to choose a...",
                    choices={"metric": "Metric", "community": "Community"},
                    selected="metric",
                ),
                ui.output_ui("chooser"),
            ),
            ui.h3("Selection Menu Results"),
            ui.p("Pick a metric or a community on the left; summary and table will update here."),
            ui.output_text_verbatim("summary"), 
            ui.output_table("preview"),
        )
    )
    )
)

# -----------------------------
# 3) Server logic 
# -----------------------------
def server(input, output, session):

    # Filter nodes by min degree
    @reactive.calc
    def filtered_nodes():
        m = input.min_deg()
        return [n for n, d in deg_map.items() if d >= m]

    @output
    @render.ui
    def graph_ui():
        nodes = filtered_nodes()
        node_set = set(nodes)

        # choose color
        color_by = input.color_by()

        # build node arrays
        x = [pos[n][0] for n in nodes]
        y = [pos[n][1] for n in nodes]

        # color values per node
        if color_by == "degree":
            colors = [deg_map.get(n, 0) for n in nodes]
            colorbar_title = "degree"
        elif color_by == "eigenvector":
            colors = [eig.get(n, 0.0) for n in nodes]
            colorbar_title = "eigenvector"
        else: 
            colors = [community_of.get(n, 0) for n in nodes]
            colorbar_title = "community"

        # labels and hover text
        labels = [str(n) for n in nodes] if input.show_labels() else None
        hovertext = [
            f"node = {n}<br>degree = {deg_map.get(n, 0)}<br>eigenvector = {eig.get(n, 0.0):.3f}<br>community = {community_of.get(n, -1)}"
            for n in nodes
        ]

        # rebuild edges 
        fx, fy = [], []
        for u, v in G.edges():
            if u in node_set and v in node_set:
                ux, uy = pos[u]
                vx, vy = pos[v]
                fx += [ux, vx, None]
                fy += [uy, vy, None]

        # edge layer
        edge_trace = go.Scatter(
            x=fx if nodes else [], y=fy if nodes else [],
            mode="lines",
            line=dict(width=1),
            hoverinfo="skip",
            showlegend=False,
        )

        # node layer
        node_trace = go.Scatter(
            x=x, y=y,
            mode="markers+text" if input.show_labels() else "markers",
            text=labels,
            textposition="top center",
            marker=dict(
                size=12,
                color=colors,
                showscale=True,
                colorbar=dict(title=colorbar_title),
            ),
            hoverinfo="text",
            hovertext=hovertext,
            showlegend=False,
        )

        fig = go.Figure(data=[edge_trace, node_trace])
        fig.update_layout(
            margin=dict(l=10, r=10, t=10, b=10),
            xaxis=dict(visible=False),
            yaxis=dict(visible=False),
        )
        if input.fix_aspect():
            fig.update_yaxes(scaleanchor="x", scaleratio=1)

        return ui.HTML(fig.to_html(include_plotlyjs="cdn", full_html=False))


    
    # Dynamically generate the second dropdown based on "metric" vs "community".
    @output
    @render.ui
    def chooser():
        if input.choice_type() == "metric":
            # If "metric", provide a dropdown of columns to choose from.
            return ui.input_select(
                "metric",
                "Metric",
                {
                    "degree": "Degree (Total)",
                    "in_degree": "In-Degree",
                    "out_degree": "Out-Degree",
                    "eigenvector": "Eigenvector Centrality",
                    "clustering": "Clustering Coefficient",
                },
                selected="degree",
            )
        else:
            # If "community", list unique community ids discovered in the graph.
            comm_choices = {str(c): f"Community {c}" for c in sorted(df["community"].unique()) if c >= 0}
            if not comm_choices:
                comm_choices = {"0": "Community 0"}
            first_key = next(iter(comm_choices.keys()))
            return ui.input_select("comm", "Community", comm_choices, selected=first_key)

    # A short textual summary; content depends on which "choice_type" is active.
    @output
    @render.text
    def summary():
        if input.choice_type() == "metric":
            m = input.metric()
            return f"Selected metric: {m}. Mean={df[m].mean():.3f}, Std={df[m].std():.3f}, Min={df[m].min():.3f}, Max={df[m].max():.3f}"
        else:
            c = int(input.comm())
            size = int((df["community"] == c).sum())
            return f"Selected community: {c}. Size={size} nodes."

    # A preview table. For metrics: top-10 nodes by that metric.
    # For communities: first 10 nodes in that community with a few columns.
    @output
    @render.table
    def preview():
        if input.choice_type() == "metric":
            m = input.metric()
            return df[["node", m]].sort_values(m, ascending=False).head(10)
        else:
            c = int(input.comm())
            comm_df = df[df["community"] == c][["node", "degree", "eigenvector", "clustering"]].head(10)
            return comm_df if not comm_df.empty else pd.DataFrame({"node": [], "degree": [], "eigenvector": [], "clustering": []})

app = App(app_ui, server)
