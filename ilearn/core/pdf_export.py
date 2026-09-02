"""Markdown → PDF for session exports (WeasyPrint preferred, fpdf2 fallback)."""

from __future__ import annotations

import html
import os
import re
from pathlib import Path
from typing import Literal

from ilearn.core.markdown_layout import split_learning_report, split_plan_report

_PROJECT_ROOT = Path(__file__).resolve().parents[2]
_ASSETS_FONTS = _PROJECT_ROOT / "assets" / "fonts"

PdfBackend = Literal["weasyprint", "fpdf2"]
_PDF_BACKEND_ENV = "ILEARN_PDF_BACKEND"
_last_pdf_backend: PdfBackend | None = None

_HEADING = re.compile(r"^(#{1,3})\s+(.*)$")
_UL = re.compile(r"^-\s+(.*)$")
_OL = re.compile(r"^\d+\.\s+(.*)$")
_TABLE_ROW = re.compile(r"^\|(.+)\|$")
_HR = re.compile(r"^-{3,}$")
_QUESTION_H3 = re.compile(r"^第\s*\d+\s*题")


def markdown_to_html(markdown: str) -> str:
    """Minimal MD→HTML covering headings, lists, tables, paragraphs, bold."""
    normalized = markdown.replace("\r\n", "\n")
    body = _markdown_lines_to_html(normalized.split("\n"))
    title = _extract_doc_title(normalized)
    return _html_document("".join(body), title=title)


def markdown_to_html_two_column(left: str, right: str) -> str:
    left_body = _markdown_lines_to_html(left.replace("\r\n", "\n").split("\n"))
    right_body = _markdown_lines_to_html(right.replace("\r\n", "\n").split("\n"))
    title = _extract_doc_title(left.replace("\r\n", "\n"))
    content = (
        "<div class='report-columns'>"
        f"<div class='report-col report-col-left'>{''.join(left_body)}</div>"
        f"<div class='report-col report-col-right'>{''.join(right_body)}</div>"
        "</div>"
    )
    return _html_document(content, title=title, two_column=True)


def markdown_to_pdf_report(markdown: str) -> bytes:
    """Render a learning report PDF; uses two columns (or two pages on fallback)."""
    left, right = split_learning_report(markdown)
    if not right:
        return markdown_to_pdf(markdown)
    if _weasyprint_usable():
        try:
            from weasyprint import HTML  # type: ignore

            html_doc = markdown_to_html_two_column(left, right)
            return HTML(string=html_doc, base_url=str(_PROJECT_ROOT)).write_pdf()
        except Exception:
            pass
    return _fpdf_pdf_two_column(left, right)


def markdown_to_pdf_plan(markdown: str) -> bytes:
    """Render plan markdown with schedule vs methods split when possible."""
    left, right = split_plan_report(markdown)
    if not right:
        return markdown_to_pdf(markdown)
    if _weasyprint_usable():
        try:
            from weasyprint import HTML  # type: ignore

            html_doc = markdown_to_html_two_column(left, right)
            return HTML(string=html_doc, base_url=str(_PROJECT_ROOT)).write_pdf()
        except Exception:
            pass
    return _fpdf_pdf_two_column(left, right)


def _markdown_lines_to_html(lines: list[str]) -> list[str]:
    body: list[str] = []
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
        if _HR.match(trimmed):
            flush_ul()
            body.append("<hr class='section-divider' />")
            i += 1
            continue
        hm = _HEADING.match(trimmed)
        if hm:
            flush_ul()
            level = len(hm.group(1))
            text = _inline(hm.group(2))
            if level == 1:
                body.append(
                    f"<div class='doc-hero'><h1 class='doc-title'>{text}</h1></div>"
                )
            elif level == 2:
                body.append(f"<h2 class='section-heading'>{text}</h2>")
            else:
                q_class = " question-heading" if _QUESTION_H3.search(hm.group(2)) else ""
                body.append(
                    f"<h3 class='subsection-heading{q_class}'>{text}</h3>"
                )
            i += 1
            continue
        um = _UL.match(trimmed)
        if um:
            indent = len(raw) - len(raw.lstrip())
            li_class = " class='nested'" if indent >= 2 else ""
            if not in_ul:
                body.append("<ul class='bullet-list'>")
                in_ul = True
            body.append(f"<li{li_class}>{_inline(um.group(1))}</li>")
            i += 1
            continue
        om = _OL.match(trimmed)
        if om:
            flush_ul()
            body.append(f"<p class='numbered-item'>{_inline(om.group(1))}</p>")
            i += 1
            continue
        flush_ul()
        if trimmed.startswith("> "):
            body.append(f"<blockquote class='callout'>{_inline(trimmed[2:])}</blockquote>")
        elif trimmed.startswith("_") and trimmed.endswith("_") and len(trimmed) > 2:
            body.append(f"<p class='muted'><em>{_inline(trimmed[1:-1])}</em></p>")
        else:
            body.append(f"<p class='body-text'>{_inline(trimmed)}</p>")
        i += 1
    flush_ul()
    return body


