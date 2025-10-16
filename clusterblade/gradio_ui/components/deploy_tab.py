import gradio as gr
from time import sleep
from clusterblade.elastic.deploy import deploy_cluster


def render_deploy_tab(shared_state):
    """
    Render the Deploy tab for Elasticsearch cluster configuration.
    """

    def start_deployment(
        cluster_name,
        enable_ssl,
        enable_http,
        http_groups,
        enable_security,
        enable_logging,
        memory_lock,
        ssh_user,
        ssh_pass,
        progress=gr.Progress(track_tqdm=True),
    ):
        if not shared_state.get("file"):
            return "⚠️ Please upload a valid 'instances.yaml' file first from the **Upload tab**, then click '🔄 Check Upload Status'."

        instances = shared_state.get("instances", [])
        node_racks = [n.get("rack", "r1") for n in instances]
        if not instances:
            return "❌ No nodes found. Please re-upload your YAML in the Upload tab."

        # 🆕 apply rack selections
        for i, node in enumerate(instances):
            node["rack"] = node_racks[i] if i < len(node_racks) else "r1"

        shared_state.update({
            "cluster_name": cluster_name or "es-cluster",
            "enable_ssl": enable_ssl,
            "enable_http": enable_http,
            "http_groups": http_groups,
            "enable_security": enable_security,
            "enable_logging": enable_logging,
            "memory_lock": memory_lock,
            "instances": instances,   # 🆕 save updated rack info
        })

        logs = []
        total_nodes = len(instances)
        logs.append("🚀 Starting Elasticsearch deployment...\n")
        yield "\n".join(logs)

        for i, node in enumerate(instances, start=1):
            node_name = node.get("name")
            node_ip = node.get("ip")
            rack = node.get("rack", "r1")

            progress((i - 1) / total_nodes, desc=f"⚙️ Deploying {node_name} ({node_ip}) [Rack {rack}]")
            logs.append(f"\n⚙️ Deploying configuration to {node_name} ({node_ip}) [Rack {rack}]...")
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
        gr.Markdown("### Elasticsearch Cluster Deployment")

        cluster_name = gr.Textbox(label="Cluster Name", placeholder="es-cluster", interactive=True)
        enable_security = gr.Checkbox(label="Enable X-Pack Security", value=False)
        enable_ssl = gr.Checkbox(label="Enable SSL (Transport)", value=False, interactive=True)
        enable_http = gr.Checkbox(label="Enable HTTPS (Client)", value=False, interactive=True)

        http_groups = gr.CheckboxGroup(
            ["master", "data", "ingest", "coordinator", "request"],
            label="Enable HTTPS on these node groups",
            interactive=False
        )

        enable_logging = gr.Checkbox(label="Enable Debug Logging", value=False)
        memory_lock = gr.Checkbox(label="Enable Memory Lock", value=False)


        

        rack_fields_box = gr.HTML("<p>⚙️ Waiting for instances.yaml...</p>")

        ssh_user = gr.Textbox(label="SSH Username", value="root", interactive=True)
        ssh_pass = gr.Textbox(label="SSH Password", type="password", interactive=True)
        logs = gr.Textbox(label="Logs", lines=20, interactive=False)
    
        run_btn = gr.Button("⚙️ Waiting for YAML- (Click check button below)", variant="primary", interactive=False)
        refresh_btn = gr.Button( "🔍 Check Upload Status", variant="secondary")

                # --- File check logic ---
        def check_file_uploaded():
            instances = shared_state.get("instances", [])
            if not shared_state.get("file") or not instances:
                return (gr.update(value="<p style='color:orange;'>⚠️ Please upload instances.yaml first.</p>"),
                gr.update(interactive=False))

            
            # ✅ Just silently confirm file exists — no display, no summary
            return (gr.update(value="<p style='color:green;'>✅ instances.yaml loaded successfully.</p>"),
            gr.update(value="🟢 Deploy Cluster", interactive=True))


        refresh_btn.click(
            fn=check_file_uploaded,
            outputs=[rack_fields_box,run_btn]
        )

        # --- Interactivity logic ---
        def toggle_security(enable_security):
            if enable_security:
                return (
                    gr.update(interactive=True),
                    gr.update(interactive=True),
                    gr.update(interactive=False),
                )
            else:
                return (
                    gr.update(value=False, interactive=False),
                    gr.update(value=False, interactive=False),
                    gr.update(value=[], interactive=False),
                )

        enable_security.change(
            fn=toggle_security,
            inputs=[enable_security],
            outputs=[enable_ssl, enable_http, http_groups],
        )

        def toggle_http_groups(enable_http):
            return gr.update(interactive=enable_http)

        enable_http.change(fn=toggle_http_groups, inputs=enable_http, outputs=http_groups)

        # --- Run deployment ---
        run_btn.click(
            fn=start_deployment,
            inputs=[
                cluster_name,
                enable_ssl,
                enable_http,
                http_groups,
                enable_security,
                enable_logging,
                memory_lock,
                ssh_user,
                ssh_pass,
            ],
            outputs=[logs],
            show_progress=True
        )
