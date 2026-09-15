# Submit ENGINEERING + DATA_COMPLIANCE PDF Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** From `doc/talk.txt`, produce Markdown + A4 PDF for engineering materials and data compliance, with WeasyPrint, Chinese fonts, and clear tables.

**Architecture:** Author two Markdown sources under `doc/submit/`. A single script wraps each MD in a shared HTML/CSS template (ILearn blue palette, YaHei, table/code styles) and calls WeasyPrint to write PDFs beside the MD files.

**Tech Stack:** Python 3, `markdown` (extra tables/fenced_code), WeasyPrint, Windows fonts (`msyh.ttc`).

## Global Constraints

- Content source of truth: `doc/talk.txt` 材料一 / 材料二 (do not invent conflicting facts).
- Brand colors: `#002FA7`, `#165DFF`; body text `#222`.
- Primary CJK font: Microsoft YaHei via `@font-face` on `C:/Windows/Fonts/msyh.ttc`.
- Output paths: `doc/submit/ENGINEERING.{md,pdf}`, `doc/submit/DATA_COMPLIANCE.{md,pdf}`.
- Keep `COMPLIANCE.md` as a short pointer to `DATA_COMPLIANCE.md`.
- Do not commit unless the user asks.

## File Structure

| File | Responsibility |
|------|----------------|
| `doc/submit/ENGINEERING.md` | Engineering material content |
| `doc/submit/DATA_COMPLIANCE.md` | Compliance material content |
| `doc/submit/md_to_pdf.py` | MD → HTML+CSS → PDF for both docs |
| `doc/submit/COMPLIANCE.md` | Redirect/pointer to DATA_COMPLIANCE |
| `doc/submit/README.md` | Index update for new artifacts |

---

### Task 1: Write ENGINEERING.md

**Files:**
- Create: `doc/submit/ENGINEERING.md`

**Interfaces:**
- Consumes: `doc/talk.txt` 材料一
- Produces: Markdown with H1/H2, GFM tables, fenced `bash`/`json` blocks

- [ ] **Step 1: Create `doc/submit/ENGINEERING.md`**

Include YAML-free header block then sections 1–7 from talk.txt:

```markdown
# ILearn 代码仓库与工程材料说明

> 项目：ILearn（课标在环 · 多 Agent 协同 · 自适应学习引擎）  
> 赛事：2026 世界人工智能开源大赛（GOAI 2026）｜赛道二 AI+教育  
> 仓库：https://github.com/QinHsiu/ILearn  
> 更新日期：2026-09-06

## 1. 运行入口
...
## 2. 依赖说明
（三列表格：依赖包 / 版本 / 用途）
...
## 7. 运行证据
```

Convert talk.txt pseudo-tables into real GFM pipes. Use fenced code for bash/json. No HTML in MD.

- [ ] **Step 2: Spot-check**

Open the file and confirm seven `##` sections and at least four tables exist.

---

### Task 2: Write DATA_COMPLIANCE.md + pointer

**Files:**
- Create: `doc/submit/DATA_COMPLIANCE.md`
- Modify: `doc/submit/COMPLIANCE.md` (replace body with pointer + keep short summary OR full redirect note at top)

**Interfaces:**
- Consumes: `doc/talk.txt` 材料二
- Produces: Markdown with sections 1–8

- [ ] **Step 1: Create `doc/submit/DATA_COMPLIANCE.md`**

```markdown
# ILearn 数据来源与合规说明

> 项目：ILearn …（同 ENGINEERING 元信息块）

## 1. 数据类型
## 2. 数据来源
## 3. 授权方式
## 4. 处理方式
## 5. 隐私保护
## 6. 行业风险提示
## 7. 使用边界与人工确认
## 8. 合规声明
```

Map talk.txt tables 1:1. Keep ✅ in授权表 if UTF-8 OK for WeasyPrint/YaHei.

- [ ] **Step 2: Update `COMPLIANCE.md`**

Prepend:

```markdown
> **本文档已迁移至 [`DATA_COMPLIANCE.md`](./DATA_COMPLIANCE.md)**（含完整表格与 PDF）。以下为精简摘要，详情以 DATA_COMPLIANCE 为准。
```

Keep existing summary body so old links still work.

---

### Task 3: Implement `md_to_pdf.py`

**Files:**
- Create: `doc/submit/md_to_pdf.py`

