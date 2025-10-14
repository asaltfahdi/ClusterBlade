import paramiko
from pathlib import Path
import time


def deploy_ssl_to_nodes(shared_state, ssh_user, ssh_pass, cert_password=None, progress_callback=None):
    """
    Deploy SSL certs from runtime/certificates/ to each node.
    Fixes chown permission issues (must be done as root).
    """

    instances = shared_state.get("instances", [])
    if not instances:
        return "❌ No instances found in shared state."

    results = []

    def run_ssh_command(ssh, command, sudo=False):
        """Executes a remote SSH command with proper privilege handling."""
        if sudo and not command.startswith("sudo"):
            command = f"sudo {command}"

        if progress_callback:
            progress_callback(f"🖥️ Running: {command}")

        stdin, stdout, stderr = ssh.exec_command(command)
        exit_status = stdout.channel.recv_exit_status()
        out = stdout.read().decode().strip()
        err = stderr.read().decode().strip()

        if exit_status != 0:
            raise RuntimeError(f"❌ Command failed ({exit_status}): {command}\n{err}")

        return out or "(no output)"

    # 🔍 Certificate source dir
    base_cert_dir = Path("runtime") / "certificates"
    if not base_cert_dir.exists():
        return f"❌ Certificate directory not found: {base_cert_dir}"

    for node in instances:
        name, ip = node["name"], node["ip"]
        try:
            log_line = f"\n🚀 Deploying SSL to node: {name} ({ip})"
            print(log_line)
            if progress_callback:
                progress_callback(log_line)

            ssh = paramiko.SSHClient()
            ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
            ssh.connect(ip, username=ssh_user, password=ssh_pass, timeout=20)

            remote_cert_dir = "/etc/elasticsearch/certs"
            sftp = ssh.open_sftp()

            # Ensure certs folder exists
            try:
                sftp.stat(remote_cert_dir)
            except FileNotFoundError:
                run_ssh_command(ssh, f"mkdir -p {remote_cert_dir}", sudo=True)
                run_ssh_command(ssh, f"chown elasticsearch:elasticsearch {remote_cert_dir}", sudo=True)

            # ✅ Upload CA and node certs
            for file in ["ca.pem", f"{name}.crt", f"{name}.key"]:
                local_file = base_cert_dir / file
                if not local_file.exists():
                    raise FileNotFoundError(f"Missing file: {local_file}")
                remote_file = f"{remote_cert_dir}/{file}"
                sftp.put(local_file.as_posix(), remote_file)
                run_ssh_command(ssh, f"chown elasticsearch:elasticsearch {remote_file}", sudo=True)
                run_ssh_command(ssh, f"chmod 640 {remote_file}", sudo=True)

            sftp.close()

            # 🧰 Rebuild keystore
            keystore_path = "/etc/elasticsearch/elasticsearch.keystore"
            run_ssh_command(ssh, f"rm -f {keystore_path}", sudo=True)
            run_ssh_command(ssh, "/usr/share/elasticsearch/bin/elasticsearch-keystore create", sudo=True)

            # Wait until keystore exists
            for _ in range(10):
                try:
                    sftp = ssh.open_sftp()
                    sftp.stat(keystore_path)
                    sftp.close()
                    break
                except FileNotFoundError:
                    time.sleep(0.5)
            else:
                raise RuntimeError("❌ Keystore not created after 5s wait.")

            # Add password if needed
            if cert_password:
                echo_cmd = (
                    f"bash -c \"echo '{cert_password}' | "
                    "/usr/share/elasticsearch/bin/elasticsearch-keystore "
                    "add -x xpack.security.transport.ssl.secure_key_passphrase\""
                )
                run_ssh_command(ssh, echo_cmd, sudo=True)
                out = run_ssh_command(
                    ssh, "/usr/share/elasticsearch/bin/elasticsearch-keystore list", sudo=True
                )
                if "xpack.security.transport.ssl.secure_key_passphrase" not in out:
                    raise RuntimeError("❌ Keystore entry missing after add!")

            # ✅ Restart service
            # if progress_callback:
            #     progress_callback(f"🔄 Restarting Elasticsearch on {name}...")
            # run_ssh_command(ssh, f"systemctl restart elasticsearch", sudo=True)

            log_line = f"✅ Successfully deployed SSL to {name} ({ip})"
            print(log_line)
            if progress_callback:
                progress_callback(log_line)
            results.append(log_line)

            ssh.close()

        except Exception as e:
            err_msg = f"❌ Failed on {name} ({ip}): {e}"
            print(err_msg)
            if progress_callback:
                progress_callback(err_msg)
            results.append(err_msg)

    return "\n".join(results)
