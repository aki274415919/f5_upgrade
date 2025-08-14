try:
    import paramiko
except Exception:  # pragma: no cover - allows running without paramiko
    paramiko = None


def ssh_cmd(ip, user, pwd, cmd, timeout=60, logger=None):
    """Execute command over SSH and return result dict."""
    result = {"rc": 0, "out": "", "err": "", "cmd": cmd}
    if paramiko is None:
        result["rc"] = 1
        result["err"] = "paramiko not available"
        return result
    try:
        client = paramiko.SSHClient()
        client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
        client.connect(ip, username=user, password=pwd, timeout=timeout)
        stdin, stdout, stderr = client.exec_command(cmd, timeout=timeout)
        result["out"] = stdout.read().decode(errors="ignore")
        result["err"] = stderr.read().decode(errors="ignore")
        client.close()
    except Exception as e:
        result["rc"] = 1
        result["err"] = str(e)
        if logger:
            logger.error(f"[{ip}] {e}")
    return result
