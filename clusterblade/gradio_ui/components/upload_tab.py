import gradio as gr
import yaml
from pathlib import Path
from collections import defaultdict


def render_upload_tab(shared_state):
    """
    Upload & preview instances.yml file grouped by node role.
    Updates shared_state with parsed data for other tabs.
    """

    def parse_yaml(file_obj):
        if not file_obj:
            return "<p style='color:red'>No file uploaded.</p>"

        try:
            path = getattr(file_obj, "name", None)
            if not path or not Path(path).exists():
                return "<p style='color:red'>❌ Invalid file.</p>"

            with open(path, "r", encoding="utf-8") as f:
                data = yaml.safe_load(f)

            instances = data.get("instances") or data.get("nodes")
            if not instances:
                return "<p style='color:orange'>⚠️ No instances found.</p>"

            # ✅ Store instances so deploy / SSL tabs can use them
            shared_state["instances"] = instances
            shared_state["file"] = path
            
            # Group nodes by inferred role
            grouped = defaultdict(list)
            for inst in instances:
                name = inst.get("name", "").lower()
                if "master" in name:
                    grouped["Master"].append(inst)
                elif "request" in name:
                    grouped["Request"].append(inst)
                elif "ingest" in name:
                    grouped["Ingest"].append(inst)
                elif "datahot" in name or "hot" in name:
                    grouped["DataHot"].append(inst)
                elif "warm" in name:
                    grouped["DataWarm"].append(inst)
                elif "cold" in name:
                    grouped["DataCold"].append(inst)
                else:
                    grouped["Other"].append(inst)

            shared_state["grouped_nodes"] = grouped

            # Generate grouped HTML preview
            html = ["<div style='font-family:monospace;'>"]
            for role, nodes in grouped.items():
                html.append(f"<h3 style='color:#4CAF50;'>{role} Nodes ({len(nodes)})</h3>")
                html.append("<table style='width:100%;border-collapse:collapse;'>")
                html.append("<tr><th>Name</th><th>IP</th><th>DNS</th></tr>")
                for inst in nodes:
                    html.append(
                        f"<tr><td>{inst.get('name')}</td>"
                        f"<td>{inst.get('ip')}</td>"
                        f"<td>{inst.get('dns')}</td></tr>"
                    )
                html.append("</table><br>")
            html.append("</div>")

            return "\n".join(html)

        except Exception as e:
            return f"<p style='color:red'>❌ Error parsing YAML: {e}</p>"

    with gr.Column():
        
        gr.Markdown("### 📤 Upload Your `instances.yml`")
        file_input = gr.File(label="Upload YAML", file_types=[".yml", ".yaml"])
        preview_html = gr.HTML(label="Preview")

        # Handle upload event
        file_input.upload(parse_yaml, inputs=[file_input], outputs=[preview_html])
       
