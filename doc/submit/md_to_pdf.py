"""Convert submit Markdown docs to A4 PDFs — Swiss / Klein Blue (no gradients).

Color lock (deck-swiss-international Klein Blue):
  accent #002FA7 · paper #fafaf8 · ink #0a0a0a
Layout: sharp corners, hairlines, no gradients/shadows/glow.
"""

from __future__ import annotations

import re
from pathlib import Path

from fpdf import FPDF
from fpdf.enums import TableCellFillMode, WrapMode
from fpdf.fonts import FontFace

HERE = Path(__file__).resolve().parent

# Prefer static Regular/Bold (VF default axis is too thin and looks "washed out")
YAHEI_REG = Path(r"C:\Windows\Fonts\msyh.ttc")
YAHEI_BOLD = Path(r"C:\Windows\Fonts\msyhbd.ttc")
NOTO_VF = Path(r"C:\Windows\Fonts\NotoSansSC-VF.ttf")
FALLBACKS = [
    Path(r"C:\Windows\Fonts\simhei.ttf"),
    Path(r"C:\Windows\Fonts\Deng.ttf"),
]

# Klein Blue IKB — locked hex from swiss skill
ACCENT = (0, 47, 167)  # #002FA7
PAPER = (255, 255, 255)  # pure white — maximizes ink contrast
INK = (0, 0, 0)
MUTED = (20, 20, 20)
RULE = (0, 0, 0)
TABLE_HEAD_BG = (230, 230, 228)
TABLE_ZEBRA = (245, 245, 243)
CODE_BG = (15, 15, 15)
CODE_FG = (255, 255, 255)

FS_BODY = 11
FS_TABLE = 10
FS_H2 = 13
FS_H3 = 11.5
FS_CODE = 8.5


def _register_fonts(pdf: FPDF) -> str:
    """Register body (regular) + body Bold with real weight, not faux-bold light VF."""
    if YAHEI_REG.exists() and YAHEI_BOLD.exists():
        pdf.add_font("body", "", fname=str(YAHEI_REG), collection_font_number=0)
        pdf.add_font("body", "B", fname=str(YAHEI_BOLD), collection_font_number=0)
        return "msyh+msyhbd"
    if NOTO_VF.exists():
        pdf.add_font(
            "body",
            "",
            fname=str(NOTO_VF),
            variations={"wght": 500.0},
        )
        pdf.add_font(
            "body",
            "B",
            fname=str(NOTO_VF),
            variations={"wght": 700.0},
        )
        return "NotoSansSC-VF wght500/700"
    for path in FALLBACKS:
        if not path.exists():
            continue
        pdf.add_font("body", "", fname=str(path))
        pdf.add_font("body", "B", fname=str(path))
        return path.name
    raise SystemExit("No usable Chinese font under C:\\Windows\\Fonts")


def _extract_title(md_text: str, fallback: str) -> tuple[str, str]:
    lines = md_text.splitlines()
    title = fallback
    skip_idx: int | None = None
    for i, line in enumerate(lines):
        if line.startswith("# "):
            title = line[2:].strip()
            skip_idx = i
            break
    if skip_idx is None:
        return title, md_text
    kept = lines[:skip_idx] + lines[skip_idx + 1 :]
    if skip_idx < len(kept) and kept[skip_idx].strip() == "":
        kept = kept[:skip_idx] + kept[skip_idx + 1 :]
    return title, "\n".join(kept)


def _strip_inline(text: str) -> str:
    text = re.sub(r"\*\*(.+?)\*\*", r"\1", text)
    text = re.sub(r"`([^`]+)`", r"\1", text)
    text = re.sub(r"\[([^\]]+)\]\([^)]+\)", r"\1", text)
    return text


