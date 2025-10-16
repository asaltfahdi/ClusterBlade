import gradio as gr
import argparse
from clusterblade.gradio_ui.components.upload_tab import render_upload_tab
from clusterblade.gradio_ui.components.deploy_tab import render_deploy_tab
from clusterblade.gradio_ui.components.ssl_tab import render_ssl_tab
from clusterblade.gradio_ui.components.monitor_tab import render_monitor_tab
from clusterblade.gradio_ui.components.readme_tab import render_readme_tab 
from clusterblade.gradio_ui.components.enable_https_tab import render_enable_https_tab
from clusterblade.core.paths import get_runtime_dir
from pathlib import Path

def main(port: int = 7860):
    # Ensure runtime directories exist
    get_runtime_dir()

    # Shared state across all tabs
    shared_state = {
        "file": None,          # uploaded YAML path
        "instances": None,     # parsed node data
        "cluster_name": None,  # cluster name from Deploy tab
    }
    CSS_PATH = Path(__file__).parent / "static" / "custom.css"
    CUSTOM_CSS = CSS_PATH.read_text(encoding="utf-8")

    with gr.Blocks(css=CUSTOM_CSS,title="ClusterBlade") as app:
        gr.HTML("<link rel='stylesheet' href='/static/custom.css'>")
        gr.Markdown("# ⚙️ ClusterBlade Control Center")
        gr.Markdown(
            "Manage your Elasticsearch cluster: Upload configuration, "
            "deploy it, generate SSL certificates, and monitor health."
        )

        # Tabs
        
        with gr.Tab("📘 README"):
            render_readme_tab()
        with gr.Tab("📤 Upload File"):
            render_upload_tab(shared_state)

        with gr.Tab("🚀 Deploy Cluster"):
            render_deploy_tab(shared_state)

        with gr.Tab("🔐 SSL Certificates"):
            render_ssl_tab(shared_state)

        with gr.Tab("Enable HTTPS"): 
            render_enable_https_tab(shared_state)

        with gr.Tab("📊 Monitor Cluster"):
            render_monitor_tab(shared_state)

        gr.Markdown("---")
        gr.Markdown(
            "🧠 **Usage:** Upload your `instances.yaml`, deploy configurations, "
            "generate SSL certificates, then verify cluster health in the Monitor tab."
        )

    app.launch(server_port=port, share=False, show_api=False)


def cli_main():
    import argparse, os
    parser = argparse.ArgumentParser(description="Launch ClusterBlade dashboard")
    parser.add_argument("--port", type=int, default=7860, help="Port number to run on")
    args = parser.parse_args()

    main(port=args.port)

if __name__ == "__main__":
    cli_main()


