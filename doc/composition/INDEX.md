# ILearn 开源参考库索引（composition）

> 本地目录：`doc/composition/`（**不上传 GitHub**，见根目录 `.gitignore`）  
> 来源清单：`doc/open_source.txt`  
> 目标：为 ILearn 多 Agent 系统提供可借鉴模块，**组合而非抄袭**。

## 克隆状态（2026-08-10）

| 目录 | open_source 条目 | 状态 |
|------|------------------|------|
| WeSmartFlow | WeSmartFlow (腾讯) | ✅ 已拉取 |
| DeepTutor | DeepTutor (港大) | ✅ 已拉取 |
| Personal-Canvas-Agent | Personal Canvas Agent | ✅ 已拉取 |
| LearnGraph | LearnGraph | ✅ 已拉取 |
| StudyCoach | StudyCoach | ✅ 已拉取 |
| inno-agent | Inno Agent | ✅ 已拉取 |
| Socratic-Education-System | Socratic Education System | ✅ 已拉取 |
| EduNex-Autonomous-AI-Tutor-for-Every-Student-Demo | EduNex | ✅ 已拉取 |
| OpenMAIC | OpenMAIC (清华) | ✅ 已拉取 |
| Claw-ED | Claw-ED | ✅ 已拉取 |
| Chinese-Teaching-AI-Agent | Chinese-Teaching-AI-Agent | ✅ 已拉取 |
| EduAgents | EduAgents | ✅ 已拉取 |
| LanguageMentor | LanguageMentor | ✅ 已拉取 |
| ai-vocab-agent | AI Vocab Agent | ✅ 已拉取 |
| learn-pi | learn-pi | ✅ 已拉取 |
| ProMentor | ProMentor | ✅ 已拉取 |
| latent | Latent | ✅ 已拉取 |
| OpenClaw-Education-Skills | Awesome OpenClaw Education Skills | ✅ 已拉取 |
| education-agent-skills | education-agent-skills | ✅ 已拉取 |
| ECNUClaw | ECNUClaw (华东师大) | ✅ 已拉取 |
| Dewey | Dewey | ✅ 已拉取 |
| tutor_gym | TutorGym | ✅ 已拉取 |
| mathtutorbench | MathTutorBench | ✅ 已拉取 |
| AI-Shool-Counselor | AI辅导员智能体系统 | ✅ 已拉取 |
| hermes-edu-skills | Hermes Edu Skills | ❌ GitHub 仓库未找到（可 npm: `hermes-edu-skills`） |
| xiaozhi-skills | xiaozhi-skills | ❌ 克隆失败（网络/仓库路径待确认） |
| EduAgentBench | EduAgentBench | ❌ 无公开 GitHub；数据集见 [HuggingFace](https://huggingface.co/datasets/eduagentbench/eduagentbench) |
| EduGemma | EduGemma | ❌ 未找到稳定公开仓库（Google Gemma 生态，待单独调研） |
| CAATS | CAATS (编程辅导) | ⚠️ 同名 `kpostekk/caats` 为课表服务，非教育 Agent；编程多 Agent 可参考 CodeEdu 论文 |
| AIFL | AIFL | ❌ 未拉取（待补充 URL） |

**已拉取：24 个** · **待补充：5+ 个**

## 文档导航

| 文件 | 内容 |
|------|------|
| [ANALYSIS_BY_REPO.md](./ANALYSIS_BY_REPO.md) | v1 初筛（README + 核心文件概览） |
| **[ANALYSIS_BY_REPO_v2.md](./ANALYSIS_BY_REPO_v2.md)** | **v2 深度审计（24 仓库 × 8 块 + synthesis）** |
| **[OPTIMIZATION_BACKLOG.md](./OPTIMIZATION_BACKLOG.md)** | **按 Agent 分类优化 backlog（P0/P1/P2）** |
| **[TODO.md](./TODO.md)** | **未完成全清单（partial + P1/P2 + 延期 + 评测 + 文档债）** |
| [MULTI_AGENT_ARCHITECTURE.md](./MULTI_AGENT_ARCHITECTURE.md) | ILearn 多 Agent 架构（P0 已实现） |
| [AGENT_MAPPING.md](./AGENT_MAPPING.md) | 四大 Agent ↔ 开源对照 |

## ILearn 当前状态（2026-08-10 更新）

GitHub **`master`** 已合入：

- MVP + Multi-Agent P0（6 Agent + Orchestrator + VL 离线降级）
- Composition Phase 1 收尾 ✅（A-01…A-05、G-01…G-06、F-01…F-04 已验收；见 `TODO.md`）
- Composition Phase 2a 诊断/证据 ✅（OPT-023…026、OPT-074；198 tests）
- Composition Phase 2b 规划/辅导 ✅（OPT-014、OPT-031…034、OPT-060；234 tests）
- 回归基线约 **234** tests

**未完成全量：** 见 **[TODO.md](./TODO.md)**（P1×12、P2×7、评测基准、F-05…F-07 等）。

**下一阶段建议：** **Composition Phase 2c**（课标向量 RAG + K12 扩展，见 `TODO.md` §H）。A-03 向量 Qdrant 索引为 2c 重点。
