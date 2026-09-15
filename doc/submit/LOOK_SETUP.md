# 用 look / look-demo 生成 ILearn Demo 视频

对应口播与分镜见 `DEMO_VIDEO_SCRIPT.md`；脚本化操作见 `look-demo-script.json`。

## 本机现状（已检查）

| 依赖 | 状态 |
|------|------|
| Node.js ≥ 18 | 已有（当前约 v24） |
| FFmpeg | **未安装 / 不在 PATH** |
| `OPENAI_API_KEY` | **未设置** |
| `look` / `look-demo` | **未安装** |

装齐前不要指望能导出 mp4。

## 1. 安装 FFmpeg（Windows）

任选其一，装完**新开终端**验证：

```powershell
ffmpeg -version
```

- 官网：https://ffmpeg.org/download.html → Windows builds → 解压后把 `bin` 加入系统 PATH  
- 若已装 Chocolatey：`choco install ffmpeg`  
- 若已装 Scoop：`scoop install ffmpeg`

## 2. 安装 CLI

文档里 `npm install -g look-demo` 与命令 `look quick` 对应同一产品线（LooK）。建议：

```powershell
npm install -g look-demo
# 若 look 命令不存在，再试：
# npm install -g @nirholas/look
look --help
# 或
look-demo --help
```

首次可能还需 Playwright 浏览器：

```powershell
npx playwright install chromium
```

## 3. 设置 OpenAI Key（PowerShell）

当前会话：

```powershell
$env:OPENAI_API_KEY = "sk-你的密钥"
```

持久化（用户级，按需）：

```powershell
[System.Environment]::SetEnvironmentVariable("OPENAI_API_KEY", "sk-你的密钥", "User")
```

**不要把 Key 写进仓库文件。**

## 4. 先启动 ILearn

两个终端：

```powershell
# 后端
cd d:\PycharmProjects\pythonProject\projects\ILearn
uvicorn ilearn.api.app:app --reload --host 127.0.0.1 --port 8000
```

```powershell
# 前端
cd d:\PycharmProjects\pythonProject\projects\ILearn\frontend
npm run dev
```

确认浏览器能打开 `http://127.0.0.1:5173`，并点一次「体验小数乘法」预热。

## 5. GOAI 正式 Demo 成片（约 7.5 分钟）

按 `doc/video.txt` 分段录屏 + **edge-tts**（`zh-CN-XiaoxiaoNeural`）+ FFmpeg 拼接：

```powershell
# 前后端已启动
python scripts/build_goai_demo_video.py
# 若只重做音画对齐/拼接：
python scripts/build_goai_demo_video.py --mux-only
```

成片：`runtime_evidence/赛道二_无界应用_ILearn_第16队_Demo视频.mp4`  
分镜配置：`doc/submit/goai_video_segments.json`

> 说明：`look-demo` 多场景会覆盖输出，故分段用 Playwright 浏览器录屏（同类自动化），配音用免费 edge-tts，不用 OpenAI。

## 6. 生成短片（60s 备用）

`look-demo` 每个场景会覆盖同一个 mp4，多场景几乎只剩最后一段。请用：

```powershell
# 前后端已启动后，在仓库根目录：
node scripts/record_ilearn_demo.mjs
```

产出：约 60s 的 `runtime_evidence/demo_recording.mp4`，以及 `demo_screenshots/01–05.png`。

### 备选：look-demo（仅适合单场景）

```powershell
look-demo record --url http://127.0.0.1:5173 --script doc/submit/look-demo-script.json --no-voiceover -o runtime_evidence/demo_recording.mp4
```

### A. 快速 AI 录制（少控制）

```powershell
look demo http://127.0.0.1:5173 --duration 60 --voice onyx --style professional -o runtime_evidence/demo_recording.mp4
```

或：

```powershell
look quick http://127.0.0.1:5173
```

本地 SPA 建议加 `--reliable`（若 CLI 支持），减少 AI 乱点。

### B. 按我们写好的分镜脚本（推荐，口播对齐提交稿）

```powershell
look-demo record --url http://127.0.0.1:5173 --script doc/submit/look-demo-script.json --width 1920 --height 1080 --voice onyx -o runtime_evidence/demo_recording.mp4
```

若二进制名是 `look`：

```powershell
look-demo record --url http://127.0.0.1:5173 --script doc/submit/look-demo-script.json -o runtime_evidence/demo_recording.mp4
```

以 `look --help` / `look-demo --help` 里实际子命令为准。

### C. 网页编辑器（可 Live Record）

```powershell
look serve
```

浏览器打开 `http://localhost:3847` → 填入 `http://127.0.0.1:5173` → Generate Demo 或 Live Record。

## 6. 产出物

- 视频：`runtime_evidence/demo_recording.mp4`
- 截图：`runtime_evidence/demo_screenshots/01_*.png` …（脚本里已写路径；若 CLI 忽略 screenshot action，仍按 DEMO 脚本手动补）

## 注意

- `look` 默认面向公网站点；本地 `127.0.0.1` 必须本机前后端已起。  
- AI `quick`/`demo` 可能点错入口；赛道提交优先 **脚本 / Live Record**。  
- 仍不上传 GitHub；成品只放本地 `runtime_evidence/`。