def _inline(text: str) -> str:
    escaped = html.escape(text)
    escaped = re.sub(r"\*\*(.+?)\*\*", r"<strong>\1</strong>", escaped)
    escaped = re.sub(r"_(.+?)_", r"<em>\1</em>", escaped)
    return escaped


def _table_html(rows: list[str]) -> str:
    if len(rows) < 2:
        return "<pre>" + html.escape("\n".join(rows)) + "</pre>"

    def cells(row: str) -> list[str]:
        return [c.strip() for c in row.strip("|").split("|")]

    header = cells(rows[0])
    # skip separator row
    body_rows = [cells(r) for r in rows[2:]]
    parts = ["<div class='table-wrap'><table class='data-table'><thead><tr>"]
    parts.extend(f"<th>{_inline(h)}</th>" for h in header)
    parts.append("</tr></thead><tbody>")
    for idx_row, row in enumerate(body_rows):
        stripe = " class='row-alt'" if idx_row % 2 == 1 else ""
        parts.append(f"<tr{stripe}>")
        for idx, _ in enumerate(header):
            cell = row[idx] if idx < len(row) else ""
            align = " class='num'" if _looks_numeric(cell) else ""
            parts.append(f"<td{align}>{_inline(cell)}</td>")
        parts.append("</tr>")
    parts.append("</tbody></table></div>")
    return "".join(parts)


def _looks_numeric(text: str) -> bool:
    t = text.strip().replace("%", "").replace(":", "")
    if not t or t == "—":
        return False
    try:
        float(t)
        return True
    except ValueError:
        return bool(re.match(r"^\d+:\d{2}$", text.strip()))


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


def _extract_doc_title(markdown: str) -> str:
    for line in markdown.split("\n"):
        trimmed = line.strip()
        hm = _HEADING.match(trimmed)
        if hm and len(hm.group(1)) == 1:
            return _strip_md(hm.group(2))
    return "ILearn 学习报告"


def _html_document(body: str, *, title: str, two_column: bool = False) -> str:
    css = _pdf_css() + (_two_column_css() if two_column else "")
    safe_title = html.escape(title)
    return (
        "<!DOCTYPE html><html lang='zh-CN'><head><meta charset='utf-8'>"
        f"<title>{safe_title}</title>"
        f"<style>{css}</style></head><body>"
        "<div class='pdf-doc'>"
        "<header class='pdf-brand-bar'>"
        "<span class='pdf-brand-mark'>ILearn</span>"
        f"<span class='pdf-doc-label'>{safe_title}</span>"
        "</header>"
        f"<main class='pdf-main'>{body}</main>"
        "<footer class='pdf-footer'>"
        "<span>ILearn 智能学习诊断系统</span>"
        "<span class='pdf-footer-note'>本报告由系统自动生成</span>"
        "</footer>"
        "</div></body></html>"
    )


