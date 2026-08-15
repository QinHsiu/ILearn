"""Markdown → PDF for session exports (WeasyPrint preferred, fpdf2 fallback)."""

from __future__ import annotations

import html
import os
import re
from pathlib import Path

_PROJECT_ROOT = Path(__file__).resolve().parents[2]
_ASSETS_FONTS = _PROJECT_ROOT / "assets" / "fonts"

_HEADING = re.compile(r"^(#{1,3})\s+(.*)$")
_UL = re.compile(r"^-\s+(.*)$")
_TABLE_ROW = re.compile(r"^\|(.+)\|$")


def markdown_to_html(markdown: str) -> str:
    """Minimal MD→HTML covering headings, lists, tables, paragraphs, bold."""
    body: list[str] = []
    lines = markdown.replace("\r\n", "\n").split("\n")
    i = 0
    in_ul = False

    def flush_ul() -> None:
        nonlocal in_ul
        if in_ul:
            body.append("</ul>")
            in_ul = False

    while i < len(lines):
        raw = lines[i]
        trimmed = raw.strip()
        if not trimmed:
            flush_ul()
            i += 1
            continue
        if trimmed.startswith("|"):
            flush_ul()
            rows: list[str] = []
            while i < len(lines) and lines[i].strip().startswith("|"):
                rows.append(lines[i].strip())
                i += 1
            body.append(_table_html(rows))
            continue
        hm = _HEADING.match(trimmed)
        if hm:
            flush_ul()
            level = len(hm.group(1))
            body.append(f"<h{level}>{_inline(hm.group(2))}</h{level}>")
            i += 1
            continue
        um = _UL.match(trimmed)
        if um:
            if not in_ul:
                body.append("<ul>")
                in_ul = True
            body.append(f"<li>{_inline(um.group(1))}</li>")
            i += 1
            continue
        flush_ul()
        if trimmed.startswith("> "):
            body.append(f"<blockquote>{_inline(trimmed[2:])}</blockquote>")
        else:
            body.append(f"<p>{_inline(trimmed)}</p>")
        i += 1
    flush_ul()
    css = _pdf_css()
    return (
        "<!DOCTYPE html><html><head><meta charset='utf-8'>"
        f"<style>{css}</style></head><body>{''.join(body)}</body></html>"
    )


def _inline(text: str) -> str:
    escaped = html.escape(text)
    return re.sub(r"\*\*(.+?)\*\*", r"<strong>\1</strong>", escaped)


def _table_html(rows: list[str]) -> str:
    if len(rows) < 2:
        return "<pre>" + html.escape("\n".join(rows)) + "</pre>"

    def cells(row: str) -> list[str]:
        return [c.strip() for c in row.strip("|").split("|")]

    header = cells(rows[0])
    # skip separator row
    body_rows = [cells(r) for r in rows[2:]]
    parts = ["<table><thead><tr>"]
    parts.extend(f"<th>{_inline(h)}</th>" for h in header)
    parts.append("</tr></thead><tbody>")
    for row in body_rows:
        parts.append("<tr>")
        for idx, _ in enumerate(header):
            parts.append(f"<td>{_inline(row[idx] if idx < len(row) else '')}</td>")
        parts.append("</tr>")
    parts.append("</tbody></table>")
    return "".join(parts)


def _candidate_font_files() -> list[Path]:
    names = (
        "NotoSansSC-Regular.otf",
        "NotoSansSC-Regular.ttf",
        "SourceHanSansSC-Regular.otf",
        "msyh.ttc",
        "msyh.ttf",
        "simhei.ttf",
        "SimSun.ttf",
    )
    found: list[Path] = []
    if _ASSETS_FONTS.is_dir():
        for name in names:
            path = _ASSETS_FONTS / name
            if path.is_file():
                found.append(path)
    windir = Path(os.environ.get("WINDIR", r"C:\Windows"))
    fonts_dir = windir / "Fonts"
    for name in names:
        path = fonts_dir / name
        if path.is_file():
            found.append(path)
    return found


