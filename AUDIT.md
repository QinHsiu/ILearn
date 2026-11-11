# ILearn Audit Readiness

ILearn 的可审计性以**宿主状态机 + append-only 事件日志 + 回执哈希**为骨架，不绑定 AutoGen / LangGraph / CrewAI 等第三方多 Agent 框架运行时。

编排立场：

| 项 | 说明 |
| --- | --- |
| 默认编排后端 | `HostStateMachineBackend`（会话阶段状态机） |
| LangGraph | 可选同构适配器 **stub**，非默认依赖（见 `ilearn.orchestration.backend`） |
| AutoGen | **不依赖**；已进入维护态并并入 Microsoft Agent Framework，ILearn 不将其列为推荐后端 |
| 决策证据 | `SessionState.event_log`（不可变事件）+ 兼容视图 `decision_log` |

## GAF-AI-EDU 映射（IEEE / 教育 AI 治理语言）

| 要求 | ILearn 对应 | 状态 |
| --- | --- | --- |
| 版本化 | `GradingReceipt.grader_version`；课标 / rubric 版本字段预留 | 部分覆盖 |
| 基于角色的访问控制 | Agent 写能力白名单；`data/agent_scopes.yaml` 按 Agent 分离 scope，可选 `ILEARN_SCOPE_*_KEY` | 部分覆盖（配置级分离已有；产品化登录 RBAC 未做） |
| 防篡改日志 | `content_hash` + 独立 `attestation_log.jsonl`；可选 `ILEARN_ATTESTATION_HMAC_KEY` 链式 HMAC | 部分覆盖（本地 HMAC 链已有；外部 TSA 未做） |
| 角色定义与职责分离 | Curriculum / Assessment / Practice / Diagnosis / Planning / Tutor / Eval 窄职责 | 已覆盖 |
| 定期审计周期 | 离线 `ilearn eval` + 本文件人工复核；无自动排期 | 未覆盖 |
| GDPR / EU AI Act / UNESCO 对齐 | 文档层声明与数据最小化实践；无正式合规包 | 未覆盖 |
| 密码学证据 | SHA-256 回执/事件摘要；无外部 TSA / 签名服务 | 部分覆盖 |

## EduAgentBench 三阶段映射（arXiv:2605.14322）

| Stage | 评测语言 | ILearn 证据坐标 |
| --- | --- | --- |
| Stage 1 教学判断 | 诊断与掌握判断 | `DiagnosisReport`、`KnowledgeEvidence`、practice/probe 双轨 |
| Stage 2 情境化辅导 | 辅导过程与护栏 | `TutorAgent` 状态机、`TutorRail` / `AnswerLeakRail`、Hint Ladder |
| Stage 3 教学工作流 | 环境状态、目标、过程证据、可见响应、工件质量 | 会话阶段状态机、`event_log` span 树、`GradingReceipt`、阶段落盘产物、`ilearn trace` |

过程证据（process evidence）在 ILearn 中对应：`evidence_log`、`KnowledgeEvidence`、`event_log` 输入/输出摘要哈希，以及批改回执。它们是部分信用的强乘数，而非“记了就算”。

## 分层回执契约（开放学科预留）

| 题型 | 回执 | “可审计”含义 |
| --- | --- | --- |
| 客观题 | `GradingReceipt`（`receipt_kind=objective`） | 可复现判分 + 内容哈希可独立验证 |
| 开放题 | `constructed` 题自动写 `receipt_kind=open_ended` + `rubric_version` + `judge_trace_snapshot` | 可审计的评分决策路径（不要求比特级复现） |

诊断输入组装会写入 `diagnosis_enrichment.context_compaction`（压缩**呈现**，不删除 `evidence_log`）。  
编排器 `diagnose()` 自动注入 `context_messages`（citation / grade / evidence 摘要行）与 `context_occupancy`。  
`PracticeAgent.grade_perception_outputs` 支持感知适配器输出接入，不改状态机。  
`SpeechAssessmentAdapter` 为可替换 ASR 适配器（需注入 `transcribe_fn`）。  
`CurriculumCitation.region` / `edition` 用于多 source pack 共存时消歧。

## CLI

```bash
ilearn trace <session_id>
ilearn audit replay <session_id>
ilearn audit derailment
ilearn resume <session_id> --decision continue|replan|human_takeover
```

批改后回执哈希写入 `data/sessions/attestations/<session_id>/attestation_log.jsonl`（与会话 JSON 物理分离）。  
Tutor 在 `done` 相位再收到输入时写入 `UNEXPECTED_STATE` 检查点：`data/sessions/checkpoints/<session_id>.unexpected.json`。

## 已知缺口（诚实清单）

1. 产品化登录 / 多租户 RBAC（当前为配置文件 scope + 可选 API key）  
2. 外部时间戳服务 / 公钥签名（本地 HMAC 链已可选启用）  
3. 开放题 / 口语完整流水线（已有分层回执与 SpeechAssessmentAdapter）  
4. 脱轨率已提供 CLI 聚合 + `reports/derailment_latest.json` 落盘；跨部署仪表盘仍待迭代