def _two_column_css() -> str:
    return (
        ".report-columns{display:grid;grid-template-columns:1fr 1fr;gap:20px;"
        "align-items:start;margin-top:8px;}"
        ".report-col{min-width:0;}"
        ".report-col-left{border-right:1px solid #e2e8f0;padding-right:12px;}"
        ".report-col-right{padding-left:4px;}"
        "@media print{"
        ".report-columns{display:block;}"
        ".report-col-left{border-right:none;padding-right:0;"
        "page-break-after:always;margin-bottom:28px;}"
        ".report-col-right{padding-left:0;}}"
    )


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
        + "@page { size: A4; margin: 14mm 14mm 18mm 14mm; "
        "@bottom-right { content: '第 ' counter(page) ' 页'; "
        f"font-family: {family}; font-size: 8pt; color: #94a3b8; }}"
        "* { box-sizing: border-box; }"
        f"body{{font-family:{family};font-size:10.5pt;line-height:1.62;"
        "color:#1a2a3a;background:#fff;margin:0;}}"
        ".pdf-doc{padding:0;}"
        ".pdf-brand-bar{display:flex;align-items:center;justify-content:space-between;"
        "gap:12px;background:linear-gradient(120deg,#002fa7 0%,#4A90D9 100%);"
        "color:#fff;padding:14px 20px;margin-bottom:20px;}"
        ".pdf-brand-mark{font-size:13pt;font-weight:700;letter-spacing:0.04em;}"
        ".pdf-doc-label{font-size:10pt;opacity:0.92;text-align:right;}"
        ".pdf-main{padding:0 4px 16px;}"
        ".pdf-footer{display:flex;justify-content:space-between;gap:12px;"
        "margin-top:24px;padding-top:10px;border-top:1px solid #e2e8f0;"
        "font-size:8.5pt;color:#94a3b8;}"
        ".doc-hero{margin:0 0 20px;padding-bottom:12px;border-bottom:2px solid #4A90D9;}"
        ".doc-title{font-size:22pt;font-weight:700;color:#002fa7;margin:0;line-height:1.25;}"
        ".section-heading{font-size:14pt;color:#002fa7;margin:22px 0 10px;padding-bottom:6px;"
        "border-bottom:1px solid #dbeafe;page-break-after:avoid;}"
        ".subsection-heading{font-size:11.5pt;color:#1e3a5f;margin:16px 0 8px;"
        "page-break-after:avoid;}"
        ".question-heading{background:#f0f7ff;border:1px solid #dbeafe;"
        "border-left:4px solid #4A90D9;padding:8px 10px;margin:14px 0 6px;"
        "border-radius:4px;}"
        ".body-text{margin:0 0 8px;}"
        ".muted{color:#64748b;font-size:9.5pt;}"
        ".bullet-list{margin:6px 0 12px;padding-left:1.2em;}"
        ".bullet-list li{margin:4px 0;}"
        ".bullet-list li.nested{margin-left:1em;list-style-type:circle;}"
        ".numbered-item{margin:4px 0 8px;padding-left:0.4em;}"
        ".section-divider{border:none;border-top:1px solid #e2e8f0;margin:18px 0;}"
        ".table-wrap{margin:10px 0 16px;overflow:hidden;border-radius:6px;"
        "border:1px solid #e2e8f0;}"
        ".data-table{border-collapse:collapse;width:100%;font-size:9.5pt;}"
        ".data-table thead th{background:#eef5fc;color:#1e3a5f;font-weight:600;"
        "text-align:left;padding:8px 10px;border-bottom:2px solid #4A90D9;}"
        ".data-table td{padding:7px 10px;border-bottom:1px solid #f1f5f9;vertical-align:top;}"
        ".data-table tbody tr.row-alt td{background:#f8fafc;}"
        ".data-table td.num{text-align:right;font-variant-numeric:tabular-nums;}"
        ".callout{margin:10px 0;padding:10px 14px;border-left:4px solid #4A90D9;"
        "background:#f0f7ff;color:#334155;border-radius:0 4px 4px 0;}"
        "strong{color:#0f172a;}"
        "h2,h3{page-break-after:avoid;}"
        "table{page-break-inside:auto;}"
        "tr{page-break-inside:avoid;page-break-after:auto;}"
    )


def configured_pdf_backend() -> PdfBackend | None:
    """Forced backend from ILEARN_PDF_BACKEND, or None for auto (WeasyPrint preferred)."""
    raw = os.environ.get(_PDF_BACKEND_ENV, "").strip().lower()
    if raw in ("weasyprint", "fpdf2"):
        return raw
    return None


