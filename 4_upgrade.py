from getpass import getpass
from forti_upgrade.precheck import run_precheck
from forti_upgrade.utils.logging import setup_logging
from forti_upgrade.utils.report import save_reports, find_keyword_hits
from forti_upgrade.utils.ssh import ssh_cmd


def aggregate_precheck(rows):
    out = "\n".join(r["raw_stdout"] for r in rows)
    err = "\n".join(r["raw_stderr"] for r in rows)
    rc = max(r["rc"] for r in rows) if rows else 0
    hits = "; ".join(filter(None, (r["keyword_hits"] for r in rows)))
    return out, err, rc, hits


def main() -> None:
    setup_logging()
    ip = input("F5 IP: ").strip()
    user = input("Username: ")
    password = getpass("Password: ")
    image = input("Image name (e.g., BIGIP.iso): ")
    volume = input("Target volume (e.g., HD1.2): ")
    do_backup = input("Backup UCS before install? (y/N): ").lower().startswith("y")

    rows = []

    pre_rows = run_precheck(ip, user, password)
    pre_out, pre_err, pre_rc, pre_hits = aggregate_precheck(pre_rows)
    rows.append({
        "stage": "upgrade",
        "name": "validate_plan",
        "status": "ok" if pre_rc == 0 else "fail",
        "severity": "error" if pre_rc != 0 else "ok",
        "keyword_hits": pre_hits,
        "command": "precheck suite",
        "rc": pre_rc,
        "note": "pre-validation run",
        "raw_stdout": pre_out,
        "raw_stderr": pre_err,
    })

    if do_backup:
        cmd = "tmsh save sys ucs /var/local/ucs/backup.ucs"
        res = ssh_cmd(ip, user, password, cmd)
        hits = "; ".join(find_keyword_hits(res["out"] + res["err"]))
        rows.append({
            "stage": "upgrade",
            "name": "backup_ucs",
            "status": "ok" if res["rc"] == 0 else "fail",
            "severity": "error" if res["rc"] != 0 else "ok",
            "keyword_hits": hits,
            "command": cmd,
            "rc": res["rc"],
            "note": "backup ucs",
            "raw_stdout": res["out"],
            "raw_stderr": res["err"],
        })

    cmd = f"tmsh install sys software image {image} volume {volume}"
    res = ssh_cmd(ip, user, password, cmd)
    hits = "; ".join(find_keyword_hits(res["out"] + res["err"]))
    rows.append({
        "stage": "upgrade",
        "name": "install_image",
        "status": "ok" if res["rc"] == 0 else "fail",
        "severity": "error" if res["rc"] != 0 else "ok",
        "keyword_hits": hits,
        "command": cmd,
        "rc": res["rc"],
        "note": "install image",
        "raw_stdout": res["out"],
        "raw_stderr": res["err"],
    })

    post_rows = run_precheck(ip, user, password)
    post_out, post_err, post_rc, post_hits = aggregate_precheck(post_rows)
    rows.append({
        "stage": "upgrade",
        "name": "post_checks",
        "status": "ok" if post_rc == 0 else "fail",
        "severity": "error" if post_rc != 0 else "ok",
        "keyword_hits": post_hits,
        "command": "precheck suite",
        "rc": post_rc,
        "note": "post-validation run",
        "raw_stdout": post_out,
        "raw_stderr": post_err,
    })

    paths = save_reports(rows)
    print(f"Reports written to: {paths['html']} and {paths['xlsx']}")


if __name__ == "__main__":
    main()
