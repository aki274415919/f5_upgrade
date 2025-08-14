import paramiko
import time
import logging
from datetime import datetime

# 日志初始化
now = datetime.now().strftime("%Y%m%d_%H%M%S")
LOG_FILE = f"F5_Precheck_{now}.log"
logging.basicConfig(filename=LOG_FILE, level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
console = logging.StreamHandler()
console.setLevel(logging.INFO)
formatter = logging.Formatter("[%(asctime)s] %(message)s")
console.setFormatter(formatter)
logging.getLogger("").addHandler(console)

def log(msg):
    logging.info(msg)

def ssh_cmd(ip, user, pwd, cmd):
    out, err = "", ""
    try:
        c = paramiko.SSHClient()
        c.set_missing_host_key_policy(paramiko.AutoAddPolicy())
        c.connect(ip, username=user, password=pwd, timeout=15)
        log(f"[{ip}] >> {cmd}")
        stdin, stdout, stderr = c.exec_command(cmd)
        out = stdout.read().decode(errors='ignore')
        err = stderr.read().decode(errors='ignore')
        log(f"[{ip}] << STDOUT:\n{out.strip()}")
        if err.strip():
            log(f"[{ip}] << STDERR:\n{err.strip()}")
        c.close()
    except Exception as e:
        log(f"[{ip}] !! Exception: {str(e)}")
    return out, err

def check_deprecated_commands(ip, user, pwd):
    log(f"[{ip}] --- Deprecated Command Check ---")
    cmd = "cat /config/preupgrade_check.scf | egrep -i 'SSL::|HTTP::header remove All|class match|matchclass|LB::reselect'"
    out, err = ssh_cmd(ip, user, pwd, cmd)
    if not out.strip():
        log(f"[{ip}] No deprecated commands found in SCF.")
    else:
        log(f"[{ip}] Deprecated commands detected. Please review above output.")

def run_checks(ip, user, pwd):
    log(f"\n========== Starting checks on {ip} ==========")
    commands = [
        ("Platform Info", "tmsh show sys hardware"),
        ("Disk Usage", "tmsh show sys disk"),
        ("RAID", "tmsh show sys raid"),
        ("Environment (Fan/Temp/Power)", "tmsh show sys environment"),
        ("CPU/Memory", "tmsh show sys performance"),
        ("Failover Status", "tmsh show cm failover-status"),
        ("License", "tmsh show sys license"),
        ("Software", "tmsh show sys software"),
        ("Sync Status", "tmsh show cm sync-status"),
        ("Virtual Servers", "tmsh show ltm virtual"),
        ("vCMP Guests", "tmsh show vcmp guest"),
        ("MCP Pending", "tmsh show sys mcp-state field-fmt"),
        ("Config Syntax Check", "tmsh load sys config verify"),
        ("iRules Listing", "tmsh list ltm rule"),
        ("SSL Certificate Listing", "tmsh list sys file ssl-cert"),
        ("Export SCF Config", "tmsh save /sys config file preupgrade_check.scf"),
    ]
    for label, cmd in commands:
        log(f"[{ip}] --- {label} ---")
        ssh_cmd(ip, user, pwd, cmd)
    check_deprecated_commands(ip, user, pwd)

def main():
    print("Enter F5 IPs (comma-separated):")
    ip_list = input("IPs: ").split(",")
    ip_list = [ip.strip() for ip in ip_list if ip.strip()]

    user = input("Username: ")
    pwd = input("Password: ")

    for ip in ip_list:
        run_checks(ip, user, pwd)

    log("\n=== All checks completed. Log saved to: " + LOG_FILE + " ===")

if __name__ == "__main__":
    main()
