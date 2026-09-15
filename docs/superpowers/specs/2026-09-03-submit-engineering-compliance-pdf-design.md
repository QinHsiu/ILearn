# Design: GOAI 提交工程说明 + 数据合规 PDF

**日期：** 2026-09-03  
**来源：** `doc/talk.txt` 材料一 / 材料二  
**已批准方案：** A（Markdown → 定制 CSS + WeasyPrint → PDF）

## 目标

生成两份可提交的工程/合规文档：先维护 Markdown，再渲染为版式统一的 A4 PDF（中文字体、表格、代码块可读）。

## 产出

| 文件 | 说明 |
|------|------|
| `doc/submit/ENGINEERING.md` | 代码仓库与工程材料（材料一） |
| `doc/submit/ENGINEERING.pdf` | 同上 PDF |
| `doc/submit/DATA_COMPLIANCE.md` | 数据来源与合规说明（材料二；内容对齐并扩展现有 `COMPLIANCE.md`） |
| `doc/submit/DATA_COMPLIANCE.pdf` | 同上 PDF |
| `doc/submit/md_to_pdf.py` | 将上述两份 MD 转为 PDF 的脚本 |

保留 `doc/submit/COMPLIANCE.md`：在文件头加一句指向 `DATA_COMPLIANCE.md` 的说明，避免旧链接失效；不以 COMPLIANCE 为主文件名。

## 内容范围

- **ENGINEERING：** 运行入口、依赖表、配置、示例数据、部署、测试、运行证据（完整采用 `talk.txt` 材料一）。
- **DATA_COMPLIANCE：** 数据类型、来源、授权、处理方式、隐私、风险、使用边界、合规声明（完整采用 `talk.txt` 材料二）。
- 封面/页眉元信息：ILearn · GOAI 2026 · 赛道二 AI+教育 · GitHub `https://github.com/QinHsiu/ILearn` · 日期 2026-09-06。

## PDF 版式

- 纸张：A4；页边距约 18–20mm；页脚：文档名 + 页码 + 仓库短链。
- 字体：正文 Microsoft YaHei（回退 DengXian / SimHei）；代码 Consolas / Cascadia Mono / 等宽回退。
- 色板：主色 `#002FA7` / `#165DFF`，正文 `#222`，表头蓝底白字，斑马纹行，浅灰边框。
- 表格：全宽、`border-collapse`、单元格内边距充足，避免折行过密。
- 代码块：深色背景、圆角、小号等宽字；行内 `code` 浅底。
- 标题：H1 文档标题；H2 章节（带底部分隔或左侧色条）；列表行距舒适。

## 转换管线

1. 用 `markdown`（或轻量解析）将 MD 转为 HTML body。
2. 套统一 CSS 模板（与 `doc/t.py` 色系一致，但按「多页文档」而非单页幻灯排）。
3. WeasyPrint `HTML(...).write_pdf()`；字体通过 `@font-face` 指向 `C:\Windows\Fonts\msyh.ttc`（及回退）。
4. 一键：`python doc/submit/md_to_pdf.py` 同时输出两份 PDF。

## 非目标

- 不改仓库业务代码、不改 Demo PPT。
- 不强制 Docker/生产部署细节超出 `talk.txt`。
- 不签署真实授权书（`AUTHORIZATION.txt` 模板保持原样）。

## 验收

- 两份 MD 可读、表格完整。
- 两份 PDF 可打开：中文无乱码、表格对齐、代码块不溢出页宽、页脚页码正常。
- `doc/submit/README.md` 索引更新为指向新文件。
