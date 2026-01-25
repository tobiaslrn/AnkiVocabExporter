import json
from typing import Dict, List, Tuple


def escape_csv(value: str) -> str:
    value = value.replace("\n", " ")
    if any(ch in value for ch in [",", '"', "\n"]):
        value = '"' + value.replace('"', '""') + '"'
    return value


def write_json(
    path: str, sections: List[Tuple[str, List[Dict[str, str]]]], fieldnames: List[str]
) -> None:
    output = {}
    for title, rows in sections:
        key = title.lower().replace(" ", "_")
        output[key] = rows

    with open(path, "w", encoding="utf-8") as f:
        json.dump(output, f, ensure_ascii=False, indent=2)


def write_markdown(
    path: str, sections: List[Tuple[str, List[Dict[str, str]]]], fieldnames: List[str]
) -> None:
    with open(path, "w", encoding="utf-8") as f:
        for idx, (title, rows) in enumerate(sections):
            if idx > 0:
                f.write("\n\n")
            f.write(f"## {title}\n\n")
            if rows:
                f.write(",".join(fieldnames) + "\n")
                for row in rows:
                    values = [escape_csv(str(row.get(name, ""))) for name in fieldnames]
                    f.write(",".join(values) + "\n")