**Interfaces:**
- Consumes: `ENGINEERING.md`, `DATA_COMPLIANCE.md`
- Produces: `render_md_to_pdf(md_path: Path, pdf_path: Path | None = None) -> Path`; CLI `main()` renders both defaults

- [ ] **Step 1: Implement converter**

```python
"""Convert submit Markdown docs to branded A4 PDFs via WeasyPrint."""
from __future__ import annotations

from pathlib import Path

import markdown
from weasyprint import HTML

HERE = Path(__file__).resolve().parent
FONT_PATHS = [
    Path(r"C:\Windows\Fonts\msyh.ttc"),
    Path(r"C:\Windows\Fonts\msyh.ttf"),
    Path(r"C:\Windows\Fonts\Deng.ttf"),
    Path(r"C:\Windows\Fonts\simhei.ttf"),
]
MONO_PATHS = [
    Path(r"C:\Windows\Fonts\consola.ttf"),
    Path(r"C:\Windows\Fonts\cascadiamono.ttf"),
]

CSS_TEMPLATE = """
@font-face {{
  font-family: "DocSans";
  src: url("file:///{font}");
}}
@font-face {{
  font-family: "DocMono";
  src: url("file:///{mono}");
}}
@page {{
  size: A4;
  margin: 18mm 16mm 20mm 16mm;
  @bottom-center {{
    content: counter(page);
    font-family: "DocSans", "Microsoft YaHei", sans-serif;
    font-size: 9pt;
    color: #64748b;
  }}
  @bottom-left {{
    content: "{footer_left}";
    font-family: "DocSans", "Microsoft YaHei", sans-serif;
    font-size: 8pt;
    color: #94a3b8;
  }}
  @bottom-right {{
    content: "github.com/QinHsiu/ILearn";
    font-family: "DocSans", "Microsoft YaHei", sans-serif;
    font-size: 8pt;
    color: #94a3b8;
  }}
}}
html, body {{
  font-family: "DocSans", "Microsoft YaHei", sans-serif;
  font-size: 10.5pt;
  line-height: 1.55;
  color: #222;
}}
.doc-banner {{
  background: linear-gradient(90deg, #002FA7, #165DFF);
  color: #fff;
  padding: 14px 18px;
  margin: -6mm -4mm 14px -4mm;
  border-radius: 0 0 6px 6px;
}}
.doc-banner .eyebrow {{ font-size: 9pt; opacity: 0.9; }}
.doc-banner h1 {{
  margin: 4px 0 0;
  font-size: 18pt;
  color: #fff;
  border: none;
  padding: 0;
}}
h1 {{
  font-size: 18pt;
  color: #0f3460;
  border-bottom: 2px solid #165DFF;
  padding-bottom: 6px;
  margin-top: 0;
}}
h2 {{
  font-size: 13pt;
  color: #002FA7;
  margin: 18px 0 8px;
  padding-left: 8px;
  border-left: 4px solid #165DFF;
}}
h3 {{ font-size: 11.5pt; color: #1e293b; margin: 12px 0 6px; }}
blockquote {{
  margin: 8px 0 14px;
  padding: 8px 12px;
  background: #f1f5f9;
  border-left: 4px solid #165DFF;
  color: #334155;
  font-size: 9.5pt;
}}
table {{
  width: 100%;
  border-collapse: collapse;
  margin: 8px 0 14px;
  font-size: 9.5pt;
}}
th, td {{
  border: 1px solid #cbd5e1;
  padding: 6px 8px;
  vertical-align: top;
  text-align: left;
}}
th {{
  background: #165DFF;
  color: #fff;
  font-weight: 600;
}}
tr:nth-child(even) td {{ background: #f8fafc; }}
pre {{
  background: #0f172a;
  color: #e2e8f0;
  padding: 10px 12px;
  border-radius: 6px;
  font-family: "DocMono", Consolas, monospace;
  font-size: 8.5pt;
  line-height: 1.45;
  white-space: pre-wrap;
  word-break: break-word;
}}
code {{
  font-family: "DocMono", Consolas, monospace;
  font-size: 9pt;
  background: #eef2f8;
  padding: 1px 4px;
  border-radius: 3px;
}}
pre code {{ background: transparent; color: inherit; padding: 0; }}
ul, ol {{ margin: 6px 0 10px; padding-left: 1.3em; }}
li {{ margin: 3px 0; }}
p {{ margin: 6px 0; }}
a {{ color: #165DFF; text-decoration: none; }}
hr {{ border: none; border-top: 1px solid #e2e8f0; margin: 16px 0; }}
"""

def pick_font(candidates: list[Path]) -> Path:
    for p in candidates:
        if p.exists():
            return p
    raise SystemExit(f"No font found among: {candidates}")

def md_to_html(md_text: str, title: str, footer_left: str) -> str:
    body = markdown.markdown(
        md_text,
        extensions=["tables", "fenced_code", "nl2br", "sane_lists"],
    )
    # Pull first h1 into banner; strip duplicate if present
    font = pick_font(FONT_PATHS).as_posix()
    mono = pick_font(MONO_PATHS + FONT_PATHS).as_posix()
    css = CSS_TEMPLATE.format(
        font=font, mono=mono, footer_left=footer_left
    )
    return f"""<!DOCTYPE html>
<html lang="zh-CN"><head><meta charset="utf-8"/>
<title>{title}</title><style>{css}</style></head>
<body>
<div class="doc-banner">
  <div class="eyebrow">GOAI 2026 · 赛道二 AI+教育 · ILearn</div>
  <h1>{title}</h1>
</div>
{body}
</body></html>"""

def render_md_to_pdf(md_path: Path, pdf_path: Path | None = None) -> Path:
    md_path = md_path.resolve()
    pdf_path = (pdf_path or md_path.with_suffix(".pdf")).resolve()
    text = md_path.read_text(encoding="utf-8")
    # title from first # line
    title = md_path.stem
    for line in text.splitlines():
        if line.startswith("# "):
            title = line[2:].strip()
            break
    html = md_to_html(text, title=title, footer_left=md_path.stem)
    HTML(string=html, base_url=str(md_path.parent)).write_pdf(str(pdf_path))
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
```

