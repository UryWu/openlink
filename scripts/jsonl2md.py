import argparse
import json
from pathlib import Path


def render_value(value, indent=0):
    prefix = "  " * indent
    if isinstance(value, dict):
        lines = []
        for k, v in value.items():
            if isinstance(v, (dict, list)):
                lines.append(f"{prefix}- **{k}**:")
                lines.append(render_value(v, indent + 1))
            else:
                val_str = "null" if v is None else str(v)
                lines.append(f"{prefix}- **{k}**: {val_str}")
        return "\n".join(lines)
    if isinstance(value, list):
        lines = []
        for item in value:
            if isinstance(item, (dict, list)):
                lines.append(f"{prefix}-")
                lines.append(render_value(item, indent + 1))
            else:
                val_str = "null" if item is None else str(item)
                lines.append(f"{prefix}- {val_str}")
        return "\n".join(lines)
    return f"{prefix}{'null' if value is None else str(value)}"


def convert(input_path, output_path):
    with open(input_path, "r", encoding="utf-8") as f:
        lines = [line.strip() for line in f if line.strip()]

    sections = []
    for idx, line in enumerate(lines, 1):
        try:
            obj = json.loads(line)
        except json.JSONDecodeError as e:
            sections.append(f"## Line {idx}\n\n*JSON parse error: {e}\n")
            continue

        title = obj.get("title") or obj.get("name") or obj.get("id") or obj.get("convId") or f"Entry {idx}"
        body = [f"## {title}\n"]
        for k, v in obj.items():
            if k in ("title", "name", "id", "convId") and not isinstance(v, (dict, list)):
                continue
            if isinstance(v, (dict, list)):
                body.append(f"**{k}**:\n\n{render_value(v)}\n")
            elif isinstance(v, str) and "\n" in v:
                body.append(f"**{k}**:\n\n```\n{v}\n``b\n")
            else:
                val_str = "null" if v is None else str(v)
                body.append(f"**{k}**: {val_str}\n")
        sections.append("\n".join(body))

    with open(output_path, "w", encoding="utf-8") as f:
        f.write("\n---\n\n".join(sections))
    print(f"Written {len(lines)} entries to {output_path}")


def main():
    parser = argparse.ArgumentParser(description="Convert JSONL to Markdown")
    parser.add_argument("-i", "--input", required=True, help="Input JSONL file")
    parser.add_argument("-o", "--output", help="Output Markdown file")
    args = parser.parse_args()

    import os
    if not os.path.exists(args.input):
        parser.error(f"Input file not found: {args.input}")

    output = args.output or os.path.splitext(args.input)[0] + ".md"
    convert(args.input, output)


if __name__ == "__main__":
    main()