def resolve_pdf_backend() -> PdfBackend:
    """Return the backend that would be used for the next PDF render."""
    forced = configured_pdf_backend()
    if forced:
        return forced
    return "weasyprint" if _weasyprint_usable() else "fpdf2"


def get_pdf_backend_info() -> dict[str, object]:
    """Status for UI: active backend, whether WeasyPrint is available, env override."""
    forced = configured_pdf_backend()
    weasy_ok = _weasyprint_usable()
    active = forced or ("weasyprint" if weasy_ok else "fpdf2")
    return {
        "backend": active,
        "weasyprint_available": weasy_ok,
        "forced": forced is not None,
        "last_used": _last_pdf_backend,
        "fallback_active": active == "fpdf2" and weasy_ok and forced is None,
    }


def _set_last_pdf_backend(backend: PdfBackend) -> None:
    global _last_pdf_backend
    _last_pdf_backend = backend


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
    forced = configured_pdf_backend()
    if forced == "fpdf2":
        _set_last_pdf_backend("fpdf2")
        return _fpdf_pdf(markdown)
    if forced == "weasyprint":
        try:
            out = _weasyprint_pdf(markdown)
            _set_last_pdf_backend("weasyprint")
            return out
        except Exception:
            _set_last_pdf_backend("fpdf2")
            return _fpdf_pdf(markdown)
    if _weasyprint_usable():
        try:
            out = _weasyprint_pdf(markdown)
            _set_last_pdf_backend("weasyprint")
            return out
        except Exception:
            pass
    _set_last_pdf_backend("fpdf2")
    return _fpdf_pdf(markdown)


def _weasyprint_pdf(markdown: str) -> bytes:
    from weasyprint import HTML  # type: ignore

    html_doc = markdown_to_html(markdown)
    return HTML(string=html_doc, base_url=str(_PROJECT_ROOT)).write_pdf()


def _fpdf_pdf_two_column(left: str, right: str) -> bytes:
    from fpdf import FPDF

    title = _extract_doc_title(left)
    pdf = FPDF(format="A4", unit="mm")
    pdf.set_auto_page_break(auto=True, margin=16)
    pdf.set_margins(14, 16, 14)
    font_name = _fpdf_register_font(pdf)
    pdf.add_page()
    _fpdf_draw_brand_header(pdf, font_name, title)
    _fpdf_write_markdown(pdf, font_name, left)
    if right.strip():
        pdf.add_page()
        _fpdf_draw_brand_header(pdf, font_name, title)
        _fpdf_write_markdown(pdf, font_name, right)
    out = pdf.output()
    if isinstance(out, (bytes, bytearray)):
        return bytes(out)
    return str(out).encode("latin-1")


def _fpdf_register_font(pdf) -> str:
    font_name = "Helvetica"
    for path in _candidate_font_files():
        if path.suffix.lower() == ".ttc":
            continue
        try:
            pdf.add_font("ILearnCJK", fname=str(path))
            return "ILearnCJK"
        except Exception:
            continue
    if font_name == "Helvetica":
        for path in _candidate_font_files():
            try:
                pdf.add_font("ILearnCJK", fname=str(path))
                return "ILearnCJK"
            except Exception:
                continue
    return font_name


def _fpdf_draw_brand_header(pdf, font_name: str, title: str) -> None:
    pdf.set_fill_color(0, 47, 167)
    pdf.rect(0, 0, pdf.w, 12, style="F")
    pdf.set_xy(pdf.l_margin, 3)
    pdf.set_font(font_name, size=11)
    pdf.set_text_color(255, 255, 255)
    pdf.cell(30, 6, "ILearn")
    label = title if len(title) <= 48 else title[:45] + "…"
    label_width = min(pdf.get_string_width(label), pdf.epw * 0.65)
    pdf.set_xy(pdf.w - pdf.r_margin - label_width, 3)
    pdf.cell(label_width, 6, label, align="R")
    pdf.set_text_color(26, 42, 58)
    pdf.set_y(16)


