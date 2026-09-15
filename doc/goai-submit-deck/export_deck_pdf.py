"""Generate GOAI submit deck PDF companion (8 landscape pages)."""

from pathlib import Path

from fpdf import FPDF

OUT = Path(__file__).resolve().parent / "deck.pdf"
FONT = r"C:\Windows\Fonts\simhei.ttf"
PRIMARY = (0, 47, 167)
SOFT = (238, 241, 247)
TEXT = (26, 35, 50)
MUTED = (95, 107, 122)
ACCENT = (76, 175, 80)
WHITE = (255, 255, 255)


class Deck(FPDF):
    def header(self) -> None:
        return


def main() -> None:
    pdf = Deck(orientation="L", format="A4", unit="mm")
    pdf.set_auto_page_break(False)
    pdf.add_font("hei", "", FONT)

    w, h = 297, 210

    def bg(rgb: tuple[int, int, int]) -> None:
        pdf.set_fill_color(*rgb)
        pdf.rect(0, 0, w, h, "F")

    def box(x: float, y: float, bw: float, bh: float, fill=WHITE) -> None:
        pdf.set_fill_color(*fill)
        pdf.set_draw_color(201, 204, 210)
        pdf.rect(x, y, bw, bh, "DF")

    def text(
        x: float,
        y: float,
        s: str,
        size: int = 14,
        color=TEXT,
    ) -> None:
        pdf.set_font("hei", size=size)
        pdf.set_text_color(*color)
        # fpdf text baseline: place near top of intended line
        for i, line in enumerate(s.split("\n")):
            pdf.text(x, y + 4 + i * (size * 0.5), line)

    # P1 Cover
    pdf.add_page()
    bg(PRIMARY)
    text(18, 22, "2026 世界人工智能开源大赛  ·  GOAI 2026", 12, (168, 182, 224))
    pdf.set_fill_color(*ACCENT)
    pdf.rect(18, 70, 18, 1.6, "F")
    text(18, 82, "ILearn", 36, WHITE)
    text(18, 105, "课标在环 · 多 Agent 协同 · 自适应学习引擎", 14, (214, 221, 240))
    pdf.set_fill_color(26, 75, 196)
    pdf.rect(18, 130, 55, 12, "F")
    text(22, 133, "赛道二 | AI+教育", 12, WHITE)
    text(18, 165, "第 16 队  ·  2026.09.06", 11, (168, 182, 224))
    text(18, 178, "https://github.com/QinHsiu/ILearn", 11, (168, 182, 224))

    # P2 Pain
    pdf.add_page()
    bg(SOFT)
    pdf.set_fill_color(*PRIMARY)
    pdf.rect(18, 14, 14, 1.4, "F")
    text(18, 22, "一个课堂、同一进度，为什么有的孩子越学越吃力？", 15, PRIMARY)
    box(18, 42, 125, 95)
    text(24, 50, "现实困境", 14, PRIMARY)
    text(24, 68, "42% 小学生认为数学最难学好", 12)
    text(24, 84, "班级掌握度差异高达 30%+", 12)
    text(24, 100, "统一进度下，缺口只会越拖越远", 12)
    box(154, 42, 125, 95)
    text(160, 50, "核心洞察", 14, PRIMARY)
    text(160, 68, "同一进度推着所有人走", 12)
    text(160, 84, "每个孩子的知识缺口完全不同", 12)
    text(160, 100, "有人卡在「小数乘法」", 12)
    text(160, 116, "有人困在「分数除法」", 12)
    text(18, 155, "用同一个节奏教全班，跟不上的孩子只会越拖越远。", 12)
    text(18, 172, "ILearn 要解决的，就是这个真实困境。", 13, PRIMARY)

    # P3 Solution
    pdf.add_page()
    bg(SOFT)
    pdf.set_fill_color(*PRIMARY)
    pdf.rect(18, 14, 14, 1.4, "F")
    text(18, 22, "ILearn 解决方案", 16, PRIMARY)
    text(18, 36, "课标在环 · 多 Agent 协同 · 自适应个性化学习", 11, MUTED)
    box(18, 48, 261, 55)
    text(24, 58, "测评 → 批改 → 诊断 → 规划 → 巩固", 14, PRIMARY)
    text(24, 76, "找缺口　　即时反馈　　定位根因　　生成方案　　闭环验证", 11)
    roles = [
        ("教师端", "班级扫描与干预\n薄弱点排行 · 优先名单"),
        ("家长端", "纯净报告与建议\n日常用语 · 可操作"),
        ("学生端", "自适应测评与激励\n苏格拉底引导 · 星星"),
    ]
    for i, (title, body) in enumerate(roles):
        x = 18 + i * 88
        box(x, 118, 82, 60)
        text(x + 6, 128, title, 13, PRIMARY)
        text(x + 6, 145, body, 11)

    # P4 Agents
    pdf.add_page()
    bg(SOFT)
    pdf.set_fill_color(*PRIMARY)
    pdf.rect(18, 14, 14, 1.4, "F")
    text(18, 22, "多 Agent 协同架构", 16, PRIMARY)
    text(18, 36, "五 Agent 流水线协同 · 全流程可观测、可追溯", 11, MUTED)
    rows = [
        ("Agent", "职责", "关键能力"),
        ("Curriculum", "课标检索", "keyword / hash_vector / Qdrant 对齐"),
        ("Assessment", "自适应组卷", "诊断卷 · 巩固卷 · 能力分层"),
        ("Practice / Tutor", "批改与辅导", "即时反馈 · 苏格拉底三级提示"),
        ("Diagnosis", "证据诊断", "Evidence Log · diagnosis_confidence"),
        ("Planning", "计划生成", "科学学习方法 · 间隔复习 · 可重规划"),
    ]
    y = 48
    for i, (a, b, c) in enumerate(rows):
        rh = 16
        fill = PRIMARY if i == 0 else (WHITE if i % 2 else SOFT)
        tc = WHITE if i == 0 else TEXT
        pdf.set_fill_color(*fill)
        pdf.set_draw_color(201, 204, 210)
        pdf.rect(18, y, 261, rh, "DF")
        text(22, y + 4, a, 10, tc)
        text(78, y + 4, b, 10, tc)
        text(128, y + 4, c, 10, tc)
        y += rh
    text(18, 160, "关键能力：课标对齐 · 证据驱动 · 编排可观测（decision_log + 上下文预算）", 11)
    text(18, 175, "零 LLM 可离线降级运行，规则引擎保障演示与试点稳定性", 11, MUTED)

    # P5 Pipeline
    pdf.add_page()
    bg(SOFT)
    pdf.set_fill_color(*PRIMARY)
    pdf.rect(18, 14, 14, 1.4, "F")
    text(18, 22, "完整任务链路：从诊断到巩固", 16, PRIMARY)
    box(18, 42, 261, 120)
    steps = [
        "01 用户输入　选择年级 / 学科 → 开始测评",
        "02 Agent 处理　自适应组卷 → 智能批改 → 证据诊断",
        "03 工具与知识库　课标检索 → 题库匹配 → 知识图谱",
        "04 结果交付　个性化学习计划 → 三端报告 → PDF 导出",
        "05 异常处理　LLM 降级 → 规则引擎备用 → 超时自动提交",
        "06 效果验证　前后对比 → 掌握度提升 → 批改时间节省",
    ]
    for i, s in enumerate(steps):
        text(28, 52 + i * 16, s, 12)
    text(18, 178, "一条链路，完整闭环，可验证", 14, ACCENT)

    # P6 Roles
    pdf.add_page()
    bg(SOFT)
    pdf.set_fill_color(*PRIMARY)
    pdf.rect(18, 14, 14, 1.4, "F")
    text(18, 22, "三端协同，各取所需", 16, PRIMARY)
    role_cards = [
        ("教师端", ["班级掌握度", "薄弱点排行", "干预学生列表", "导出班级报告", "从批改中解放，聚焦教学"]),
        ("家长端", ["孩子学习进度", "家庭辅导建议", "无术语报告", "看得懂、可操作", "日常用语，降低焦虑"]),
        ("学生端", ["自适应测评", "苏格拉底引导", "星星激励", "进度可视化", "个性化路径，即时反馈"]),
    ]
    for i, (title, lines) in enumerate(role_cards):
        x = 18 + i * 90
        box(x, 42, 84, 110)
        text(x + 6, 52, title, 13, PRIMARY)
        for j, line in enumerate(lines):
            text(x + 6, 70 + j * 14, line, 10 if j < 4 else 9, TEXT if j < 4 else MUTED)
    text(18, 168, "差异化价值：教师拿班级干预清单 · 家长拿家庭辅导建议 · 学生拿个性化巩固路径", 11, MUTED)
    text(18, 182, "家长端强制清洗内部 ID，不出现 kp_* / 课标黑话", 11, MUTED)

    # P7 Effectiveness
    pdf.add_page()
    bg(SOFT)
    pdf.set_fill_color(*PRIMARY)
    pdf.rect(18, 14, 14, 1.4, "F")
    text(18, 22, "教学效果量化验证", 16, PRIMARY)
    metrics = [
        ("掌握度提升", "诊断前 45% → 巩固后 78%\n↑ 提升 33%"),
        ("批改时间节省 70%", "传统 90 分钟\nILearn 15 分钟"),
        ("诊断置信度 85%+", "基于证据日志\n结论可追溯审计"),
    ]
    for i, (t, b) in enumerate(metrics):
        x = 18 + i * 90
        box(x, 42, 84, 48)
        text(x + 5, 50, t, 11, PRIMARY)
        text(x + 5, 66, b, 10)
    cmp_rows = [
        ("对比维度", "传统教学", "ILearn"),
        ("批改耗时", "90 分钟", "15 分钟"),
        ("个性化程度", "统一作业", "自适应"),
        ("反馈周期", "1–2 天", "即时"),
        ("薄弱点识别", "经验判断", "数据驱动"),
    ]
    y = 105
    for i, (a, b, c) in enumerate(cmp_rows):
        rh = 14
        fill = PRIMARY if i == 0 else (WHITE if i % 2 else SOFT)
        tc = WHITE if i == 0 else TEXT
        pdf.set_fill_color(*fill)
        pdf.set_draw_color(201, 204, 210)
        pdf.rect(18, y, 261, rh, "DF")
        text(24, y + 3, a, 10, tc)
        text(100, y + 3, b, 10, tc)
        text(190, y + 3, c, 10, tc)
        y += rh

    # P8 Closing
    pdf.add_page()
    bg(SOFT)
    pdf.set_fill_color(*PRIMARY)
    pdf.rect(18, 14, 14, 1.4, "F")
    text(18, 22, "技术实现 · 合规 · 开源", 16, PRIMARY)
    box(18, 42, 125, 80)
    text(24, 50, "技术栈与质量", 13, PRIMARY)
    text(24, 68, "FastAPI + React · Pydantic + Vite", 10)
    text(24, 82, "Qdrant + WeasyPrint / fpdf2", 10)
    text(24, 96, "554+ 后端测试 · 73+ 前端测试", 10)
    text(24, 110, "零 LLM 可离线运行", 10)
    box(154, 42, 125, 80)
    text(160, 50, "数据与合规", 13, PRIMARY)
    text(160, 68, "小学数学 4–6 年级 · 人教课标", 10)
    text(160, 82, "公开题库 + 模拟画像（化名）", 10)
    text(160, 96, "无真实个人信息持久化", 10)
    text(160, 110, "AI 诊断仅供参考，需教师确认", 10)
    pdf.set_fill_color(*PRIMARY)
    pdf.rect(18, 138, 261, 48, "F")
    text(24, 148, "ILearn —— 让每个孩子拥有课标对齐、数据驱动、持续进化的 AI 学习伙伴", 11, WHITE)
    text(24, 164, "开源：https://github.com/QinHsiu/ILearn  ·  60 秒上手", 11, (214, 221, 240))
    text(24, 176, "感谢评委，欢迎提问！", 11, WHITE)

    pdf.output(str(OUT))
    print(f"wrote {OUT} ({OUT.stat().st_size} bytes)")


if __name__ == "__main__":
    main()
