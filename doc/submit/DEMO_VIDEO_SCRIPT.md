# ILearn Demo 视频脚本（60 秒）

> 用途：GOAI 2026 赛道二现场演示备用录屏 / 讲解词  
> 录制工具建议：OBS Studio / 腾讯会议录制；或 **look / look-demo**（见 `LOOK_SETUP.md` + `look-demo-script.json`）  
> 分辨率：1920×1080，浏览器全屏或最大化，隐藏无关书签栏

---

## 一、开录前检查清单

1. 后端：`uvicorn ilearn.api.app:app --reload --host 127.0.0.1 --port 8000`
2. 前端：`cd frontend && npm run dev` → `http://127.0.0.1:5173`
3. 浏览器无痕窗口，缩放 100%，关闭通知
4. 提前点一次「体验小数乘法」确认 demo 可用（可丢弃该会话再开录）
5. 麦克风测试；话术放在第二屏，避免录到讲稿窗口

---

## 二、分镜与话术（总计约 60 秒）

| 时间 | 画面操作 | 口播话术 | 备注 |
|------|----------|----------|------|
| 0–5s | 打开 `http://127.0.0.1:5173` Landing Page，停留展示品牌与入口 | 「各位评委好，现在为您演示 ILearn 的完整教学闭环。」 | 截图存为 `01_landing_page.png` |
| 5–15s | 滚到「体验完整教学单元」；角色选「教师」；点击「体验小数乘法」 | 「我们预置了五年级小数乘法单元，一键进入，无需注册。」 | 等待跳转教师端 |
| 15–25s | 教师端：班级指标卡、薄弱点排行、干预学生；点开一名学生 | 「这是教师端——班级平均掌握度清晰可见，薄弱点排行与干预名单帮助老师精准定位。」 | `02_teacher_dashboard.png` |
| 25–35s | 回到 Landing（或新开标签）选角色「学生」再体验；展示测评/学情页 | 「切换到学生端——系统自适应组卷，错题可走苏格拉底引导，最多三级提示。」 | 若时间紧：直接用 demo 学生链接 |
| 35–45s | 角色「家长」进入家长端；展示事实摘要与辅导建议 | 「家长端——技术术语已译成日常用语，家长看到的是可操作的家庭辅导建议，而不是内部知识点 ID。」 | `03_parent_dashboard.png` |
| 45–55s | 教师端学情详情中的「教学效果验证」面板 | 「效果量化——掌握度前后对比、批改时间节省、诊断置信度与证据可追溯；演示数据会标明模拟来源。」 | `04_effectiveness_panel.png` |
| 55–60s | 可点一次「导出学习报告 PDF」，展示下载或引擎徽章后收尾 | 「以上就是 ILearn 从测评到巩固的完整闭环：一条链路，三端协同，数据驱动。」 | 可选 `05_pdf_export.png` |

---

## 三、压缩版（若现场仅剩 45 秒）

1. Landing（5s）→ 教师端班级扫描（15s）→ 家长端摘要（10s）→ 效果量化（10s）→ 收尾（5s）  
2. 学生端改为口头一句带过：「学生端支持自适应测评与苏格拉底辅导。」

---

## 四、录制文件命名

```text
runtime_evidence/demo_recording.mp4
runtime_evidence/demo_screenshots/
  01_landing_page.png
  02_teacher_dashboard.png
  03_parent_dashboard.png
  04_effectiveness_panel.png
  05_pdf_export.png
```

---

## 五、API 旁路验证（录屏前可选）

```bash
# 创建演示会话
curl -X POST http://127.0.0.1:8000/demo/units/math_5_1/session

# 三端摘要（家长端不得出现 kp_ / dec_）
curl http://127.0.0.1:8000/sessions/<SESSION_ID>/summary/teacher
curl http://127.0.0.1:8000/sessions/<SESSION_ID>/summary/parent
curl http://127.0.0.1:8000/sessions/<SESSION_ID>/summary/student

# 效果量化
curl http://127.0.0.1:8000/sessions/<SESSION_ID>/effectiveness

# PDF
curl -o report.pdf http://127.0.0.1:8000/sessions/<SESSION_ID>/export/report.pdf
curl -o effectiveness.pdf http://127.0.0.1:8000/sessions/<SESSION_ID>/export/effectiveness.pdf
```

详细命令与预期字段见 `runtime_evidence/README.md`。
