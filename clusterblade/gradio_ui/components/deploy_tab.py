import gradio as gr
from time import sleep
from clusterblade.elastic.deploy import deploy_cluster


def render_deploy_tab(shared_state):
    """
    Render the Deploy tab for Elasticsearch cluster configuration.
    """

    def start_deployment(cluster_name, enable_ssl, enable_http, http_groups, ssh_user, ssh_pass, progress=gr.Progress(track_tqdm=True)):
        if not shared_state.get("file"):
            return "⚠️ Please upload a valid 'instances.yaml' file first from the **Upload tab**, then click '🔄 Check Upload Status'."

        shared_state.update({
            "cluster_name": cluster_name or "es-cluster",
            "enable_ssl": enable_ssl,
            "enable_http": enable_http,
            "http_groups": http_groups,
        })

        logs = []
        instances = shared_state.get("instances", [])
        if not instances:
            return "❌ No nodes found. Please re-upload your YAML in the Upload tab."

        total_nodes = len(instances)
        logs.append("🚀 Starting Elasticsearch deployment...\n")
        yield "\n".join(logs)

        for i, node in enumerate(instances, start=1):
            node_name = node.get("name")
            node_ip = node.get("ip")

            progress((i - 1) / total_nodes, desc=f"⚙️ Deploying {node_name} ({node_ip})")
            logs.append(f"\n⚙️ Deploying configuration to {node_name} ({node_ip})...")
            yield "\n".join(logs)

            try:
                result = deploy_cluster(shared_state, ssh_user, ssh_pass)
                logs.append(f"✅ Finished node {node_name} ({node_ip}) successfully.\n{result}")
            except Exception as e:
                logs.append(f"❌ Failed on {node_name} ({node_ip}): {e}")
                yield "\n".join(logs)
                continue

            progress(i / total_nodes, desc=f"✅ Completed {node_name}")
            yield "\n".join(logs)

        progress(1.0, desc="🎉 All nodes deployed successfully")
        logs.append("\n🎉 All nodes deployed successfully.\n")
        yield "\n".join(logs)

    with gr.Blocks():
        # --- Top info + refresh button ---
        gr.Markdown("""
        ## **🔄 Check Upload Status** button below to verify that the file is detected.
        """)

        with gr.Row():
            refresh_btn = gr.Button("🔍 Check Upload Status", variant="secondary", scale=1)

        # --- Main configuration section ---
        gr.Markdown("### Elasticsearch Cluster Deployment")

        cluster_name = gr.Textbox(label="Cluster Name", placeholder="es-cluster", interactive=True)
        enable_ssl = gr.Checkbox(label="Enable SSL", value=True)
        enable_http = gr.Checkbox(label="Enable HTTP", value=False)

        http_groups = gr.CheckboxGroup(
            ["master", "data", "ingest", "coordinator"],
            label="Enable HTTP on these node groups",
            interactive=False
        )

        def toggle_http_groups(enable_http):
            return gr.CheckboxGroup.update(interactive=enable_http)
        enable_http.change(fn=toggle_http_groups, inputs=enable_http, outputs=http_groups)

        with gr.Row():
            ssh_user = gr.Textbox(label="SSH Username", value="root", interactive=True)
            ssh_pass = gr.Textbox(label="SSH Password", type="password", interactive=True)

        with gr.Row():
            run_btn = gr.Button("🟢 Deploy Cluster", variant="primary", scale=2, interactive=False)

        progress_bar = gr.Markdown("### ⏳ Deployment Progress:")
        logs = gr.Textbox(label="Logs", lines=20, interactive=False)

        # --- Manual refresh logic ---
        def check_file_uploaded():
            """
            Enables or disables the Deploy button depending on whether
            a YAML file has been uploaded. Compatible with all Gradio versions.
            """
            if shared_state.get("file"):
                # YAML uploaded → enable deploy
                return gr.Button("🟢 Deploy Cluster", interactive=True)
            else:
                # No YAML yet → keep disabled with message
                return gr.Button("⏳ Waiting for 'instances.yaml' upload...", interactive=False)

        refresh_btn.click(fn=check_file_uploaded, outputs=[run_btn])

        # --- Run deployment ---
        run_btn.click(
            fn=start_deployment,
            inputs=[cluster_name, enable_ssl, enable_http, http_groups, ssh_user, ssh_pass],
            outputs=[logs],
            show_progress=True
        )
