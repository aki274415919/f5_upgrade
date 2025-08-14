import logging
import re
from typing import List, Dict

from .utils.ssh import ssh_cmd
from .utils.report import KEYWORD_PATTERNS, find_keyword_hits

ERROR_TERMS = re.compile(
    r"expired|invalid|grace|Not All Devices Synced|Disconnected|Failed|Error|alarm|critical|unavailable|inactive",
    re.IGNORECASE,
)


def run_precheck(ip: str, user: str, password: str) -> List[Dict[str, object]]:
    """Run predefined read-only tmsh commands and return report rows."""
    commands = [
        ("software", "tmsh show sys software"),
        ("version", "tmsh show sys version"),
        ("hardware", "tmsh show sys hardware"),
        ("memory", "tmsh show sys memory"),
        ("cpu", "tmsh show sys cpu"),
        ("disk", "tmsh show sys disk"),
        ("license", "tmsh show sys license"),
        ("cm-sync", "tmsh show cm sync-status"),
        ("device-group", "tmsh show cm device-group"),
    ]
    rows: List[Dict[str, object]] = []
    logger = logging.getLogger(__name__)

    for name, cmd in commands:
        res = ssh_cmd(ip, user, password, cmd)
        out, err, rc = res["out"], res["err"], res["rc"]
        pattern = KEYWORD_PATTERNS.get(name)
        hits = find_keyword_hits(out + err, pattern)
        keyword_hits = "; ".join(hits)
        if rc != 0 or (keyword_hits and ERROR_TERMS.search(keyword_hits)):
            severity = "error"
        elif keyword_hits:
            severity = "warn"
        else:
            severity = "ok"
        status = "ok" if rc == 0 else "fail"
        note = "no noteworthy keywords" if not keyword_hits else "keywords found"
        if rc != 0 and err:
            note = err.strip().splitlines()[-1]
        row = {
            "stage": "precheck",
            "name": name,
            "status": status,
            "severity": severity,
            "keyword_hits": keyword_hits,
            "command": cmd,
            "rc": rc,
            "note": note,
            "raw_stdout": out,
            "raw_stderr": err,
        }
        rows.append(row)
        logger.info("[%s] %s rc=%s severity=%s hits=%s", ip, name, rc, severity, keyword_hits)
    return rows
