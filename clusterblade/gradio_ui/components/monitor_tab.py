import gradio as gr
import requests
import paramiko
import socket
from typing import Tuple
import subprocess
REQUEST_TIMEOUT = 3  # seconds
open_health_js = """
(_data) => {
    const result = _data?.[0];
    if (typeof result === 'string' && result.startsWith('http')) {
        window.open(result, '_blank');
        return '';
    }
    return result;
}
"""

def render_monitor_tab(shared_state):
    """Cluster monitor tab."""

    # ---------- Helpers ----------
    def ip_suffix_2(ip: str) -> str:
        last = ip.split(".")[-1]
        return last[-2:].zfill(2)

    def check_ssh_port(ip: str) -> bool:
        try:
            socket.setdefaulttimeout(REQUEST_TIMEOUT)
            s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            ok = (s.connect_ex((ip, 22)) == 0)
            s.close()
            return ok
        except Exception:
            return False

    def check_es_http(ip: str, user: str, pwd: str, use_https: bool) -> bool:
        port = int(f"92{ip_suffix_2(ip)}")
        scheme = "https" if use_https else "http"
        url = f"{scheme}://{ip}:{port}"
        try:
            r = requests.get(url, auth=(user, pwd), timeout=REQUEST_TIMEOUT, verify=False)
            return r.status_code == 200 or r.status_code == 401
        except Exception:
            return False
        
    def is_node_in_cluster(ip: str, es_user: str, es_pass: str, use_https: bool) -> bool:
        """Return True if this node is listed in _cat/nodes output."""
        port = int(f"92{ip_suffix_2(ip)}")
        scheme = "https" if use_https else "http"
        base_ip = ip  # this node's IP
        url = f"{scheme}://{base_ip}:{port}/_cat/nodes?h=ip&format=json"
        try:
            r = requests.get(url, auth=(es_user, es_pass), timeout=REQUEST_TIMEOUT, verify=False)
            if r.status_code == 200:
                nodes = [n["ip"] for n in r.json()]
                return base_ip in nodes
            return False
        except Exception:
            return False
    

    def ssh_exec(ip: str, user: str, pwd: str, cmd: str) -> Tuple[bool, str]:
        try:
            cli = paramiko.SSHClient()
            cli.set_missing_host_key_policy(paramiko.AutoAddPolicy())
            cli.connect(ip, username=user, password=pwd, timeout=REQUEST_TIMEOUT + 2)
            _, out, err = cli.exec_command(cmd)
            out_s = out.read().decode().strip()
            err_s = err.read().decode().strip()
            cli.close()
            if err_s:
                return False, err_s
            return True, out_s or "OK"
        except Exception as e:
            return False, str(e)

    def status_colors(vm_up: bool, es_up: bool) -> Tuple[str, str]:
        border = "#00cc66" if vm_up else "#ff3333"
        dot = "limegreen" if es_up else "red"
        return border, dot

    # ---------- Actions ----------

    def execute_action(ssh_user, ssh_pass, node_ip, action, es_user, es_pass, use_https):
        if not node_ip or not action:
            return "⚠️ Missing IP or action!"

        # Dynamically detect cluster name from each node
        def get_cluster_name(ip: str) -> str:
            ok, output = ssh_exec(
                ip,
                ssh_user,
                ssh_pass,
                "grep '^cluster.name' /etc/elasticsearch/elasticsearch.yml | cut -d ':' -f2 | tr -d ' '"
            )
            if ok and output:
                return output.strip()
            return "elasticsearch"  # fallback if not found

        cluster_name = get_cluster_name(node_ip)

        # command-based actions
        cmd_map = {
            "Start Node": "sudo systemctl start elasticsearch",
            "Stop Node": "sudo systemctl stop elasticsearch",
            "Restart Node": "sudo systemctl restart elasticsearch",
            "Reboot VM": "sudo reboot",
            "Node logs": f"sudo tail -n 100 /var/log/elasticsearch/{cluster_name}.log",
        }

        # non-command actions handled internally
        if action == "Go To Cluster Health":
            scheme = "https" if use_https else "http"
            port = int(f"92{ip_suffix_2(node_ip)}")
            url = f"{scheme}://{node_ip}:{port}/_cluster/health?pretty"
            curl_cmd = [
                "curl", "-s",
                "-u", f"{es_user}:{es_pass}",
                "--connect-timeout", "5",
                url
            ]
            if use_https:
                curl_cmd.append("-k")  # ignore cert validation for self-signed certs

            try:
                output = subprocess.check_output(curl_cmd, stderr=subprocess.STDOUT).decode()
                return f"📊 Cluster Health on {node_ip} ({cluster_name}):\n{'-'*60}\n{output}"
            except Exception as e:
                return f"❌ Curl failed ({e}"
            except Exception as e:
                return f"❌ Unexpected error: {e}"


        cmd = cmd_map.get(action)
        if not cmd:
            return f"❌ Unknown action: {action}"

        ok, msg = ssh_exec(node_ip, ssh_user, ssh_pass, cmd)
        action_name = action.capitalize()

        if action == "Node logs":
            node_name_cmd = "hostname"
            ok_name, vm_name = ssh_exec(node_ip, ssh_user, ssh_pass, node_name_cmd)
            vm_name = vm_name.strip() if ok_name and vm_name else node_ip

            prefix = f"📜 Last 100 lines from {cluster_name}.log on {vm_name} ({node_ip}):"
            content = msg if ok else f"❌ Error: {msg}"
            return f"{prefix}\n{'-'*60}\n{content}"

        return f"{'✅' if ok else '❌'} {action_name} on {node_ip}: {msg}"

            
    def open_cluster_health(es_user, es_pass, node_ip, use_https):
        """Return a URL to open cluster health view for the given node."""
        scheme = "https" if use_https else "http"
        port = int(f"92{ip_suffix_2(node_ip)}")
        return f"{scheme}://{es_user}:{es_pass}@{node_ip}:{port}/_cluster/health?pretty"

    def restart_all_nodes(ssh_user, ssh_pass):
        instances = shared_state.get("instances") or []
        if not instances:
            return "⚠️ No nodes available to restart."
        results = []
        for node in instances:
            name, ip = node.get("name", ""), node.get("ip", "")
            results.append(f"♻️ Restarting {name} ({ip})...")
            ok, msg = ssh_exec(ip, ssh_user, ssh_pass, "sudo systemctl restart elasticsearch")
            results.append(f"{'✅' if ok else '❌'} Restarted {name}: {msg}")
        return "\n".join(results)

    # ---------- Build UI ----------
    with gr.Blocks() as monitor_ui:

        gr.Markdown("### 🖥️ Cluster Monitor")

        with gr.Row():
            ssh_user = gr.Textbox(label="SSH Username", value="root", interactive=True)
            ssh_pass = gr.Textbox(label="SSH Password", interactive=True)

        with gr.Row():
            es_user = gr.Textbox(label="ES Username", value="elastic", interactive=True)
            es_pass = gr.Textbox(label="ES Password", interactive=True)
            use_https = gr.Checkbox(label="Use HTTPS for ES checks", value=False)

        refresh_btn = gr.Button("🔄 Refresh Status")
        clear_btn = gr.Button("🧹 Clear Logs")
        restart_all_btn = gr.Button("♻️ Restart All Nodes")

        logs = gr.Textbox(label="Logs", lines=12, interactive=False)

        node_rows = []
        MAX_NODES = 500

        # --- Each node row ---
        for _ in range(MAX_NODES):
            with gr.Row(visible=False) as row:
                node_html = gr.HTML("")
                node_ip_box = gr.Textbox(value="", visible=False)
                action_choice = gr.Dropdown(
                    ["Start Node", "Stop Node", "Restart Node", "Node logs" ,"Reboot VM", "Go To Cluster Health"],
                    label="Action",
                    interactive=True,
                )
                run_btn = gr.Button("🚀 Run")
                run_btn.click(
                    fn=execute_action,
                    inputs=[ssh_user, ssh_pass, node_ip_box, action_choice, es_user, es_pass, use_https],
                    outputs=[logs]
                )

            node_rows.append((row, node_html, node_ip_box))

        # ---------- Refresh Logic ----------
        def refresh_nodes(ssh_user_v, ssh_pass_v, es_user_v, es_pass_v, use_https_v):
            instances = shared_state.get("instances") or []
            total = len(instances)
            vis_updates, html_updates, ip_updates = [], [], []

            for idx, (row, node_html, ip_box) in enumerate(node_rows):
                if idx < total:
                    node = instances[idx]
                    name, ip = node.get("name", ""), node.get("ip", "")
                    vm_up = check_ssh_port(ip)
                    es_up = check_es_http(ip, es_user_v, es_pass_v, use_https_v) if vm_up else False
                    in_cluster = is_node_in_cluster(ip, es_user_v, es_pass_v, use_https_v) if es_up else False
                    
                    border, dot = status_colors(vm_up, es_up)
                    status_text = f"{'VM Online' if vm_up else 'VM Offline'} | {'ES Running' if es_up else 'ES Down'}"
                    if es_up:
                        status_text += f" | {'🟢 Joined Cluster' if in_cluster else '🟡 Not Joined'}"
                    dot_class = "pulse-dot online" if es_up else "pulse-dot offline"
                    html = f"""
                        <div style='border:2px solid {border};background:#181818;color:#e0e0e0;
                                    padding:12px;border-radius:10px;width:240px;'>
                            <span class='{dot_class}'></span>
                            <b>{name}</b><br>{ip}<br><small>{status_text}</small>
                        </div>
                    """
                    vis_updates.append(gr.update(visible=True))
                    html_updates.append(gr.update(value=html))
                    ip_updates.append(gr.update(value=ip))
                else:
                    vis_updates.append(gr.update(visible=False))
                    html_updates.append(gr.update(value=""))
                    ip_updates.append(gr.update(value=""))

            return vis_updates + html_updates + ip_updates + [f"✅ Refreshed {total} nodes."]

        def clear_logs():
            return ""

        # ---------- Bind Buttons ----------
        refresh_btn.click(
            fn=refresh_nodes,
            inputs=[ssh_user, ssh_pass, es_user, es_pass, use_https],
            outputs=[
                *[r[0] for r in node_rows],  # visibility
                *[r[1] for r in node_rows],  # HTML
                *[r[2] for r in node_rows],  # IP textboxes
                logs,
            ],
        )

        clear_btn.click(fn=clear_logs, outputs=[logs])
        restart_all_btn.click(fn=restart_all_nodes, inputs=[ssh_user, ssh_pass], outputs=[logs])

    return monitor_ui
