import hashlib
import html
import json
import re
from datetime import date
from pathlib import Path

from django.db import transaction

from .models import CompetitionPracticeLink

MARKDOWN_LINK_RE = re.compile(r"\[([^\]]*)\]\(([^)]*)\)")
HEADING_RE = re.compile(r"^(#{1,6})\s+(.*)$")
HTML_BREAK_RE = re.compile(r"<br\s*/?>", flags=re.IGNORECASE)
HTML_TAG_RE = re.compile(r"<[^>]+>")
CONTROL_CHAR_RE = re.compile(r"[\u0000-\u0008\u000b\u000c\u000e-\u001f\u200b\u200c\u200d\ufeff]")
WHITESPACE_RE = re.compile(r"[ \t]+")
YEAR_RE = re.compile(r"(20\d{2})")
DATE_RE = re.compile(r"^(20\d{2})-(\d{2})-(\d{2})$")

PLACEHOLDER_LINK_TEXTS = {
    "",
    "【待补充】",
    "待补充",
    "暂无",
    "-",
}

SOURCE_LABEL_TO_FILE = {
    "provincial_invitational": "01 - 省赛与邀请赛.md",
    "icpc": "02 - ICPC.md",
    "ccpc": "03 - CCPC.md",
}


def load_text_file(path: str | Path) -> str:
    file_path = Path(path)
    raw = file_path.read_bytes()
    for encoding in ("utf-8", "utf-8-sig", "gb18030", "gbk"):
        try:
            text = raw.decode(encoding)
            break
        except UnicodeDecodeError:
            continue
    else:
        text = raw.decode("utf-8", errors="ignore")

    text = text.replace("\r\n", "\n").replace("\r", "\n")
    return CONTROL_CHAR_RE.sub("", text)


def _normalize_markdown_cell(value: str) -> str:
    value = html.unescape(str(value or ""))
    value = HTML_BREAK_RE.sub("\n", value)
    value = HTML_TAG_RE.sub("", value)
    value = value.replace("\\|", "|")
    value = value.replace("**", "")
    value = value.replace("*", "")
    value = value.replace("`", "")
    value = value.replace("$^\\bullet$", "")
    value = value.replace("$\\color{red}{\\bf{^1}}$", "")
    return value.strip()


def extract_markdown_links(value: str) -> list[dict]:
    links: list[dict] = []
    for label, url in MARKDOWN_LINK_RE.findall(str(value or "")):
        url = str(url or "").strip()
        if not url or not re.match(r"^https?://", url, flags=re.IGNORECASE):
            continue
        clean_label = _normalize_markdown_cell(label).strip() or url
        item = {"label": clean_label[:80], "url": url[:500]}
        if item not in links:
            links.append(item)
    return links


def markdown_cell_to_text(value: str) -> str:
    text = str(value or "")
    text = MARKDOWN_LINK_RE.sub(lambda match: match.group(1) or match.group(2), text)
    text = _normalize_markdown_cell(text)
    lines = []
    for raw_line in text.split("\n"):
        line = WHITESPACE_RE.sub(" ", raw_line).strip()
        if line:
            lines.append(line)
    return "\n".join(lines).strip()


def parse_practice_links_text(raw_text: str) -> tuple[list[dict], str]:
    raw_text = str(raw_text or "").strip()
    if not raw_text:
        return [], ""

    links = extract_markdown_links(raw_text)
    if links:
        stripped = MARKDOWN_LINK_RE.sub("", raw_text)
        note = markdown_cell_to_text(stripped)
        if note in PLACEHOLDER_LINK_TEXTS:
            note = "待补充"
        return links, note[:255]

    parsed_links: list[dict] = []
    note_lines: list[str] = []
    for raw_line in re.split(r"[\n,]+", raw_text):
        line = markdown_cell_to_text(raw_line)
        if not line:
            continue
        if re.match(r"^https?://", line, flags=re.IGNORECASE):
            parsed_links.append({"label": "链接", "url": line[:500]})
            continue
        match = re.match(r"^(.*?)\s+(https?://\S+)$", line, flags=re.IGNORECASE)
        if match:
            parsed_links.append(
                {
                    "label": match.group(1).strip()[:80] or "链接",
                    "url": match.group(2).strip()[:500],
                }
            )
            continue
        note_lines.append(line)

    deduped_links: list[dict] = []
    for item in parsed_links:
        if item not in deduped_links:
            deduped_links.append(item)

    note = "；".join(note_lines).strip("； ")
    if note in PLACEHOLDER_LINK_TEXTS:
        note = "待补充"
    return deduped_links, note[:255]