class SubmitPDF(FPDF):
    def __init__(self, footer_left: str) -> None:
        super().__init__(format="A4", unit="mm")
        self.footer_left = footer_left
        self.font_label = _register_fonts(self)
        self.set_auto_page_break(auto=True, margin=18)
        self.set_margins(18, 18, 18)

    def header(self) -> None:
        # Flat paper fill every page (no gradient)
        self.set_fill_color(*PAPER)
        self.rect(0, 0, self.w, self.h, style="F")
        if self.page_no() == 1:
            return
        # Continuation pages: thin top accent rule
        self.set_draw_color(*ACCENT)
        self.set_line_width(0.7)
        self.line(0, 0, self.w, 0)
        self.set_y(14)

    def footer(self) -> None:
        self.set_draw_color(*RULE)
        self.set_line_width(0.25)
        y = self.h - 14
        self.line(self.l_margin, y, self.w - self.r_margin, y)
        self.set_y(-11)
        self.set_font("body", size=8.5)
        self.set_text_color(*MUTED)
        third = self.epw / 3
        self.set_x(self.l_margin)
        self.cell(third, 6, self.footer_left.upper(), align="L")
        self.cell(third, 6, f"{self.page_no()}", align="C")
        self.cell(third, 6, "QinHsiu / ILearn", align="R")

    def cover_block(self, title: str) -> None:
        # Top accent bar (solid, flat — no gradient)
        self.set_fill_color(*ACCENT)
        self.rect(0, 0, self.w, 4.5, style="F")

        self.set_y(14)
        self.set_font("body", "B", 9)
        self.set_text_color(*INK)
        self.cell(
            0,
            5,
            "GOAI 2026  ·  TRACK 02 AI+EDU  ·  ILEARN",
            new_x="LMARGIN",
            new_y="NEXT",
        )

        self.ln(2)
        self.set_font("body", "B", 18)
        self.set_text_color(*INK)
        self.multi_cell(self.epw, 9, title)

        # Hairline under title
        self.ln(2)
        self.set_draw_color(*ACCENT)
        self.set_line_width(0.8)
        y = self.get_y()
        self.line(self.l_margin, y, self.l_margin + 28, y)
        self.ln(6)
        self.set_text_color(*INK)

    def h2(self, text: str) -> None:
        self.ln(4)
        self.set_font("body", "B", FS_H2)
        self.set_text_color(*INK)
        self.multi_cell(self.epw, 7.2, text)
        self.set_draw_color(*ACCENT)
        self.set_line_width(0.55)
        y = self.get_y() + 0.5
        self.line(self.l_margin, y, self.w - self.r_margin, y)
        self.ln(3)
        self.set_text_color(*INK)

    def h3(self, text: str) -> None:
        self.ln(2.5)
        self.set_font("body", "B", FS_H3)
        self.set_text_color(*INK)
        self.multi_cell(self.epw, 6.2, text)
        self.ln(1)

    def para(self, text: str, size: float = FS_BODY) -> None:
        self.set_font("body", size=size)
        self.set_text_color(*INK)
        self.multi_cell(self.epw, 6.0, text)
        self.ln(0.6)

    def quote(self, text: str) -> None:
        x0 = self.l_margin
        y0 = self.get_y()
        self.set_x(x0 + 4)
        self.set_font("body", size=FS_BODY)
        self.set_text_color(*INK)
        self.multi_cell(self.epw - 4, 5.8, text)
        y1 = self.get_y()
        self.set_draw_color(*ACCENT)
        self.set_line_width(1.2)
        self.line(x0, y0, x0, y1)
        self.set_fill_color(*PAPER)
        self.set_text_color(*INK)
        self.ln(2)

    def bullet(self, text: str) -> None:
        self.set_font("body", size=FS_BODY)
        self.set_text_color(*INK)
        x = self.l_margin
        y = self.get_y()
        self.set_fill_color(*ACCENT)
        self.rect(x, y + 2.0, 1.8, 1.8, style="F")
        self.set_xy(x + 4, y)
        self.multi_cell(self.epw - 4, 6.0, text)
        self.ln(0.4)

    def code_block(self, code: str) -> None:
        self.ln(1.5)
        self.set_fill_color(*CODE_BG)
        self.set_text_color(*CODE_FG)
        self.set_font("body", size=FS_CODE)
        padded = code.rstrip("\n") or " "
        self.multi_cell(self.epw, 4.8, padded, fill=True)
        self.set_fill_color(*PAPER)
        self.set_text_color(*INK)
        self.ln(2)

    def hr(self) -> None:
        self.ln(3)
        mid = self.l_margin + self.epw / 2
        self.set_draw_color(*ACCENT)
        self.set_line_width(0.45)
        self.line(mid - 6, self.get_y(), mid + 6, self.get_y())
        self.ln(4)

    def write_table(self, header: list[str], rows: list[list[str]]) -> None:
        if not header:
            return
        self.ln(1.5)
        n = len(header)
        if n == 3:
            widths = (self.epw * 0.22, self.epw * 0.38, self.epw * 0.40)
        elif n == 2:
            widths = (self.epw * 0.30, self.epw * 0.70)
        else:
            widths = tuple(self.epw / n for _ in range(n))

        # Reset graphics state before table (avoids code-block black bleed)
        self.set_fill_color(*PAPER)
        self.set_text_color(*INK)
        self.set_draw_color(*RULE)
        self.set_line_width(0.2)
        self.set_font("body", size=FS_TABLE)

        heading = FontFace(
            emphasis="BOLD",
            color=INK,
            fill_color=TABLE_HEAD_BG,
            size_pt=FS_TABLE,
        )
        with super().table(
            col_widths=widths,
            width=self.epw,
            line_height=5.6,
            text_align="LEFT",
            first_row_as_headings=True,
            headings_style=heading,
            cell_fill_color=TABLE_ZEBRA,
            cell_fill_mode=TableCellFillMode.EVEN_ROWS,
            wrapmode=WrapMode.CHAR,
            padding=2.2,
            borders_layout="SINGLE_TOP_LINE",
        ) as tbl:
            head = tbl.row()
            for cell in header:
                head.cell(_strip_inline(cell))
            for row_data in rows:
                row = tbl.row()
                for i in range(n):
                    val = row_data[i] if i < len(row_data) else ""
                    row.cell(_strip_inline(val))
        self.set_fill_color(*PAPER)
        self.set_text_color(*INK)
        self.ln(2.5)


