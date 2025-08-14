from getpass import getpass
from forti_upgrade.precheck import run_precheck
from forti_upgrade.utils.logging import setup_logging
from forti_upgrade.utils.report import save_reports


def main() -> None:
    setup_logging()
    ip_list = [ip.strip() for ip in input("Enter F5 IPs (comma-separated): ").split(",") if ip.strip()]
    user = input("Username: ")
    password = getpass("Password: ")
    rows = []
    for ip in ip_list:
        rows.extend(run_precheck(ip, user, password))
    paths = save_reports(rows)
    print(f"Reports written to: {paths['html']} and {paths['xlsx']}")


if __name__ == "__main__":
    main()
