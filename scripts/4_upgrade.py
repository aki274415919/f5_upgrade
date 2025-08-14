import sys
from pathlib import Path

sys.path.append(str(Path(__file__).resolve().parents[1]))

from f5_upgrade.utils.logging import setup_logging
from f5_upgrade.utils.ssh import ssh_cmd


def select_image():
    return input("Firmware image path: ").strip()


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


def run():
    logger, _ = setup_logging()
    ip = input("Device IP: ").strip()
    user = input("Username: ")
    pwd = input("Password: ")
    image = select_image()
    validate_device(ip, user, pwd, logger)
    backup_config(ip, user, pwd, logger)
    install_image(ip, user, pwd, image, logger)
    post_check(ip, user, pwd, logger)
    logger.info("Upgrade workflow completed")


if __name__ == "__main__":
    run()
