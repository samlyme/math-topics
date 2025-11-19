# demo2_select_menu.py
# -----------------------------
# What this demo shows:
# - Two-step selection menu:
#     * Choose whether you're selecting a METRIC (degree/eigenvector/clustering)
#       or a COMMUNITY (community 0/1/2…).
#     * Then choose the specific metric or community value.
# - A live summary string and a preview table that update with your selection.
#
# How to run (from an activated .venv):
#   python -m shiny run --reload demo2_select_menu.py --port 8001


from shiny import App, ui, render, reactive
import pandas as pd
import numpy as np
import networkx as nx

# -----------------------------
# 1) Build a small example network + compute metrics
# -----------------------------
G = nx.gnm_random_graph(60, 140, seed=7)

deg = dict(G.degree())
eig = nx.eigenvector_centrality(G, max_iter=1000)
clust = nx.clustering(G)

communities = list(nx.algorithms.community.greedy_modularity_communities(G))
community_of = {n: cid for cid, C in enumerate(communities) for n in C}

# Assemble a DataFrame with several metrics for each node.
df = pd.DataFrame(
    {
        "node": list(G.nodes()),
        "degree": [deg[n] for n in G.nodes()],
        "eigenvector": [eig[n] for n in G.nodes()],
        "clustering": [clust[n] for n in G.nodes()],
        "community": [community_of[n] for n in G.nodes()],
    }
)

# -----------------------------
# 2) Define the Shiny UI
# -----------------------------
app_ui = ui.page_sidebar(
    ui.sidebar(
        # First choose: are we selecting a metric or a community?
        ui.input_radio_buttons(
            "choice_type",
            "I want to choose a...",
            choices={"metric": "Metric", "community": "Community"},
            selected="metric",
        ),
        # The second dropdown ("chooser") depends on the first choice, so we generate it from the server.
        ui.output_ui("chooser"),
    ),

    ui.h3("Selection Menu Demo"),
    ui.p("Pick a metric or a community on the left; summary and table will update here."),
    ui.output_text_verbatim("summary"),  # a one-line summary of the current selection
    ui.output_table("preview"),          # preview table of nodes

    title="Demo 2 — Selection Menus",
)

# -----------------------------
# 3) Server logic
# -----------------------------
def server(input, output, session):
    # Dynamically generate the second dropdown based on "metric" vs "community".
    @output
    @render.ui
    def chooser():
        if input.choice_type() == "metric":
            # If "metric", provide a dropdown of columns to choose from.
            return ui.input_select(
                "metric",
                "Metric",
                {"degree": "Degree", "eigenvector": "Eigenvector", "clustering": "Clustering"},
                selected="degree",
            )
        else:
            # If "community", list unique community ids discovered in the graph.
            comm_choices = {str(c): f"Community {c}" for c in sorted(df["community"].unique())}
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
            return df[df["community"] == c][["node", "degree", "eigenvector", "clustering"]].head(10)




app = App(app_ui, server)
