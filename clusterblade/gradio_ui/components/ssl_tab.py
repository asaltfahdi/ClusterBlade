import gradio as gr
from pathlib import Path
from clusterblade.certificates.deploy_ssl import deploy_ssl_to_nodes
from clusterblade.certificates.generator import generate_all_from_yaml

def render_ssl_tab(shared_state):
    """
    SSL tab — regenerates and deploys SSL certificates for all nodes.
    """
    def generate_and_deploy(ssh_user, ssh_pass, cert_pass,cert_validity):
        logs = []

        if "file" not in shared_state or not Path(shared_state["file"]).exists():
            return "❌ Please upload and parse instances.yml first."

        yaml_path = Path(shared_state["file"])
        cert_dir = Path("runtime/certificates")
        password = cert_pass.encode() if cert_pass else None
        cert_validity=int(cert_validity) if cert_validity.isdigit() else 3650
        try:
            logs.append("🧹 Cleaning and regenerating SSL certificates...\n")
            generate_all_from_yaml(yaml_path, cert_dir, password,cert_validity)
            logs.append("✅ Certificates regenerated successfully.\n")
        except Exception as e:
            logs.append(f"❌ SSL generation failed: {e}\n")
            return "\n".join(logs)

        try:
            logs.append("🚀 Starting SSL deployment to nodes...\n")
            deploy_logs = deploy_ssl_to_nodes(shared_state, ssh_user, ssh_pass, cert_pass)
            logs.append(deploy_logs)
            logs.append("🎉 SSL deployment completed.\n")
        except Exception as e:
            logs.append(f"❌ SSL deployment failed: {e}\n")

        return "\n".join(logs)

    with gr.Column():
        gr.Markdown("## 🔐 SSL Certificate Generator & Deployment")

        ssh_user = gr.Textbox(label="SSH Username", placeholder="root or elastic", interactive=True)
        ssh_pass = gr.Textbox(label="SSH Password", type="password", interactive=True)
        cert_pass = gr.Textbox(
            label="Certificate Password (optional)",
            placeholder="Leave empty for no encryption",
            interactive=True
        )
        cert_validity = gr.Textbox(label="Number of Days (3650 days - 10y)", placeholder="10y", interactive=True)

        run_btn = gr.Button("⚙️ Regenerate & Deploy SSL Certificates", variant="primary", scale=2)
        logs_box = gr.Textbox(label="Logs", lines=20, interactive=False)

        run_btn.click(
            fn=generate_and_deploy,
            inputs=[ssh_user, ssh_pass, cert_pass,cert_validity],
            outputs=[logs_box]
        )
