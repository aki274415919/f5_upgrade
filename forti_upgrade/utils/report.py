import os
import re
import html
from datetime import datetime
from typing import List, Dict

import pandas as pd
from openpyxl import load_workbook
from openpyxl.styles import PatternFill

# Keyword regexes per requirement
KEYWORD_PATTERNS = {
    "software": r"FAIL|Error|install.*(fail|error)|image.*not.*found|HD\d+\.\d+.*(unavailable|inactive)|Volume.*(in-use|not.*ready)",
    "version": r"\bBIG-IP\b.*|\bBuild\b.*",
    "hardware": r"(fan|temperature).*(alarm|critical)|power.*(fail|off)",
    "memory": r"Memory.*(low|critical)|Swap.*(high|in use)",
    "cpu": r"(cpu.*usage|load).*(\d+)%|system load average",
    "disk": r"(disk\s+space|free).*?(\d+%)|error.*(md|raid)",
    "license": r"(expired|invalid|grace)",
    "cm-sync": r"Not All Devices Synced|Disconnected|Sync.*(Failed|Error)|\bIn Sync\b",
    "devicegrp": r"quorum.*(lost|0)",
}

ALL_KEYWORDS_RE = re.compile("|".join(f"({p})" for p in KEYWORD_PATTERNS.values()), re.IGNORECASE)


def find_keyword_hits(text: str, pattern: str | None = None) -> List[str]:
    """Return list of keyword matches using provided or global pattern."""
    regex = re.compile(pattern, re.IGNORECASE) if pattern else ALL_KEYWORDS_RE
    return list({m.group(0) for m in regex.finditer(text)})


def _highlight(text: str) -> str:
    """HTML-escape text and wrap keyword hits in <mark>."""
    if not text:
        return ""
    def repl(match: re.Match) -> str:
        return f"<mark>{html.escape(match.group(0))}</mark>"
    result = []
    last = 0
    for m in ALL_KEYWORDS_RE.finditer(text):
        result.append(html.escape(text[last:m.start()]))
        result.append(repl(m))
        last = m.end()
    result.append(html.escape(text[last:]))
    return "".join(result)


REVIEW_GUIDE = """<h2>Review Guide (what to check)</h2>
<pre>
1) software (tmsh show sys software)
   - Target volume state should be "available"/"inactive" before install; avoid installing into active/in-use volumes.
   - Image presence: verify image name matches plan; if "not found" or "inactive", investigate.
2) version (tmsh show sys version)
   - Current BIG-IP version/build; confirm matches maintenance policy and upgrade path.
3) hardware (tmsh show sys hardware)
   - Fans: statuses must be OK; any "alarm/critical" is a blocker.
   - Temperature: ensure within vendor normal; any "critical" flag is a blocker.
4) memory (tmsh show sys memory)
   - Free memory >= 20% preferred; "low/critical" indicates pressure. Swap "high/in use" suggests memory contention.
5) cpu (tmsh show sys cpu)
   - Sustained CPU > 85% is risky before upgrade; consider rescheduling.
6) disk (tmsh show sys disk)
   - Free space on relevant volumes >= 20%; any RAID/md errors must be resolved first.
7) license (tmsh show sys license)
   - Must not be expired; "grace" means close to expiry—renew before upgrade.
8) cm-sync (tmsh show cm sync-status)
   - Should be "In Sync". If "Not All Devices Synced"/"Disconnected"/"Failed", fix HA sync before upgrade.
9) device-group (tmsh show cm device-group)
   - Quorum must not be lost (quorum>0). Lost quorum blocks safe failover/sync.
</pre>"""


COLUMNS = [
    "stage",
    "name",
    "status",
    "severity",
    "keyword_hits",
    "command",
    "rc",
    "note",
    "raw_stdout",
    "raw_stderr",
]


def save_reports(rows: List[Dict[str, object]]) -> Dict[str, str]:
    """Save rows to HTML and Excel reports and return their paths."""
    os.makedirs("reports", exist_ok=True)
    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    html_path = os.path.join("reports", f"run_{ts}.html")
    xlsx_path = os.path.join("reports", f"run_{ts}.xlsx")

    df = pd.DataFrame(rows, columns=COLUMNS)
    df.to_excel(xlsx_path, index=False, sheet_name="summary")

    # Conditional formatting
    wb = load_workbook(xlsx_path)
    ws = wb["summary"]
    max_row = ws.max_row
    max_col = ws.max_column
    fills = {
        "ok": PatternFill(start_color="CCFFCC", end_color="CCFFCC", fill_type="solid"),
        "warn": PatternFill(start_color="FFFFCC", end_color="FFFFCC", fill_type="solid"),
        "error": PatternFill(start_color="FFCCCC", end_color="FFCCCC", fill_type="solid"),
    }
    keyword_fill = fills["warn"]
    for row in range(2, max_row + 1):
        severity = (ws.cell(row, 4).value or "").lower()
        fill = fills.get(severity)
        if fill:
            for col in range(1, max_col + 1):
                ws.cell(row, col).fill = fill
        if ws.cell(row, 5).value:
            ws.cell(row, 5).fill = keyword_fill
    wb.save(xlsx_path)

    # HTML generation
    with open(html_path, "w", encoding="utf-8") as f:
        f.write("<html><head><title>Run Report</title>\n")
        f.write("<style>table,th,td{border:1px solid #ccc;border-collapse:collapse;}th,td{padding:4px;}\n")
        f.write(".ok{background:#ccffcc;}.warn{background:#ffffcc;}.error{background:#ffcccc;}\n")
        f.write("details{margin-left:1em;} pre{background:#f5f5f5;padding:5px;}\n")
        f.write("</style></head><body>")
        f.write("<h1>Run Report</h1>\n<table>\n<tr>")
        for col in COLUMNS[:-2]:
            f.write(f"<th>{html.escape(col)}</th>")
        f.write("</tr>\n")
        for row in rows:
            cls = row.get("severity", "").lower()
            f.write(f"<tr class='{cls}'>")
            for col in COLUMNS[:-2]:
                val = row.get(col, "")
                f.write(f"<td>{html.escape(str(val))}</td>")
            f.write("</tr>\n<tr><td colspan='" + str(len(COLUMNS)-2) + "'>")
            f.write("<details><summary>STDOUT</summary><pre>" + _highlight(row.get("raw_stdout", "")) + "</pre></details>")
            f.write("<details><summary>STDERR</summary><pre>" + _highlight(row.get("raw_stderr", "")) + "</pre></details>")
            f.write("</td></tr>\n")
        f.write("</table>\n" + REVIEW_GUIDE + "\n</body></html>")

    return {"html": html_path, "xlsx": xlsx_path}
