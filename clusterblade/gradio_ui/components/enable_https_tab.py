import gradio as gr
import paramiko
import time
from pathlib import Path
from clusterblade.certificates.generator import generate_http_certs


def render_enable_https_tab(shared_state):
    """
    Tab to generate and deploy HTTPS certificates to Elasticsearch nodes.
    It does NOT modify elasticsearch.yml — that is handled separately.
    """

    def deploy_https(ssh_user, ssh_pass, cert_pass, selected_groups):
        logs = []

        # Check that instances.yml has been uploaded and parsed
        if "instances" not in shared_state or not shared_state["instances"]:
            return "❌ Please upload and parse instances.yml first using the Upload tab."

        yaml_path = Path(shared_state["file"])
        https_cert_dir = Path("runtime/certificates/https")
        https_cert_dir.mkdir(parents=True, exist_ok=True)

        # Check if CA exists (generated from SSL tab)
        ca_cert = Path("runtime/certificates/ca.pem")
        ca_key = Path("runtime/certificates/ca.key")

        if not ca_cert.exists() or not ca_key.exists():
            logs.append("⚠️ Missing CA files (ca.pem / ca.key). Please generate SSL certificates first.\n")
            return "\n".join(logs)

        # Step 1️⃣ - Generate HTTPS certificates
        try:
            logs.append("🔐 Generating HTTPS (HTTP layer) certificates using existing CA...\n")
            generate_http_certs(https_cert_dir, ca_cert, ca_key)
            logs.append("✅ HTTPS certificates generated successfully.\n")
        except Exception as e:
            logs.append(f"❌ Failed to generate HTTPS certificates: {e}\n")
            return "\n".join(logs)

        # Step 2️⃣ - Deploy HTTPS certs to selected nodes
        instances = shared_state["instances"]

        # Filter by node group names if selected
        selected_nodes = [
            node for node in instances
            if any(group in node.get("name", "") for group in selected_groups)
        ] or instances

        for node in selected_nodes:
            name, ip = node.get("name"), node.get("ip")
            logs.append(f"\n🚀 Deploying HTTPS certs to {name} ({ip})...\n")

            try:
                ssh = paramiko.SSHClient()
                ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
                ssh.connect(ip, username=ssh_user, password=ssh_pass, timeout=15)
                sftp = ssh.open_sftp()

                remote_dir = "/etc/elasticsearch/certs"
                ssh.exec_command(f"sudo mkdir -p {remote_dir}")
                ssh.exec_command(f"sudo chown elasticsearch:elasticsearch {remote_dir}")
                time.sleep(0.2)

                for file_name in ["ca.crt", "http.crt", "http.key"]:
                    local_file = https_cert_dir / file_name
                    if not local_file.exists():
                        logs.append(f"⚠️ Missing file: {local_file}\n")
                        continue

                    remote_file = f"{remote_dir}/{file_name}"
                    sftp.put(local_file.as_posix(), remote_file)
                    ssh.exec_command(f"sudo chown elasticsearch:elasticsearch {remote_file}")
                    ssh.exec_command(f"sudo chmod 640 {remote_file}")
                    time.sleep(0.1)

                sftp.close()
                ssh.close()

                logs.append(f"✅ HTTPS certs deployed successfully to {name} ({ip})\n")

            except Exception as e:
                logs.append(f"❌ Failed on {name} ({ip}): {e}\n")

        logs.append("\n🎉 HTTPS deployment completed!\n")
        return "\n".join(logs)

    # UI Components
    with gr.Column(elem_classes=["floating-box"]):
        gr.Markdown("## 🌐 Generate & Deploy HTTPS Certificates")

        ssh_user = gr.Textbox(label="SSH Username", placeholder="root or elastic", interactive=True)
        ssh_pass = gr.Textbox(label="SSH Password", type="password", interactive=True)
        cert_pass = gr.Textbox(
            label="Certificate Password (optional)",
            placeholder="Leave empty if not required",
            interactive=True
        )

        node_groups = ["master", "data", "ingest", "coordinator", "request"]
        selected_groups = gr.CheckboxGroup(
            choices=node_groups,
            label="Select Node Groups to Enable HTTPS",
            value=["master", "data"],
        )

        deploy_btn = gr.Button("⚙️ Generate & Deploy HTTPS", variant="primary", scale=2)
        output_box = gr.Textbox(label="Logs", lines=20, interactive=False)

        deploy_btn.click(
            fn=deploy_https,
            inputs=[ssh_user, ssh_pass, cert_pass, selected_groups],
            outputs=[output_box]
        )

    return gr.Column()
