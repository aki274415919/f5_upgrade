import paramiko
from typing import Dict


def ssh_cmd(host: str, user: str, password: str, cmd: str, timeout: int = 30) -> Dict[str, object]:
    """Execute `cmd` on remote host via SSH and return command details."""
    out = err = ""
    rc = 0
    try:
        client = paramiko.SSHClient()
        client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
        client.connect(host, username=user, password=password, timeout=timeout)
        stdin, stdout, stderr = client.exec_command(cmd)
        out = stdout.read().decode(errors="ignore")
        err = stderr.read().decode(errors="ignore")
        rc = stdout.channel.recv_exit_status()
        client.close()
    except Exception as exc:  # network errors, etc.
        err = str(exc)
        rc = 1
    return {"rc": rc, "out": out, "err": err, "cmd": cmd}