def practice_links_to_text(links: list | None, note: str = "") -> str:
    lines = []
    for item in links or []:
        if not isinstance(item, dict):
            continue
        label = str(item.get("label") or "").strip() or "链接"
        url = str(item.get("url") or "").strip()
        if url:
            lines.append(f"{label} {url}")
    clean_note = str(note or "").strip()
    if clean_note:
        lines.append(clean_note)
    return "\n".join(lines)


def _split_markdown_table_row(line: str) -> list[str]:
    stripped = str(line or "").strip().strip("\ufeff")
    if not stripped.startswith("|"):
        return []
    return [cell.strip() for cell in stripped.strip("|").split("|")]


def _parse_markdown_tables(path: str | Path) -> list[tuple[str, list[str], list[str]]]:
    lines = load_text_file(path).split("\n")
    rows: list[tuple[str, list[str], list[str]]] = []
    current_heading = ""
    index = 0
    while index < len(lines):
        heading_match = HEADING_RE.match(lines[index])
        if heading_match:
            current_heading = markdown_cell_to_text(heading_match.group(2))
            index += 1
            continue

        if lines[index].startswith("|") and index + 1 < len(lines) and lines[index + 1].startswith("|:"):
            headers = _split_markdown_table_row(lines[index])
            index += 2
            while index < len(lines) and lines[index].startswith("|"):
                cells = _split_markdown_table_row(lines[index])
                if cells:
                    rows.append((current_heading, headers, cells))
                index += 1
            continue

        index += 1

    return rows


def _infer_year(section: str, event_date_text: str, short_name: str, official_name: str) -> int:
    match = DATE_RE.match(str(event_date_text or "").strip())
    if match:
        return int(match.group(1))

    for candidate in (short_name, official_name, section):
        year_match = YEAR_RE.search(str(candidate or ""))
        if year_match:
            return int(year_match.group(1))
    raise ValueError(f"Cannot infer year for competition practice link: {short_name}")


def _parse_event_date(event_date_text: str) -> date | None:
    match = DATE_RE.match(str(event_date_text or "").strip())
    if not match:
        return None
    return date(int(match.group(1)), int(match.group(2)), int(match.group(3)))


def _infer_provincial_stage(short_name: str, official_name: str) -> str:
    short_name = str(short_name or "")
    official_name = str(official_name or "")
    low = official_name.lower()
    if "邀请赛" in short_name or "邀请赛" in official_name or "invitational" in low:
        return CompetitionPracticeLink.Stage.INVITATIONAL
    return CompetitionPracticeLink.Stage.PROVINCIAL


def _infer_provincial_series(stage: str, combined_text: str) -> str:
    low = combined_text.lower()
    if (
        "ccpc" in low
        or "中国大学生程序设计竞赛" in combined_text
        or "中国大学生程序设计大赛" in combined_text
    ):
        return CompetitionPracticeLink.Series.CCPC
    if (
        "icpc" in low
        or "international collegiate programming contest" in low
        or "acm-icpc" in low
        or "国际大学生程序设计竞赛" in combined_text
    ):
        return CompetitionPracticeLink.Series.ICPC
    if stage == CompetitionPracticeLink.Stage.INVITATIONAL:
        return CompetitionPracticeLink.Series.CCPC
    return CompetitionPracticeLink.Series.ICPC


def _infer_stage_for_series(source_label: str, short_name: str, official_name: str) -> str | None:
    short_name = str(short_name or "")
    official_name = str(official_name or "")
    combined = f"{short_name}\n{official_name}"
    low = combined.lower()

    if source_label == "icpc":
        if "决赛" in combined or "final" in low:
            return None
        if "网络" in combined or "online" in low or "预选赛" in combined or "preliminary" in low:
            return CompetitionPracticeLink.Stage.NETWORK
        return CompetitionPracticeLink.Stage.REGIONAL

    if source_label == "ccpc":
        if (
            "女生专场" in combined
            or "高职专场" in combined
            or "决赛" in combined
            or "final" in low
            or "girls" in low
            or "vocational" in low
        ):
            return None
        if "网络" in combined or "online" in low:
            return CompetitionPracticeLink.Stage.NETWORK
        return CompetitionPracticeLink.Stage.REGIONAL

    return _infer_provincial_stage(short_name, official_name)


def _make_source_key(
    *,
    source_label: str,
    section: str,
    short_name: str,
    official_name: str,
    event_date_text: str,
    series: str,
    stage: str,
) -> str:
    payload = "|".join(
        [
            source_label,
            section,
            short_name,
            official_name,
            event_date_text,
            series,
            stage,
        ]
    )
    digest = hashlib.sha1(payload.encode("utf-8")).hexdigest()[:16]
    return f"{source_label}-{digest}"