Adjust banner so MD's own `#` title is not duplicated: either strip first H1 from body after conversion, or omit banner H1 and keep MD H1 styled. Prefer: after `markdown.markdown`, if body starts with `<h1>...</h1>`, remove it and use that text as banner title.

- [ ] **Step 2: Dry-run import**

Run: `python -c "import markdown; import weasyprint; print('ok')"`  
Expected: `ok` (install `markdown` / `weasyprint` if missing via project env).

---

### Task 4: Generate PDFs + update README

**Files:**
- Create: `doc/submit/ENGINEERING.pdf`, `doc/submit/DATA_COMPLIANCE.pdf`
- Modify: `doc/submit/README.md`

- [ ] **Step 1: Run converter**

```bash
cd d:\PycharmProjects\pythonProject\projects\ILearn
python doc/submit/md_to_pdf.py
```

Expected: two `OK ...` lines; PDFs > 10KB each.

- [ ] **Step 2: Visual/size check**

```bash
python -c "from pathlib import Path; 
for n in ['ENGINEERING.pdf','DATA_COMPLIANCE.pdf']:
 p=Path('doc/submit')/n; print(n, p.stat().st_size)"
```

Open PDFs and confirm: Chinese glyphs OK, tables have blue headers, code blocks wrap, footer page numbers present.

- [ ] **Step 3: Update `doc/submit/README.md` section 4**

Replace compliance-only section with:

```markdown
## 3. 代码仓库与工程材料

- Markdown：`doc/submit/ENGINEERING.md`
- PDF：`doc/submit/ENGINEERING.pdf`
- 源草稿：`doc/talk.txt` 材料一

## 4. 数据来源与合规

- Markdown：`doc/submit/DATA_COMPLIANCE.md`
- PDF：`doc/submit/DATA_COMPLIANCE.pdf`
- 精简摘要（兼容旧链）：`doc/submit/COMPLIANCE.md`
- 授权确认书模板：`doc/submit/AUTHORIZATION.txt`
```

Renumber runtime_evidence if needed so sections stay coherent with existing README.

- [ ] **Step 4: Done gate**

List `doc/submit/ENGINEERING.md`, `.pdf`, `DATA_COMPLIANCE.md`, `.pdf`, `md_to_pdf.py` all exist. Report absolute paths to user.

---

## Self-Review

1. Spec coverage: ENGINEERING + DATA_COMPLIANCE MD/PDF, md_to_pdf.py, COMPLIANCE pointer, README — all tasked.  
2. No TBD placeholders.  
3. `render_md_to_pdf(md_path, pdf_path=None) -> Path` consistent across tasks.