def _pdf_css() -> str:
    families = ["'Noto Sans CJK SC'", "'Microsoft YaHei'", "'PingFang SC'", "sans-serif"]
    font_faces: list[str] = []
    for path in _candidate_font_files()[:2]:
        url = path.as_uri()
        font_faces.append(
            f"@font-face {{ font-family: 'ILearnCJK'; src: url('{url}'); }}"
        )
        families.insert(0, "'ILearnCJK'")
    family = ", ".join(families)
    return (
        "".join(font_faces)
        + f"body{{font-family:{family};font-size:12px;line-height:1.5;"
        "color:#1a2a3a;margin:24px;}}"
        "h1{font-size:22px;color:#4A90D9;}h2{font-size:16px;color:#4A90D9;}"
        "h3{font-size:13px;}table{border-collapse:collapse;width:100%;"
        "margin:8px 0;}th,td{border:1px solid #ccc;padding:4px 6px;}"
        "th{background:#eef5fc;}blockquote{border-left:3px solid #4A90D9;"
        "padding:4px 8px;color:#5A7A9A;}"
    )


def _weasyprint_usable() -> bool:
    """True when native libs for WeasyPrint are loadable (skip noisy failed import)."""
    try:
        from cffi import FFI

        ffi = FFI()
        for name in (
            "libgobject-2.0-0",
            "gobject-2.0-0",
            "libgobject-2.0.so.0",
            "libgobject-2.0.0.dylib",
        ):
            try:
                ffi.dlopen(name)
                return True
            except OSError:
                continue
    except Exception:
        return False
    return False


def markdown_to_pdf(markdown: str) -> bytes:
    """Render markdown to PDF bytes. Prefer WeasyPrint; fall back to fpdf2."""
    if _weasyprint_usable():
        try:
            return _weasyprint_pdf(markdown)
        except Exception:
            pass
    return _fpdf_pdf(markdown)


def _weasyprint_pdf(markdown: str) -> bytes:
    from weasyprint import HTML  # type: ignore

    html_doc = markdown_to_html(markdown)
    return HTML(string=html_doc, base_url=str(_PROJECT_ROOT)).write_pdf()


def _fpdf_pdf(markdown: str) -> bytes:
    from fpdf import FPDF

    pdf = FPDF(format="A4", unit="mm")
    pdf.set_auto_page_break(auto=True, margin=16)
    pdf.add_page()
    font_name = "Helvetica"
    # Prefer .ttf/.otf — fpdf2 is unreliable with some .ttc collections.
    for path in _candidate_font_files():
        if path.suffix.lower() == ".ttc":
            continue
        try:
            pdf.add_font("ILearnCJK", fname=str(path))
            font_name = "ILearnCJK"
            break
        except Exception:
            continue
    if font_name == "Helvetica":
        for path in _candidate_font_files():
            try:
                pdf.add_font("ILearnCJK", fname=str(path))
                font_name = "ILearnCJK"
                break
            except Exception:
                continue

    def set_size(size: float) -> None:
        pdf.set_font(font_name, size=size)

    def write_block(text: str, size: float = 11, line_h: float = 6) -> None:
        set_size(size)
        pdf.set_x(pdf.l_margin)
        pdf.multi_cell(
            w=pdf.epw,
            h=line_h,
            text=text,
            new_x="LMARGIN",
            new_y="NEXT",
        )

    set_size(11)
    for raw in markdown.replace("\r\n", "\n").split("\n"):
        line = raw.rstrip()
        if not line.strip():
            pdf.ln(4)
            continue
        if _TABLE_ROW.match(line.strip()):
            write_block(line.strip(), size=9, line_h=5)
            continue
        hm = _HEADING.match(line.strip())
        if hm:
            level = len(hm.group(1))
            sizes = {1: 18, 2: 14, 3: 12}
            write_block(_strip_md(hm.group(2)), size=sizes.get(level, 11), line_h=8)
            pdf.ln(1)
            continue
        um = _UL.match(line.strip())
        if um:
            write_block("- " + _strip_md(um.group(1)))
            continue
        write_block(_strip_md(line.strip()))
    out = pdf.output()
    if isinstance(out, (bytes, bytearray)):
        return bytes(out)
    return str(out).encode("latin-1")


def _strip_md(text: str) -> str:
    return re.sub(r"\*\*(.+?)\*\*", r"\1", text)
