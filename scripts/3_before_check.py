import argparse
import sys
from pathlib import Path

sys.path.append(str(Path(__file__).resolve().parents[1]))

from f5_upgrade.utils.logging import setup_logging
from f5_upgrade.utils.ssh import ssh_cmd
from f5_upgrade.utils.report import save_html, save_excel, apply_highlight
from f5_upgrade.utils.messages import MESSAGES

ERROR_KEYS = ["expired", "invalid", "fail", "error", "critical", "alarm", "unavailable",
              "inactive", "offline", "lost", "unreachable", "down", "degraded"]
WARN_KEYS = ["warn", "deprecated", "high", "exceeded", "mismatch"]

COLOR_MAP = {k: "#ffb3b3" for k in ERROR_KEYS}
COLOR_MAP.update({k: "#fff4b3" for k in WARN_KEYS})

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
    "tmsh save /sys config file preupgrade_check.scf && cat /config/preupgrade_check.scf | egrep -i 'SSL::|HTTP::header remove All|class match|matchclass|LB::reselect'",
]


def analyse(text):
    lt = text.lower()
    severity = "normal"
    focus = MESSAGES["default_ok"]
    if any(k in lt for k in ERROR_KEYS):
        severity = "critical"
        focus = MESSAGES["default_warning"]
    elif any(k in lt for k in WARN_KEYS):
        severity = "warning"
        focus = MESSAGES["default_warning"]
    return severity, focus


def run():
    parser = argparse.ArgumentParser(description="F5 upgrade pre-checks")
    parser.add_argument("--mock", action="store_true", help="generate mock outputs")
    args = parser.parse_args()

    logger, log_file = setup_logging()
    html_path = log_file.replace(".log", ".html")
    xlsx_path = log_file.replace(".log", ".xlsx")

    ip = input("Device IP: ").strip()
    user = input("Username: ")
    pwd = input("Password: ")

    rows = []
    for idx, cmd in enumerate(CHECK_COMMANDS, 1):
        if args.mock:
            mock_outputs = {
                "tmsh show sys disk": "sda1 90% warn",
                "tmsh show sys license": "license valid",
            }
            out = mock_outputs.get(cmd, f"simulated output for {cmd}")
            result = {"rc": 0, "out": out, "err": "", "cmd": cmd}
        else:
            result = ssh_cmd(ip, user, pwd, cmd, logger=logger)
        out = result["out"]
        logger.info(f"$ {cmd}\n{out}")
        severity, focus = analyse(out)
        highlight_rules = {k: ("#ff6b6b" if k in ERROR_KEYS else "#ffd93b") for k in COLOR_MAP if k in out.lower()}
        highlighted = apply_highlight(out, highlight_rules) if highlight_rules else out
        rows.append({
            "index": idx,
            "command": cmd,
            "output": highlighted,
            "raw_output": out,
            "focus": focus,
            "severity": severity,
        })

    save_html(rows, html_path)
    save_excel(rows, xlsx_path)
    logger.info(f"HTML report saved to {html_path}")
    logger.info(f"Excel report saved to {xlsx_path}")


if __name__ == "__main__":
    run()
