#!/usr/bin/env python3
"""MARCXML -> ISBD bibliography -> PDF/HTML exporter.

Focused fields: 020, 090, 100, 111, 245, 250, 260, 300, 490, 650
"""
from __future__ import annotations

import argparse
import html
import re
import subprocess
import sys
import xml.etree.ElementTree as ET
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, Iterable, List, Tuple

NS = {"marc": "http://www.loc.gov/MARC21/slim"}


@dataclass
class Record:
    control_001: str
    fields: Dict[str, List[Dict[str, List[str]]]]


def normalize_text(value: str) -> str:
    value = re.sub(r"\s+", " ", value or "").strip()
    return value.rstrip("/,:; ")


def parse_marcxml(path: Path) -> Iterable[Record]:
    tree = ET.parse(path)
    root = tree.getroot()
    for rec in root.findall("marc:record", NS):
        control_001 = ""
        fields: Dict[str, List[Dict[str, List[str]]]] = {}
        for c in rec.findall("marc:controlfield", NS):
            if c.attrib.get("tag") == "001":
                control_001 = normalize_text(c.text or "")
        for d in rec.findall("marc:datafield", NS):
            tag = d.attrib.get("tag", "")
            submap: Dict[str, List[str]] = {}
            for s in d.findall("marc:subfield", NS):
                code = s.attrib.get("code", "")
                submap.setdefault(code, []).append(normalize_text(s.text or ""))
            fields.setdefault(tag, []).append(submap)
        yield Record(control_001=control_001, fields=fields)


def first_subfield(fields: Dict[str, List[Dict[str, List[str]]]], tag: str, code: str) -> str:
    for datafield in fields.get(tag, []):
        vals = datafield.get(code, [])
        for v in vals:
            if v:
                return v
    return ""


def all_subfields(fields: Dict[str, List[Dict[str, List[str]]]], tag: str, code: str) -> List[str]:
    out: List[str] = []
    for datafield in fields.get(tag, []):
        out.extend(v for v in datafield.get(code, []) if v)
    return out


def build_isbd(record: Record) -> str:
    f = record.fields
    author = first_subfield(f, "100", "a")
    meeting = first_subfield(f, "111", "a")
    title = first_subfield(f, "245", "a")
    subtitle = first_subfield(f, "245", "b")
    responsibility = first_subfield(f, "245", "c")

    edition = first_subfield(f, "250", "a")
    place = first_subfield(f, "260", "a")
    publisher = first_subfield(f, "260", "b")
    year = first_subfield(f, "260", "c")

    extent = first_subfield(f, "300", "a")
    other_phys = first_subfield(f, "300", "b")
    size = first_subfield(f, "300", "c")

    series = first_subfield(f, "490", "a")
    subjects = all_subfields(f, "650", "a")
    call_numbers = all_subfields(f, "090", "a")
    isbns = all_subfields(f, "020", "a")

    chunks: List[str] = []

    heading = author or meeting
    if heading:
        chunks.append(f"{heading}.")

    title_block = title
    if subtitle:
        title_block += f" : {subtitle}"
    if responsibility:
        title_block += f" / {responsibility}"
    if title_block:
        chunks.append(f"{title_block}.")

    if edition:
        chunks.append(f"{edition}.")

    pub = ""
    if place:
        pub += place
    if publisher:
        pub += (" : " if pub else "") + publisher
    if year:
        pub += (", " if pub else "") + year
    if pub:
        chunks.append(f"{pub}.")

    phys = ""
    if extent:
        phys += extent
    if other_phys:
        phys += (" : " if phys else "") + other_phys
    if size:
        phys += (" ; " if phys else "") + size
    if phys:
        chunks.append(f"{phys}.")

    if series:
        chunks.append(f"({series}).")

    if subjects:
        chunks.append("Konular: " + " ; ".join(dict.fromkeys(subjects)) + ".")

    if call_numbers:
        chunks.append("Yer numarası: " + " ; ".join(dict.fromkeys(call_numbers)) + ".")

    if isbns:
        chunks.append("ISBN: " + " ; ".join(dict.fromkeys(isbns)) + ".")

    return " ".join(chunks).strip()


def sort_key(record: Record) -> Tuple[str, str]:
    f = record.fields
    k1 = first_subfield(f, "100", "a") or first_subfield(f, "111", "a") or first_subfield(f, "245", "a")
    return (k1.lower(), record.control_001)


def dedup_key(record: Record, mode: str) -> str:
    f = record.fields
    if mode == "none":
        return record.control_001 or str(id(record))

    title = first_subfield(f, "245", "a").lower()
    author = first_subfield(f, "100", "a").lower() or first_subfield(f, "111", "a").lower()
    publisher = first_subfield(f, "260", "b").lower()
    year = first_subfield(f, "260", "c").lower()
    edition = first_subfield(f, "250", "a").lower()

    if mode == "copy":
        return "|".join([title, author, publisher, year, edition])
    if mode == "work":
        return "|".join([title, author])
    raise ValueError(f"Unsupported dedup mode: {mode}")


def render_html(entries: List[str], title: str) -> str:
    items = "\n".join(f"<li>{html.escape(e)}</li>" for e in entries)
    return f"""<!doctype html>
<html lang=\"tr\">
<head>
  <meta charset=\"utf-8\">
  <style>
    body {{ font-family: 'Noto Serif', 'DejaVu Serif', serif; margin: 24mm; line-height: 1.45; }}
    h1 {{ font-size: 16pt; margin-bottom: 1em; }}
    ol {{ padding-left: 1.2em; }}
    li {{ margin-bottom: 0.6em; font-size: 10.5pt; }}
  </style>
</head>
<body>
  <h1>{html.escape(title)}</h1>
  <ol>
    {items}
  </ol>
</body>
</html>"""


def main() -> int:
    ap = argparse.ArgumentParser(description="Generate ISBD-oriented bibliography PDF from MARCXML.")
    ap.add_argument("--input", required=True, type=Path, help="Input MARCXML file")
    ap.add_argument("--output-pdf", required=True, type=Path, help="Output PDF path")
    ap.add_argument("--output-html", type=Path, help="Optional output HTML path")
    ap.add_argument("--title", default="Bibliyografya", help="Document title")
    ap.add_argument(
        "--dedup-mode",
        choices=["none", "copy", "work"],
        default="copy",
        help="none: keep all, copy: collapse same manifestation copies, work: collapse by work",
    )
    args = ap.parse_args()

    records = sorted(parse_marcxml(args.input), key=sort_key)

    seen = set()
    entries: List[str] = []
    for r in records:
        k = dedup_key(r, args.dedup_mode)
        if k in seen:
            continue
        seen.add(k)
        isbd = build_isbd(r)
        if isbd:
            entries.append(isbd)

    html_content = render_html(entries, args.title)
    html_path = args.output_html or args.output_pdf.with_suffix(".html")
    html_path.write_text(html_content, encoding="utf-8")

    try:
        subprocess.run(
            [sys.executable, "-m", "weasyprint", str(html_path), str(args.output_pdf)],
            check=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
        )
    except Exception as exc:
        print(
            "PDF üretimi başarısız. 'weasyprint' kurulu değil olabilir. "
            f"HTML üretildi: {html_path}. Hata: {exc}",
            file=sys.stderr,
        )
        return 1

    print(f"Tamamlandı. Kayıt sayısı: {len(entries)} | PDF: {args.output_pdf} | HTML: {html_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