def build_competition_practice_snapshot(source_paths: dict[str, str | Path]) -> list[dict]:
    records: list[dict] = []
    display_order = 0
    for source_label in ("provincial_invitational", "icpc", "ccpc"):
        source_path = source_paths.get(source_label)
        if not source_path:
            continue

        for section, headers, cells in _parse_markdown_tables(source_path):
            if len(cells) < 3:
                continue

            short_name = markdown_cell_to_text(cells[0])
            official_name = markdown_cell_to_text(cells[1])
            stage = _infer_stage_for_series(source_label, short_name, official_name)
            if not stage:
                continue

            event_date_text = markdown_cell_to_text(cells[2]) if len(cells) > 2 else ""
            event_date = _parse_event_date(event_date_text)

            organizer = ""
            practice_cell = cells[-1] if cells else ""
            if source_label in {"icpc", "ccpc"} and len(cells) >= 5:
                organizer = markdown_cell_to_text(cells[3])
                practice_cell = cells[-1]

            practice_links, practice_links_note = parse_practice_links_text(practice_cell)
            official_links = extract_markdown_links(cells[1])
            official_url = official_links[0]["url"] if official_links else ""

            combined_text = "\n".join(markdown_cell_to_text(cell) for cell in cells if cell)
            series = (
                CompetitionPracticeLink.Series.ICPC
                if source_label == "icpc"
                else CompetitionPracticeLink.Series.CCPC
                if source_label == "ccpc"
                else _infer_provincial_series(stage, combined_text)
            )

            year = _infer_year(section, event_date_text, short_name, official_name)
            display_order += 1
            source_key = _make_source_key(
                source_label=source_label,
                section=section,
                short_name=short_name,
                official_name=official_name,
                event_date_text=event_date_text,
                series=series,
                stage=stage,
            )
            records.append(
                {
                    "source_key": source_key,
                    "year": year,
                    "series": series,
                    "stage": stage,
                    "short_name": short_name[:120],
                    "official_name": official_name[:500] or short_name[:500],
                    "official_url": official_url[:500],
                    "event_date": event_date.isoformat() if event_date else None,
                    "event_date_text": (event_date_text or (event_date.isoformat() if event_date else ""))[:80],
                    "organizer": organizer[:255],
                    "practice_links": practice_links,
                    "practice_links_note": practice_links_note[:255],
                    "source_file": SOURCE_LABEL_TO_FILE.get(source_label, Path(source_path).name)[:120],
                    "source_section": section[:180],
                    "display_order": display_order,
                }
            )
    return records


def load_competition_practice_snapshot(path: str | Path) -> list[dict]:
    data = json.loads(load_text_file(path))
    if not isinstance(data, list):
        raise ValueError("Competition practice snapshot must be a JSON list.")
    return data


@transaction.atomic
def upsert_competition_practice_snapshot(
    records: list[dict],
    *,
    operator=None,
    replace_missing: bool = False,
) -> dict:
    seen_keys: list[str] = []
    created_count = 0
    updated_count = 0

    for item in records:
        source_key = str(item.get("source_key") or "").strip()
        if not source_key:
            continue
        event_date_raw = item.get("event_date") or None
        event_date = _parse_event_date(event_date_raw) if isinstance(event_date_raw, str) else event_date_raw

        defaults = {
            "year": int(item["year"]),
            "series": item["series"],
            "stage": item["stage"],
            "short_name": str(item.get("short_name") or "")[:120],
            "official_name": str(item.get("official_name") or "")[:500],
            "official_url": str(item.get("official_url") or "")[:500],
            "event_date": event_date,
            "event_date_text": str(item.get("event_date_text") or "")[:80],
            "organizer": str(item.get("organizer") or "")[:255],
            "practice_links": item.get("practice_links") or [],
            "practice_links_note": str(item.get("practice_links_note") or "")[:255],
            "source_file": str(item.get("source_file") or "")[:120],
            "source_section": str(item.get("source_section") or "")[:180],
            "display_order": int(item.get("display_order") or 0),
            "updated_by": operator if getattr(operator, "is_authenticated", False) else None,
        }
        obj, created = CompetitionPracticeLink.objects.update_or_create(source_key=source_key, defaults=defaults)
        if created and getattr(operator, "is_authenticated", False):
            obj.created_by = operator
            obj.save(update_fields=["created_by", "updated_at"])
        seen_keys.append(source_key)
        if created:
            created_count += 1
        else:
            updated_count += 1

    removed_count = 0
    if replace_missing and seen_keys:
        removed_count, _ = CompetitionPracticeLink.objects.exclude(source_key__in=seen_keys).delete()

    return {
        "created": created_count,
        "updated": updated_count,
        "removed": removed_count,
        "total": len(seen_keys),
    }
