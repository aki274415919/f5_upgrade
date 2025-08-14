from pathlib import Path
import re
try:
    from openpyxl import Workbook
    from openpyxl.styles import PatternFill
except Exception:  # pragma: no cover - allow running without openpyxl
    Workbook = None
    PatternFill = None


def apply_highlight(text, rules):
    def repl(match):
        word = match.group(0)
        color = rules[word.lower()]
        return f"<mark style='background-color:{color}'>{word}</mark>"
    pattern = re.compile("|".join(re.escape(k) for k in rules), re.IGNORECASE)
    return pattern.sub(lambda m: repl(m), text)


def save_html(rows, path, multilingual=True):
    Path(path).parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        f.write("<html><meta charset='utf-8'><body>\n")
        f.write("<table border='1' cellspacing='0' cellpadding='5'>\n")
        f.write("<tr><th>序号/番号/No</th><th>命令/コマンド/Command</th><th>返回值/出力/Output</th><th>需要关注的内容/要確認事項/Items to Review</th></tr>\n")
        for row in rows:
            focus = "<br/>".join([row["focus"][lang] for lang in ("zh", "ja", "en")])
            f.write(
                f"<tr><td>{row['index']}</td><td>{row['command']}</td><td>{row['output']}</td><td>{focus}</td></tr>\n"
            )
        f.write("</table></body></html>")


def save_excel(rows, path, highlight_rules=None):
    if Workbook is None:
        import csv
        with open(path, "w", newline="", encoding="utf-8") as f:
            writer = csv.writer(f)
            writer.writerow(["序号", "命令行", "返回值", "备注", "需要关注的内容（日文）"])
            for row in rows:
                writer.writerow([row["index"], row["command"], row["raw_output"], "", row["focus"]["ja"]])
        return
    wb = Workbook()
    ws = wb.active
    ws.append(["序号", "命令行", "返回值", "备注", "需要关注的内容（日文）"])
    colors = {
        "critical": "FFC7CE",  # red
        "warning": "FFEB9C",  # yellow
        "normal": "C6EFCE",   # green
    }
    for row in rows:
        ws.append([row["index"], row["command"], row["raw_output"], "", row["focus"]["ja"]])
        fill = PatternFill(start_color=colors[row["severity"]], end_color=colors[row["severity"]], fill_type="solid")
        for cell in ws[ws.max_row]:
            cell.fill = fill
    wb.save(path)