def _parse_table(lines: list[str], start: int) -> tuple[list[str], list[list[str]], int]:
    rows_raw: list[str] = []
    i = start
    while i < len(lines) and lines[i].strip().startswith("|"):
        rows_raw.append(lines[i].strip())
        i += 1

    def cells(row: str) -> list[str]:
        return [c.strip() for c in row.strip("|").split("|")]

    if len(rows_raw) < 2:
        return [], [], i
    header = cells(rows_raw[0])
    body: list[list[str]] = []
    for raw in rows_raw[1:]:
        if re.match(r"^\|?\s*:?-+:?\s*(\|\s*:?-+:?\s*)+\|?$", raw):
            continue
        body.append(cells(raw))
    return header, body, i


def _render_fpdf(md_path: Path, pdf_path: Path, title: str, body_md: str) -> str:
    pdf = SubmitPDF(footer_left=md_path.stem)
    pdf.add_page()
    pdf.cover_block(title)

    lines = body_md.replace("\r\n", "\n").split("\n")
    i = 0
    in_code = False
    code_buf: list[str] = []

    while i < len(lines):
        line = lines[i]
        stripped = line.strip()

        if stripped.startswith("```"):
            if in_code:
                pdf.code_block("\n".join(code_buf))
                code_buf = []
                in_code = False
            else:
                in_code = True
            i += 1
            continue
        if in_code:
            code_buf.append(line)
            i += 1
            continue

        if not stripped:
            pdf.ln(2)
            i += 1
            continue

        if stripped.startswith("|"):
            header, rows, i = _parse_table(lines, i)
            if header:
                pdf.write_table(header, rows)
            continue

        if re.match(r"^---+$", stripped):
            pdf.hr()
            i += 1
            continue

        if stripped.startswith("### "):
            pdf.h3(_strip_inline(stripped[4:]))
            i += 1
            continue
        if stripped.startswith("## "):
            pdf.h2(_strip_inline(stripped[3:]))
            i += 1
            continue
        if stripped.startswith("# "):
            pdf.h2(_strip_inline(stripped[2:]))
            i += 1
            continue

        if stripped.startswith("> "):
            parts: list[str] = []
            while i < len(lines) and lines[i].strip().startswith(">"):
                q = lines[i].strip()
                parts.append(_strip_inline(q[1:].lstrip()))
                i += 1
            pdf.quote("\n".join(parts))
            continue

        if stripped.startswith("- ") or stripped.startswith("* "):
            pdf.bullet(_strip_inline(stripped[2:]))
            i += 1
            continue

        pdf.para(_strip_inline(stripped))
        i += 1

    if in_code and code_buf:
        pdf.code_block("\n".join(code_buf))

    pdf.output(str(pdf_path))
    return pdf.font_label


def render_md_to_pdf(md_path: Path, pdf_path: Path | None = None) -> Path:
    md_path = md_path.resolve()
    pdf_path = (pdf_path or md_path.with_suffix(".pdf")).resolve()
    raw = md_path.read_text(encoding="utf-8")
    title, body_md = _extract_title(raw, fallback=md_path.stem)
    font_name = _render_fpdf(md_path, pdf_path, title, body_md)
    print(f"  font={font_name}")
    return pdf_path


def main() -> None:
    targets = [
        HERE / "ENGINEERING.md",
        HERE / "DATA_COMPLIANCE.md",
    ]
    for md in targets:
        if not md.exists():
            raise SystemExit(f"Missing {md}")
        out = render_md_to_pdf(md)
        print(f"OK {md.name} -> {out.name} ({out.stat().st_size} bytes)")


if __name__ == "__main__":
    main()
