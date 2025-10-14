import paramiko

def execute_remote(ip, username, password, commands, port=22):
    logs = []
    ssh = paramiko.SSHClient()
    ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    ssh.connect(ip, username=username, password=password, port=port)

    for cmd in commands:
        logs.append(f"$ {cmd}")
        stdin, stdout, stderr = ssh.exec_command(cmd)
        out, err = stdout.read().decode(), stderr.read().decode()
        if out: logs.append(out)
        if err: logs.append(err)
    ssh.close()
    return "\n".join(logs)
