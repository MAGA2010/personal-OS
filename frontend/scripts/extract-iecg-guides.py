#!/usr/bin/env python3
"""Extract IECG college profiles from DOCX into source-preserving JSON.

The extractor keeps the original Chinese text and makes only lightweight,
reviewable structure. It does not claim that a 2025 profile is current.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import re
from pathlib import Path
from zipfile import ZipFile
from xml.etree import ElementTree as ET

W_NS = "http://schemas.openxmlformats.org/wordprocessingml/2006/main"
SECTION_HEADINGS = [
    "基本情况",
    "简介/特点",
    "费用",
    "申请截止日",
    "申请基本要求（这是最低要求，不是录取要求！）",
    "本科新生招生情况",
    "本科新生转正情况",
    "本科录取中位线（25% - 75%录取学生处于这个阶段）",
    "本科转学招生情况",
    "录取考量因素",
    "本科专业设置",
    "学生反馈",
    "总结",
]


def clean(value: str) -> str:
    value = value.replace("\u00a0", " ").replace("\u3000", " ")
    return re.sub(r"[ \t]+", " ", value).strip()


def local_name(tag: str) -> str:
    return tag.rsplit("}", 1)[-1]


def element_text(element: ET.Element) -> str:
    return clean("".join(node.text or "" for node in element.iter() if local_name(node.tag) == "t"))


def extract_lines(docx_path: Path) -> list[str]:
    with ZipFile(docx_path) as archive:
        root = ET.fromstring(archive.read("word/document.xml"))
    body = next((node for node in root.iter() if local_name(node.tag) == "body"), root)
    lines: list[str] = []
    for block in list(body):
        name = local_name(block.tag)
        if name == "p":
            text = element_text(block)
            if text:
                lines.append(text)
        elif name == "tbl":
            for row in block:
                if local_name(row.tag) != "tr":
                    continue
                cells = []
                for cell in row:
                    if local_name(cell.tag) == "tc":
                        text = element_text(cell)
                        if text:
                            cells.append(text)
                if cells:
                    lines.append(" | ".join(cells))
    return lines


def first_after(lines: list[str], label: str) -> str | None:
    for index, line in enumerate(lines):
        if line == label and index + 1 < len(lines):
            return lines[index + 1]
        prefix = label + " | "
        if line.startswith(prefix):
            value = line[len(prefix):].strip()
            return value.split(" | ", 1)[0].strip() if value else None
    return None

def all_urls(lines: list[str]) -> list[str]:
    found: list[str] = []
    for line in lines:
        for value in re.findall(r"https?://[^\s)]+|www\.[^\s)]+", line):
            value = value.rstrip("，。；,.;")
            if value not in found:
                found.append(value)
    return found


def number_after(lines: list[str], label: str) -> float | int | None:
    value = first_after(lines, label)
    if not value:
        return None
    match = re.search(r"\d[\d,]*(?:\.\d+)?", value)
    if not match:
        return None
    raw = match.group(0).replace(",", "")
    number = float(raw)
    return int(number) if number.is_integer() else number


def sectionize(lines: list[str]) -> list[dict[str, object]]:
    sections: list[dict[str, object]] = []
    current_title = "概览"
    current: list[str] = []

    def flush() -> None:
        nonlocal current
        if current:
            sections.append({
                "id": f"section-{len(sections) + 1}",
                "title": current_title,
                "paragraphs": current,
                "text": "\n".join(current),
            })
        current = []

    for line in lines:
        matched = next((heading for heading in SECTION_HEADINGS if line == heading or line.startswith(heading)), None)
        if matched:
            flush()
            current_title = matched
        else:
            current.append(line)
    flush()
    return sections


def structured_facts(lines: list[str], sections: list[dict[str, object]]) -> dict[str, object]:
    acceptance = None
    for line in lines:
        if "录取率" in line:
            match = re.search(r"(\d+(?:\.\d+)?)%", line)
            if match:
                acceptance = float(match.group(1))
                break
    website = first_after(lines, "学校官网")
    if website and not website.startswith(("http://", "https://")):
        website = "https://" + website
    deadline_section = next((s for s in sections if s["title"] == "申请截止日"), None)
    requirement_section = next((s for s in sections if s["title"].startswith("申请基本要求")), None)
    facts: dict[str, object] = {
        "officialWebsite": website,
        "founded": first_after(lines, "建校时间"),
        "schoolType": first_after(lines, "学校性质"),
        "location": first_after(lines, "地理位置"),
        "undergraduateStudents": number_after(lines, "本科生人数"),
        "graduateStudents": number_after(lines, "研究生人数"),
        "studentFacultyRatio": first_after(lines, "师生比例"),
        "freshmanRetentionRate": first_after(lines, "大一返校率"),
        "fourYearGraduationRate": first_after(lines, "4年毕业率"),
        "sixYearGraduationRate": first_after(lines, "6年毕业率"),
        "acceptanceRatePercent": acceptance,
        "deadlines": deadline_section.get("text") if deadline_section else None,
        "minimumRequirements": requirement_section.get("text") if requirement_section else None,
        "sourceUrls": all_urls(lines),
    }
    return {key: value for key, value in facts.items() if value not in (None, "", [])}


def extract_profile(docx_path: Path, source_root: Path, snapshot_year: int) -> dict[str, object]:
    lines = extract_lines(docx_path)
    sections = sectionize(lines)
    school_name_raw = first_after(lines, "学校名称")
    if school_name_raw and school_name_raw.endswith(", MIT"):
        school_name_raw = school_name_raw.split(",", 1)[0].strip()
    relative = docx_path.relative_to(source_root).as_posix()
    digest = hashlib.sha1(relative.encode("utf-8")).hexdigest()[:16]
    return {
        "id": f"iecg-{snapshot_year}-{digest}",
        "sourceFile": relative,
        "sourceSnapshotYear": snapshot_year,
        "schoolNameRaw": school_name_raw,
        "sections": sections,
        "structured": structured_facts(lines, sections),
        "rawText": "\n".join(lines),
        "displayTier": "preview",
        "sourceStatus": "archived_source",
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--source-dir", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--year", type=int, default=2025)
    args = parser.parse_args()
    source_dir = args.source_dir.resolve()
    files = sorted(source_dir.rglob("*.docx"))
    if not files:
        raise SystemExit(f"No DOCX files found under {source_dir}")
    profiles = [extract_profile(path, source_dir, args.year) for path in files]
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps({
        "source": "IECG 美本院校资料 Top90-2025",
        "sourceSnapshotYear": args.year,
        "extractedAt": __import__("datetime").datetime.now(__import__("datetime").timezone.utc).isoformat(),
        "profileCount": len(profiles),
        "profiles": profiles,
    }, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"extracted {len(profiles)} profiles -> {args.output}")


if __name__ == "__main__":
    main()