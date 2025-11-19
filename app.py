from shiny import App, ui, render
app_ui = ui.page_fluid(
ui.h2("Hello Shiny!"),
ui.input_slider("n", "Number", 1, 10, 5),
ui.output_text("out")
)
def server(input, output, session):
    @output
    @render.text
    def out():
        return f"You picked {input.n()}"
app = App(app_ui, server)