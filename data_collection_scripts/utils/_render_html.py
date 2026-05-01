import json
from pathlib import Path
from html import escape
import sys


ROOT_DIR = Path(__file__).resolve().parent.parent.parent
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))


import json
from html import escape

def build_table_from_dict(data):
    """Build table using only valid list columns with same length."""
    valid_cols = {}

    # Keep only list columns
    for k, v in data.items():
        if isinstance(v, list) and len(v) > 0:
            valid_cols[k] = v

    if not valid_cols:
        return None

    # Find most common length
    lengths = {}
    for v in valid_cols.values():
        lengths[len(v)] = lengths.get(len(v), 0) + 1

    target_len = max(lengths, key=lengths.get)

    # Filter columns with same length
    valid_cols = {k: v for k, v in valid_cols.items() if len(v) == target_len}

    if len(valid_cols) < 2:
        return None  # not enough columns for table

    # Build table
    html = "<table border='1' style='border-collapse: collapse;'>\n"

    # header
    html += "<tr>" + "".join(f"<th>{escape(k)}</th>" for k in valid_cols.keys()) + "</tr>\n"

    # rows
    for i in range(target_len):
        html += "<tr>"
        for col in valid_cols.values():
            html += f"<td>{escape(str(col[i]))}</td>"
        html += "</tr>\n"

    html += "</table><br>\n"
    return html


def render_json(data):
    html = ""

    if isinstance(data, dict):
        table = build_table_from_dict(data)
        if table:
            html += table
        else:
            for k, v in data.items():
                html += f"<h3>{escape(str(k))}</h3>\n"
                html += render_json(v)

    elif isinstance(data, list):
        for item in data:
            html += render_json(item)

    else:
        html += f"<p>{escape(str(data))}</p>\n"

    return html


def json_to_html(input_file, output_file):
    with open(input_file, "r", encoding="utf-8") as f:
        data = json.load(f)

    html = "<html><body>\n"
    html += render_json(data)
    html += "\n</body></html>"

    with open(output_file, "w", encoding="utf-8") as f:
        f.write(html)




# Example usage
json_to_html("database/demo_data/screener_data/TCS.json", "output.html")