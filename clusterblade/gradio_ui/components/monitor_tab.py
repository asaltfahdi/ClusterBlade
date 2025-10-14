import gradio as gr
import requests
import paramiko
import socket
from typing import Tuple
import os
REQUEST_TIMEOUT = 3  # seconds


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

    def check_es_http(ip: str, user: str, pwd: str) -> bool:
        port = int(f"92{ip_suffix_2(ip)}")
        url = f"http://{ip}:{port}"
        try:
            r = requests.get(url, auth=(user, pwd), timeout=REQUEST_TIMEOUT)
            return r.status_code == 200
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

    def execute_action(ssh_user, ssh_pass, node_ip, action):
        print(f"Action requested: {action} on {node_ip}")  # debug
        if not node_ip or not action:
            return "⚠️ Missing IP or action!"
        cmd_map = {
            "start": "sudo systemctl start elasticsearch",
            "stop": "sudo systemctl stop elasticsearch",
            "restart": "sudo systemctl restart elasticsearch",
            "reboot": "sudo reboot",
        }
        cmd = cmd_map.get(action)
        if not cmd:
            return f"❌ Unknown action: {action}"
        ok, msg = ssh_exec(node_ip, ssh_user, ssh_pass, cmd)
        action_name = action.capitalize()
        return f"{'✅' if ok else '❌'} {action_name} on {node_ip}: {msg}"

    # ---------- Build UI ----------

    with gr.Blocks() as monitor_ui:
     
        gr.Markdown("### 🖥️ Cluster Monitor")

        with gr.Row():
            ssh_user = gr.Textbox(label="SSH Username", value="root", interactive=True)
            ssh_pass = gr.Textbox(label="SSH Password", interactive=True)
        with gr.Row():
            es_user = gr.Textbox(label="ES Username", value="elastic", interactive=True)
            es_pass = gr.Textbox(label="ES Password", interactive=True)

        refresh_btn = gr.Button("🔄 Refresh Status")
        clear_btn = gr.Button("🧹 Clear Logs")

        logs = gr.Textbox(label="Logs", lines=10, interactive=False)

        node_rows = []
        MAX_NODES = 500

        # --- Each node row ---
        for _ in range(MAX_NODES):
            with gr.Row(visible=False) as row:
                node_html = gr.HTML("")
                node_ip_box = gr.Textbox(value="", visible=False)  # ← real IP carrier
                action_choice = gr.Dropdown(
                    ["start", "stop", "restart", "reboot"],
                    label="Action",
                    interactive=True
                )
                run_btn = gr.Button("🚀 Run")

                run_btn.click(
                    fn=execute_action,
                    inputs=[ssh_user, ssh_pass, node_ip_box, action_choice],
                    outputs=[logs],
                )
            node_rows.append((row, node_html, node_ip_box))

        # ---------- Refresh Logic ----------
        def refresh_nodes(ssh_user_v, ssh_pass_v, es_user_v, es_pass_v):
            """Rebuild statuses & update IP boxes."""
            instances = shared_state.get("instances") or []
            total = len(instances)
            vis_updates, html_updates, ip_updates = [], [], []

            for idx, (row, node_html, ip_box) in enumerate(node_rows):
                if idx < total:
                    node = instances[idx]
                    name, ip = node.get("name", ""), node.get("ip", "")
                    vm_up = check_ssh_port(ip)
                    es_up = check_es_http(ip, es_user_v, es_pass_v) if vm_up else False
                    border, dot = status_colors(vm_up, es_up)
                    status_text = f"{'VM Online' if vm_up else 'VM Offline'} | {'ES Running' if es_up else 'ES Down'}"
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
                    ip_updates.append(gr.update(value=ip))  # ✅ set IP here
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
            inputs=[ssh_user, ssh_pass, es_user, es_pass],
            outputs=[
                *[r[0] for r in node_rows],  # visibility
                *[r[1] for r in node_rows],  # HTML
                *[r[2] for r in node_rows],  # IP textboxes
                logs,
            ],
        )

        clear_btn.click(fn=clear_logs, outputs=[logs])

    return monitor_ui
