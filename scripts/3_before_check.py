import argparse
import sys
from pathlib import Path

sys.path.append(str(Path(__file__).resolve().parents[1]))

from f5_upgrade.utils.logging import setup_logging
from f5_upgrade.utils.ssh import ssh_cmd
from f5_upgrade.utils.report import save_html, save_excel, analyse
from f5_upgrade.utils.messages import MESSAGES


def get_user_input_gui():
    import tkinter as tk
    from tkinter import filedialog, simpledialog, messagebox
    import sys as _sys

    root = tk.Tk()
    root.withdraw()

    firmware_path = filedialog.askopenfilename(
        title="Select F5 Firmware ISO (选择F5固件ISOファイルを選択)",
        filetypes=[("ISO Files", "*.iso")]
    )
    if not firmware_path:
        messagebox.showerror("Error", "No firmware selected. Exit.")
        _sys.exit()

    primary_ip = simpledialog.askstring("F5 Management IP", "Enter the primary F5 management IP:")
    if not primary_ip:
        messagebox.showerror("Error", "Primary IP required. Exit.")
        _sys.exit()

    secondary_ip = simpledialog.askstring("F5 Secondary IP", "Enter standby/secondary F5 IP (leave blank if standalone):")
    username = simpledialog.askstring("SSH Username", "Enter SSH username:")
    password = simpledialog.askstring("SSH Password", "Enter SSH password:", show="*")
    if not username or not password:
        messagebox.showerror("Error", "Username/password required. Exit.")
        _sys.exit()

    return firmware_path, primary_ip, secondary_ip, username, password


CHECK_COMMANDS = [
    "tmsh show sys hardware",
    "tmsh show sys disk",
    "tmsh show sys raid",
    "tmsh show sys environment",
    "tmsh show sys performance",
    "tmsh show cm failover-status",
    "tmsh show sys license",
    "tmsh show sys software",
    "tmsh show cm sync-status",
    "tmsh show ltm virtual",
    "tmsh show vcmp guest",
    "tmsh show sys mcp-state field-fmt",
    "tmsh load sys config verify",
    "tmsh list ltm rule",
    "tmsh list sys file ssl-cert",
    "tmsh list /sys crypto cert",
    "tmsh save /sys config file preupgrade_check.scf",
]


def check_deprecated_commands(ip, user, pwd, logger):
    cmd = (
        "cat /config/preupgrade_check.scf | "
        "egrep -i 'SSL::|HTTP::header remove All|class match|matchclass|LB::reselect'"
    )
    result = ssh_cmd(ip, user, pwd, cmd, logger=logger)
    return result["out"]


def run():
    parser = argparse.ArgumentParser(description="F5 upgrade pre-checks")
    parser.add_argument("--mock", action="store_true", help="generate mock outputs")
    args = parser.parse_args()

    logger, log_file = setup_logging()
    html_path = log_file.replace(".log", ".html")
    xlsx_path = log_file.replace(".log", ".xlsx")

    if args.mock:
        firmware_path = ""
        primary_ip = "192.0.2.1"
        secondary_ip = ""
        username = "admin"
        password = "password"
    else:
        firmware_path, primary_ip, secondary_ip, username, password = get_user_input_gui()

    ip_list = [ip for ip in [primary_ip, secondary_ip] if ip]
    results = []
    idx = 1
    for ip in ip_list:
        for cmd in CHECK_COMMANDS:
            if args.mock:
                mock_outputs = {
                    "tmsh show sys disk": "sda1 90% warn",
                }
                out = mock_outputs.get(cmd, f"simulated output for {cmd}")
                result = {"rc": 0, "out": out, "err": "", "cmd": cmd}
            else:
                result = ssh_cmd(ip, username, password, cmd, logger=logger)
            out = result["out"]
            logger.info(f"[{ip}]$ {cmd}\n{out}")
            _, msg = analyse(cmd, out)
            results.append([idx, cmd, ip, out, msg["ja"]])
            idx += 1
        if args.mock:
            out = ""
        else:
            out = check_deprecated_commands(ip, username, password, logger)
        logger.info(f"[{ip}] deprecated command check\n{out}")
        msg = MESSAGES["default_warning"] if out.strip() else MESSAGES["default_ok"]
        results.append([idx, "deprecated command check", ip, out, msg["ja"]])
        idx += 1

    save_excel(results, xlsx_path)
    save_html(results, html_path)
    logger.info(f"HTML report saved to {html_path}")
    logger.info(f"Excel report saved to {xlsx_path}")


if __name__ == "__main__":
    run()
