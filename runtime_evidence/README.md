# runtime_evidence

本目录存放 GOAI 2026 提交用的**运行证据**。按 `doc/submit.txt` 清单组织。

## 目录结构

```text
runtime_evidence/
├── README.md
├── test_results_20260906.txt      # pytest -q 输出
├── frontend_test_results.txt      # frontend vitest 摘要
├── offline_run_log.txt            # CLI 离线闭环日志
├── demo_api_smoke.txt             # demo 会话 / 三端摘要 / effectiveness 抽样
├── demo_screenshots/
│   ├── README.md                  # 截图拍摄说明
│   ├── 01_landing_page.png        # 待录制后放入
│   ├── 02_teacher_dashboard.png
│   ├── 03_parent_dashboard.png
│   ├── 04_effectiveness_panel.png
│   └── 05_pdf_export.png
├── demo_recording.mp4             # 60 秒备用短片
└── demo.mp4                       # GOAI 正式 Demo（旁白+录屏，提交上传用）
```

## 已自动生成

| 文件 | 说明 |
|------|------|
| `test_results_20260906.txt` | 后端 `pytest -q` 原始输出 |
| `offline_run_log.txt` | `python -m ilearn.cli.main agents run --region 北京 --grade 5 --age 11 --offline` |
| `frontend_test_results.txt` | 前端 Vitest 摘要（修复 mock 后复跑） |
| `demo_api_smoke.txt` | Demo API 冒烟结果 |
| `demo.mp4` | 正式演示成片（edge-tts + 分段录屏） |

## 待人工补齐

1. **截图**（按 `demo_screenshots/README.md`；若已生成 `01–05.png` 可直接提交）  
2. ~~成片~~ 见 `demo.mp4`

## 复跑命令

```bash
# 后端
pytest -q | tee runtime_evidence/test_results_20260906.txt

# 前端
cd frontend && npm run test -- --run 2>&1 | tee ../runtime_evidence/frontend_test_results.txt

# 离线闭环
python -m ilearn.cli.main agents run --region 北京 --grade 5 --age 11 --offline 2>&1 | tee runtime_evidence/offline_run_log.txt

# Demo API 冒烟
python scripts/capture_demo_evidence.py
```

## 关联文档

- 视频脚本：`doc/submit/DEMO_VIDEO_SCRIPT.md`
- 合规说明：`doc/submit/COMPLIANCE.md`
- 授权模板：`doc/submit/AUTHORIZATION.txt`
- 项目方案 PPT：`doc/goai-submit-deck/`