def _fpdf_write_table(pdf, font_name: str, rows: list[str]) -> None:
    if len(rows) < 2:
        pdf.multi_cell(pdf.epw, 5, "\n".join(rows))
        return

    def cells(row: str) -> list[str]:
        return [c.strip() for c in row.strip("|").split("|")]

    header = cells(rows[0])
    body_rows = [cells(r) for r in rows[2:]]
    col_n = max(len(header), 1)
    col_w = pdf.epw / col_n
    pdf.set_font(font_name, size=8)
    pdf.set_fill_color(238, 245, 252)
    for h in header:
        pdf.cell(col_w, 6, _strip_md(h)[:18], border=1, fill=True)
    pdf.ln()
    pdf.set_fill_color(255, 255, 255)
    for row_idx, row in enumerate(body_rows):
        if row_idx % 2 == 1:
            pdf.set_fill_color(248, 250, 252)
        else:
            pdf.set_fill_color(255, 255, 255)
        for idx in range(col_n):
            cell = row[idx] if idx < len(row) else ""
            pdf.cell(col_w, 5, _strip_md(cell)[:22], border=1, fill=True)
        pdf.ln()
    pdf.set_fill_color(255, 255, 255)
    pdf.ln(2)


def _fpdf_write_markdown(pdf, font_name: str, markdown: str) -> None:
    def set_size(size: float) -> None:
        pdf.set_font(font_name, size=size)

    def write_block(text: str, size: float = 10.5, line_h: float = 6) -> None:
        set_size(size)
        pdf.set_x(pdf.l_margin)
        pdf.multi_cell(
            w=pdf.epw,
            h=line_h,
            text=text,
            new_x="LMARGIN",
            new_y="NEXT",
        )

    lines = markdown.replace("\r\n", "\n").split("\n")
    i = 0
    skipped_title = False
    while i < len(lines):
        line = lines[i].rstrip()
        if not line.strip():
            pdf.ln(3)
            i += 1
            continue
        if line.strip().startswith("|"):
            table_rows: list[str] = []
            while i < len(lines) and lines[i].strip().startswith("|"):
                table_rows.append(lines[i].strip())
                i += 1
            _fpdf_write_table(pdf, font_name, table_rows)
            continue
        if _HR.match(line.strip()):
            pdf.ln(2)
            pdf.set_draw_color(226, 232, 240)
            y = pdf.get_y()
            pdf.line(pdf.l_margin, y, pdf.w - pdf.r_margin, y)
            pdf.ln(4)
            i += 1
            continue
        hm = _HEADING.match(line.strip())
        if hm:
            level = len(hm.group(1))
            text = _strip_md(hm.group(2))
            if level == 1 and not skipped_title:
                skipped_title = True
                i += 1
                continue
            sizes = {1: 16, 2: 13, 3: 11}
            pdf.ln(2 if level > 1 else 0)
            write_block(text, size=sizes.get(level, 10.5), line_h=7)
            pdf.ln(1)
            i += 1
            continue
        um = _UL.match(line.strip())
        if um:
            write_block("• " + _strip_md(um.group(1)), size=10)
            i += 1
            continue
        if line.strip().startswith("> "):
            pdf.set_fill_color(240, 247, 255)
            write_block("▎ " + _strip_md(line.strip()[2:]), size=9.5)
            i += 1
            continue
        write_block(_strip_md(line.strip()))
        i += 1


def _fpdf_pdf(markdown: str) -> bytes:
    from fpdf import FPDF

    title = _extract_doc_title(markdown)
    pdf = FPDF(format="A4", unit="mm")
    pdf.set_auto_page_break(auto=True, margin=16)
    pdf.set_margins(14, 16, 14)
    pdf.add_page()
    font_name = _fpdf_register_font(pdf)
    _fpdf_draw_brand_header(pdf, font_name, title)
    _fpdf_write_markdown(pdf, font_name, markdown)
    out = pdf.output()
    if isinstance(out, (bytes, bytearray)):
        return bytes(out)
    return str(out).encode("latin-1")


def _strip_md(text: str) -> str:
    return re.sub(r"\*\*(.+?)\*\*", r"\1", text)
