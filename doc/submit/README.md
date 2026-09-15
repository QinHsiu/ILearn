# GOAI 2026 提交材料索引

本目录与仓库内相关路径对应 `doc/submit.txt` / `doc/talk.txt` 的交付物。

## 1. 项目方案 PPT / PDF

- 目录：`doc/goai-submit-deck/`
- PPTX：`doc/goai-submit-deck/ILearn_GOAI2026_项目方案.pptx`
- PDF：`doc/goai-submit-deck/ILearn_GOAI2026_项目方案.pdf`
- 可编辑源：`deck.pptd` + `pages/`

## 2. Demo 视频脚本

- `doc/submit/DEMO_VIDEO_SCRIPT.md`（60 秒分镜 + 话术 + API 旁路）
- `doc/submit/LOOK_SETUP.md`（look / look-demo 安装与录制）
- `doc/submit/look-demo-script.json`（与口播对齐的自动化分镜）

## 3. 代码仓库与工程材料

- Markdown：`doc/submit/ENGINEERING.md`
- PDF：`doc/submit/ENGINEERING.pdf`
- 源草稿：`doc/talk.txt` 材料一
- 生成脚本：`doc/submit/md_to_pdf.py`

## 4. 运行证据 runtime_evidence

- 目录：`runtime_evidence/`
- 说明：`runtime_evidence/README.md`
- 已含：pytest / vitest / 离线 CLI / Demo API 冒烟
- 待补：截图 PNG、`demo_recording.mp4`（若尚未放入）

## 5. 数据来源与合规

- Markdown：`doc/submit/DATA_COMPLIANCE.md`
- PDF：`doc/submit/DATA_COMPLIANCE.pdf`
- 精简摘要（兼容旧链）：`doc/submit/COMPLIANCE.md`
- 授权确认书模板：`doc/submit/AUTHORIZATION.txt`
- 源草稿：`doc/talk.txt` 材料二

## 建议提交打包清单

```text
ILearn_GOAI2026/
  ILearn_GOAI2026_项目方案.pptx
  ILearn_GOAI2026_项目方案.pdf
  DEMO_VIDEO_SCRIPT.md
  ENGINEERING.md
  ENGINEERING.pdf
  DATA_COMPLIANCE.md
  DATA_COMPLIANCE.pdf
  AUTHORIZATION.txt（签署扫描件可选）
  runtime_evidence/
  （代码仓库链接：https://github.com/QinHsiu/ILearn）
```

## 重新生成 PDF

```bash
python doc/submit/md_to_pdf.py
```
