import paramiko
from pathlib import Path
from clusterblade.elastic.config_gen import render_es_config


def deploy_cluster(shared_state, ssh_user, ssh_pass, progress_callback=None):
    """
    Deploy Elasticsearch YAML configs to all nodes in the cluster.
    - Renders elasticsearch.yml via Jinja2 template
    - Uploads to node via SSH
    - Restarts Elasticsearch (non-blocking)
    """

    cluster_name = shared_state.get("cluster_name", "es-cluster")
    enable_ssl = shared_state.get("enable_ssl", True)
    enable_http = shared_state.get("enable_http", False)
    http_groups = shared_state.get("http_groups", [])

    grouped = shared_state.get("grouped_nodes", {})
    masters = grouped.get("master", []) or grouped.get("Master", [])
    all_nodes = [n for nodes in grouped.values() for n in nodes]

    logs = []
    for node in all_nodes:
        ip = node["ip"]
        node_name = node["name"]

        try:
            logs.append(f"⚙️ Deploying config to {node_name} ({ip})...")

            # 1️⃣ Render elasticsearch.yml locally
            cfg_path = render_es_config(
                cluster_name,
                node,
                masters,
                enable_ssl=enable_ssl,
                enable_http=enable_http,
                http_groups=http_groups,
            )
            logs.append(f"📝 Generated config for {node_name} at {cfg_path}")

            # 2️⃣ Connect via SSH
            ssh = paramiko.SSHClient()
            ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
            ssh.connect(ip, username=ssh_user, password=ssh_pass, timeout=10)
            sftp = ssh.open_sftp()

            # 3️⃣ Upload config
            remote_dir = "/etc/elasticsearch/"
            remote_path = f"{remote_dir}elasticsearch.yml"
            try:
                sftp.mkdir(remote_dir)
            except IOError:
                pass  # already exists

            sftp.put(cfg_path, remote_path)
            logs.append(f"📤 Uploaded config → {ip}:{remote_path}")

            # 4️⃣ Restart Elasticsearch (non-blocking)
            restart_cmds = [
                "sudo systemctl daemon-reload",
                # Start restart in background — doesn’t wait
                "nohup sudo systemctl restart elasticsearch >/dev/null 2>&1 &",
                "sudo systemctl enable elasticsearch",
            ]

            for cmd in restart_cmds:
                ssh.exec_command(cmd)

            logs.append(f"🚀 Restart triggered for {node_name} — moving to next node.")
            logs.append(f"✅ Node {node_name} ({ip}) processed.\n")
            logs.append("#----------------------------------------------------#\n")

            if progress_callback:
                progress_callback(f"✅ {node_name} done")

            sftp.close()
            ssh.close()

        except Exception as e:
            logs.append(f"❌ Failed on {node_name} ({ip}): {e}")

    logs.append("🎯 Deployment completed for all nodes (without waiting for restart).")
    return "\n".join(logs)
