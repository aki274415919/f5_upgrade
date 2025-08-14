import sys
from pathlib import Path

sys.path.append(str(Path(__file__).resolve().parents[1]))

from f5_upgrade.utils.logging import setup_logging
from f5_upgrade.utils.ssh import ssh_cmd


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


def validate_device(ip, user, pwd, logger):
    logger.info(f"Validating device {ip}")
    ssh_cmd(ip, user, pwd, "tmsh show sys hardware", logger=logger)


def backup_config(ip, user, pwd, logger):
    logger.info("Backing up configuration")
    ssh_cmd(ip, user, pwd, "tmsh save /sys ucs preupgrade.ucs", logger=logger)


def install_image(ip, user, pwd, image, logger):
    logger.info("Installing image")
    ssh_cmd(ip, user, pwd, f"tmsh install sys software image {image}", logger=logger)


def post_check(ip, user, pwd, logger):
    logger.info("Post upgrade validation")
    ssh_cmd(ip, user, pwd, "tmsh show sys software", logger=logger)


def run(ip, user, pwd, image):
    logger, _ = setup_logging()
    validate_device(ip, user, pwd, logger)
    backup_config(ip, user, pwd, logger)
    install_image(ip, user, pwd, image, logger)
    post_check(ip, user, pwd, logger)
    logger.info("Upgrade workflow completed")


if __name__ == "__main__":
    firmware_path, primary_ip, secondary_ip, username, password = get_user_input_gui()
    run(primary_ip, username, password, firmware_path)
