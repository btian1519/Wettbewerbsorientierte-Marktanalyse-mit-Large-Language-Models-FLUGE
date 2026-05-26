"""
Generate FlightScope AI presentation PPT (Chinese version)
"""
from pptx import Presentation
from pptx.util import Inches, Pt, Emu
from pptx.dml.color import RGBColor
from pptx.enum.text import PP_ALIGN
from pptx.util import Inches, Pt
import copy

# ── Color Palette ──────────────────────────────────────────────────────────
C_BG        = RGBColor(0x0F, 0x11, 0x17)   # dark background
C_ACCENT    = RGBColor(0x6C, 0x63, 0xFF)   # purple accent
C_ACCENT2   = RGBColor(0x00, 0xD4, 0xAA)   # teal accent
C_WHITE     = RGBColor(0xFF, 0xFF, 0xFF)
C_LIGHT     = RGBColor(0xC5, 0xCA, 0xE9)   # light text
C_MUTED     = RGBColor(0x88, 0x92, 0xB0)   # muted text
C_GREEN     = RGBColor(0x00, 0xE6, 0x76)
C_ORANGE    = RGBColor(0xFF, 0x70, 0x43)
C_YELLOW    = RGBColor(0xFF, 0xCA, 0x28)
C_CARD      = RGBColor(0x1A, 0x1D, 0x27)   # card background

prs = Presentation()
prs.slide_width  = Inches(13.33)
prs.slide_height = Inches(7.5)

BLANK = prs.slide_layouts[6]  # completely blank layout


# ── Helpers ────────────────────────────────────────────────────────────────

def add_bg(slide, color=C_BG):
    """Fill slide background with solid color."""
    bg = slide.background
    fill = bg.fill
    fill.solid()
    fill.fore_color.rgb = color


def add_rect(slide, left, top, width, height, fill_color, alpha=None):
    """Add a filled rectangle shape."""
    shape = slide.shapes.add_shape(
        1,  # MSO_SHAPE_TYPE.RECTANGLE
        Inches(left), Inches(top), Inches(width), Inches(height)
    )
    shape.fill.solid()
    shape.fill.fore_color.rgb = fill_color
    shape.line.fill.background()
    return shape


def add_text(slide, text, left, top, width, height,
             font_size=18, bold=False, color=C_WHITE,
             align=PP_ALIGN.LEFT, wrap=True, italic=False):
    """Add a text box."""
    txBox = slide.shapes.add_textbox(
        Inches(left), Inches(top), Inches(width), Inches(height)
    )
    tf = txBox.text_frame
    tf.word_wrap = wrap
    p = tf.paragraphs[0]
    p.alignment = align
    run = p.add_run()
    run.text = text
    run.font.size = Pt(font_size)
    run.font.bold = bold
    run.font.italic = italic
    run.font.color.rgb = color
    return txBox


def add_multiline(slide, lines, left, top, width, height,
                  font_size=16, color=C_LIGHT, bold_first=False,
                  line_spacing_pt=6, indent=False):
    """Add multiple lines into a single text box."""
    txBox = slide.shapes.add_textbox(
        Inches(left), Inches(top), Inches(width), Inches(height)
    )
    tf = txBox.text_frame
    tf.word_wrap = True
    first = True
    for line in lines:
        if first:
            p = tf.paragraphs[0]
            first = False
        else:
            p = tf.add_paragraph()
        p.space_before = Pt(line_spacing_pt)
        run = p.add_run()
        run.text = line
        run.font.size = Pt(font_size)
        run.font.color.rgb = color
        if bold_first and lines.index(line) == 0:
            run.font.bold = True
    return txBox


def slide_header(slide, title, subtitle=None, accent_color=C_ACCENT):
    """Add a standard header bar with title."""
    add_rect(slide, 0, 0, 13.33, 1.15, accent_color)
    add_text(slide, title, 0.35, 0.18, 12.0, 0.75,
             font_size=28, bold=True, color=C_WHITE)
    if subtitle:
        add_text(slide, subtitle, 0.35, 0.82, 12.0, 0.4,
                 font_size=13, color=RGBColor(0xDD, 0xDD, 0xFF))


def add_bullet_box(slide, title, bullets, left, top, width, height,
                   accent=C_ACCENT):
    """Add a card with title and bullet list."""
    add_rect(slide, left, top, width, height, C_CARD)
    # left accent bar
    add_rect(slide, left, top, 0.06, height, accent)
    add_text(slide, title, left + 0.14, top + 0.1, width - 0.2, 0.4,
             font_size=14, bold=True, color=accent)
    bullet_lines = ["• " + b for b in bullets]
    add_multiline(slide, bullet_lines, left + 0.14, top + 0.5,
                  width - 0.2, height - 0.6, font_size=13, color=C_LIGHT)


def slide_number(slide, num, total=11):
    add_text(slide, f"{num} / {total}", 12.5, 7.1, 0.8, 0.35,
             font_size=10, color=C_MUTED, align=PP_ALIGN.RIGHT)


# ══════════════════════════════════════════════════════════════════════════
# SLIDE 1 — TITLE
# ══════════════════════════════════════════════════════════════════════════
sl = prs.slides.add_slide(BLANK)
add_bg(sl)
# gradient-ish accent block
add_rect(sl, 0, 0, 13.33, 3.2, C_ACCENT)
add_rect(sl, 0, 2.8, 13.33, 0.6, C_ACCENT2)

add_text(sl, "✈  FlightScope AI", 0.6, 0.55, 12.0, 1.1,
         font_size=42, bold=True, color=C_WHITE, align=PP_ALIGN.CENTER)
add_text(sl, "基于大模型的欧洲航空市场竞争分析与运力决策支持",
         0.6, 1.6, 12.0, 0.7,
         font_size=20, color=RGBColor(0xDD, 0xDD, 0xFF), align=PP_ALIGN.CENTER)
add_text(sl, "Wettbewerbsorientierte Marktanalyse mit LLMs  ·  RWTH Aachen  ·  SoSe 2026",
         0.6, 2.28, 12.0, 0.45,
         font_size=13, italic=True, color=RGBColor(0xCC, 0xCC, 0xFF), align=PP_ALIGN.CENTER)

add_rect(sl, 2.5, 3.7, 8.33, 0.05, C_ACCENT)
add_text(sl, "团队成员：[姓名1]  ·  [姓名2]  ·  [姓名3]",
         0.6, 3.85, 12.0, 0.5,
         font_size=16, color=C_LIGHT, align=PP_ALIGN.CENTER)
add_text(sl, "30. April 2026",
         0.6, 4.45, 12.0, 0.4,
         font_size=13, color=C_MUTED, align=PP_ALIGN.CENTER)
slide_number(sl, 1)

# ══════════════════════════════════════════════════════════════════════════
# SLIDE 2 — 问题与动机
# ══════════════════════════════════════════════════════════════════════════
sl = prs.slides.add_slide(BLANK)
add_bg(sl)
slide_header(sl, "问题与动机", "为什么航空市场需要 LLM 驱动的竞争分析？")

problems = [
    "航空公司竞争激烈，用户反馈数据海量且高度分散",
    "纯人工竞品分析效率低、主观性强、难以持续更新",
    "LLM 可以把大量非结构化评论转为可比较的结构化洞察",
    "运营决策还缺少「价格」与「需求/客流」一体化数据支撑",
    "目标：从【口碑对比】升级为【运力决策支持】工具",
]
for i, p in enumerate(problems):
    y = 1.35 + i * 1.0
    add_rect(sl, 0.5, y, 12.33, 0.78, C_CARD)
    add_rect(sl, 0.5, y, 0.08, 0.78, C_ACCENT if i % 2 == 0 else C_ACCENT2)
    add_text(sl, p, 0.75, y + 0.12, 11.8, 0.55, font_size=15, color=C_LIGHT)

slide_number(sl, 2)

# ══════════════════════════════════════════════════════════════════════════
# SLIDE 3 — 行业范围界定
# ══════════════════════════════════════════════════════════════════════════
sl = prs.slides.add_slide(BLANK)
add_bg(sl)
slide_header(sl, "行业范围界定", "研究边界：欧洲短途/中途客运航线")

add_bullet_box(sl, "全服务航司（Network Carrier）",
               ["Lufthansa（德国）", "Air France（法国）", "KLM（荷兰）"],
               0.4, 1.3, 3.9, 2.5, C_ORANGE)

add_bullet_box(sl, "低成本航司（Low-Cost Carrier）",
               ["Ryanair（爱尔兰）", "easyJet（英国）", "Wizz Air（匈牙利）"],
               4.5, 1.3, 3.9, 2.5, C_ACCENT2)

add_bullet_box(sl, "数据来源",
               ["Trustpilot / App Store 评论",
                "票价快照与价格趋势",
                "需求代理：搜索热度、预订代理、评论量",
                "OTP / 准点率公开数据"],
               8.6, 1.3, 4.3, 2.5, C_ACCENT)

add_rect(sl, 0.4, 4.05, 12.53, 0.05, C_ACCENT)
add_text(sl, "研究焦点 → 德语与英语用户视角下，全服务 vs 低成本的多维度竞争格局",
         0.4, 4.2, 12.53, 0.6,
         font_size=14, color=C_ACCENT2, bold=True)

slide_number(sl, 3)

# ══════════════════════════════════════════════════════════════════════════
# SLIDE 4 — 文献基础
# ══════════════════════════════════════════════════════════════════════════
sl = prs.slides.add_slide(BLANK)
add_bg(sl)
slide_header(sl, "文献基础", "三篇文献如何支撑本工具的方法链")

cols = [
    ("📖 Porter\nCompetitive Strategy",
     C_ORANGE,
     ["五力模型搭建市场竞争结构",
      "识别行业盈利压力来源",
      "→ 同业竞争强（价格/航线/时隙）",
      "→ 用户议价能力高（比价透明）",
      "→ 进入壁垒高（机队/时隙/监管）",
      "作用：确定【为什么这个市场值得分析】"]),
    ("📊 IPA + Kano\n(Review-based)",
     C_ACCENT2,
     ["区分基础项 / 绩效项 / 兴奋项",
      "→ 基础项：安全、准点、规则透明",
      "→ 绩效项：价格性价比、问题处理",
      "→ 兴奋项：智能改签、优质 App",
      "作用：确定【应该关注哪些维度】"]),
    ("🤖 LLM-Cure\n(Review Analysis)",
     C_ACCENT,
     ["LLM 从评论中抽取优劣势与证据句",
      "多竞争对手标准化评分",
      "可解释的竞争情报矩阵",
      "→ 方法直接迁移到航空场景",
      "作用：提供【如何自动化分析】的技术范式"]),
]

for i, (title, color, bullets) in enumerate(cols):
    x = 0.4 + i * 4.3
    add_rect(sl, x, 1.3, 4.1, 5.6, C_CARD)
    add_rect(sl, x, 1.3, 4.1, 0.08, color)
    add_text(sl, title, x + 0.15, 1.42, 3.8, 0.75,
             font_size=14, bold=True, color=color)
    add_multiline(sl, ["• " + b for b in bullets],
                  x + 0.15, 2.2, 3.8, 4.5,
                  font_size=12.5, color=C_LIGHT)

slide_number(sl, 4)

# ══════════════════════════════════════════════════════════════════════════
# SLIDE 5 — 分析维度
# ══════════════════════════════════════════════════════════════════════════
sl = prs.slides.add_slide(BLANK)
add_bg(sl)
slide_header(sl, "分析维度框架", "评论维度（LLM层）+ 决策维度（运力层）")

dims_left = [
    ("1", "准点率与可靠性",      "OTP、取消率、不正常航班处理"),
    ("2", "票价与收费透明度",    "价格清晰度、隐性费用、行李收费规则"),
    ("3", "客服与航变处理能力",  "响应速度、投诉解决率、IrrOps 服务"),
    ("4", "数字体验",            "App/Web 质量、自助服务、在线值机"),
    ("5", "乘机体验",            "登机流程、座位舒适、行李体验"),
    ("6", "退改签效率",          "退款速度、改签便利性、规则公平性"),
]
dims_right = [
    ("7", "航线-时段价格水平",   "票价时间序列、价格弹性、竞争对手定价"),
    ("8", "需求与客流指标",      "搜索热度、预订代理、评论量趋势、座位供给"),
]

for i, (num, name, desc) in enumerate(dims_left):
    y = 1.3 + i * 0.95
    add_rect(sl, 0.4, y, 6.2, 0.82, C_CARD)
    add_rect(sl, 0.4, y, 0.42, 0.82, C_ACCENT)
    add_text(sl, num, 0.4, y + 0.18, 0.42, 0.45,
             font_size=16, bold=True, color=C_WHITE, align=PP_ALIGN.CENTER)
    add_text(sl, name, 0.95, y + 0.06, 3.0, 0.38,
             font_size=13, bold=True, color=C_WHITE)
    add_text(sl, desc, 0.95, y + 0.42, 5.5, 0.38,
             font_size=11, color=C_MUTED)

add_text(sl, "↓ 扩展维度（运力决策层）", 6.9, 1.25, 6.0, 0.45,
         font_size=13, bold=True, color=C_ACCENT2)
for i, (num, name, desc) in enumerate(dims_right):
    y = 1.75 + i * 1.15
    add_rect(sl, 6.9, y, 6.0, 0.95, C_CARD)
    add_rect(sl, 6.9, y, 0.42, 0.95, C_ACCENT2)
    add_text(sl, num, 6.9, y + 0.22, 0.42, 0.45,
             font_size=16, bold=True, color=C_BG, align=PP_ALIGN.CENTER)
    add_text(sl, name, 7.44, y + 0.07, 3.5, 0.38,
             font_size=13, bold=True, color=C_ACCENT2)
    add_text(sl, desc, 7.44, y + 0.48, 5.3, 0.42,
             font_size=11, color=C_MUTED)

slide_number(sl, 5)

# ══════════════════════════════════════════════════════════════════════════
# SLIDE 6 — 工具方案 工作流
# ══════════════════════════════════════════════════════════════════════════
sl = prs.slides.add_slide(BLANK)
add_bg(sl)
slide_header(sl, "FlightScope AI — 工具方案", "端到端工作流")

steps = [
    ("① 输入",    C_ACCENT,  "航司 + 航线 + 时间 + 数据来源"),
    ("② 采集",    C_ACCENT2, "评论  ·  票价时间序列  ·  需求代理数据"),
    ("③ 分析",    C_ORANGE,  "LLM 文本洞察  +  Forecast / 规则引擎"),
    ("④ 可视化",  C_GREEN,   "雷达图  ·  排名  ·  趋势  ·  运力决策建议"),
]

for i, (label, color, desc) in enumerate(steps):
    x = 0.5 + i * 3.1
    add_rect(sl, x, 1.35, 2.85, 2.0, C_CARD)
    add_rect(sl, x, 1.35, 2.85, 0.08, color)
    add_text(sl, label, x + 0.15, 1.48, 2.55, 0.55,
             font_size=17, bold=True, color=color)
    add_text(sl, desc, x + 0.15, 2.1, 2.55, 0.95,
             font_size=13, color=C_LIGHT, wrap=True)
    if i < 3:
        add_text(sl, "→", x + 2.85, 1.9, 0.35, 0.5,
                 font_size=22, bold=True, color=C_MUTED, align=PP_ALIGN.CENTER)

# BYOK
add_rect(sl, 0.5, 3.65, 12.33, 2.85, C_CARD)
add_rect(sl, 0.5, 3.65, 0.08, 2.85, C_ACCENT)
add_text(sl, "🔑  软件架构（API 策略）", 0.75, 3.75, 12.0, 0.5,
         font_size=15, bold=True, color=C_ACCENT)

arch = [
    "BYOK（Bring Your Own Key）：用户在 UI 输入自己的 API Key（Google Gemini 或其他 OpenAI-compatible 模型）",
    "Fallback → OpenRouter：主通道不可用时自动切换 OpenRouter，保障演示稳定性",
    "Engine 无关性：同一分析管道，可替换模型后端  ·  连接测试按钮即时验证",
]
add_multiline(sl, ["• " + a for a in arch],
              0.75, 4.3, 12.0, 2.0, font_size=13, color=C_LIGHT)

slide_number(sl, 6)

# ══════════════════════════════════════════════════════════════════════════
# SLIDE 7 — UI 设计
# ══════════════════════════════════════════════════════════════════════════
sl = prs.slides.add_slide(BLANK)
add_bg(sl)
slide_header(sl, "UI 设计概览", "Sidebar + 控制区 + 5个结果 Tab")

# Sidebar mock
add_rect(sl, 0.4, 1.3, 2.6, 5.7, RGBColor(0x1A, 0x1D, 0x27))
add_rect(sl, 0.4, 1.3, 2.6, 0.08, C_ACCENT)
add_text(sl, "⚙  Sidebar", 0.55, 1.42, 2.3, 0.45,
         font_size=14, bold=True, color=C_ACCENT)
add_multiline(sl, [
    "🔑 API & Engine Settings",
    "  · Key 输入",
    "  · 模型通道选择",
    "  · Test Connection",
    "",
    "✈  航司选择 (4-8家)",
    "📍 航线选择",
    "📅 时间范围",
    "📦 数据来源",
    "",
    "▶  Run Analysis",
], 0.55, 1.95, 2.3, 4.8, font_size=11.5, color=C_LIGHT)

# Main area — control bar
add_rect(sl, 3.2, 1.3, 9.7, 0.7, RGBColor(0x22, 0x26, 0x3A))
add_text(sl, "主分析区  —  5 个结果 Tab", 3.4, 1.4, 9.3, 0.5,
         font_size=13, bold=True, color=C_WHITE)

tabs = [
    ("Overview",          C_ACCENT,  "KPI 卡片 + 雷达图"),
    ("Dimension Ranking", C_ACCENT2, "分维度排名 + 证据"),
    ("Head-to-Head",      C_ORANGE,  "两家航司深度对比"),
    ("Evidence",          C_YELLOW,  "原文证据句 + 问题模式"),
    ("Capacity Planner",  C_GREEN,   "Add/Hold/Reduce\n机型 + 时段建议"),
]
for i, (name, color, desc) in enumerate(tabs):
    x = 3.2 + i * 1.94
    add_rect(sl, x, 2.15, 1.88, 4.7, C_CARD)
    add_rect(sl, x, 2.15, 1.88, 0.08, color)
    add_text(sl, name, x + 0.1, 2.28, 1.68, 0.5,
             font_size=11.5, bold=True, color=color)
    add_text(sl, desc, x + 0.1, 2.85, 1.68, 3.8,
             font_size=11, color=C_LIGHT, wrap=True)

slide_number(sl, 7)

# ══════════════════════════════════════════════════════════════════════════
# SLIDE 8 — MVP 与价值
# ══════════════════════════════════════════════════════════════════════════
sl = prs.slides.add_slide(BLANK)
add_bg(sl)
slide_header(sl, "MVP 与业务价值", "最小可用版本 + 可行动决策输出")

add_text(sl, "MVP = 最小可用版本（Minimum Viable Product）", 0.5, 1.3, 12.5, 0.5,
         font_size=14, color=C_MUTED, italic=True)

mvp_features = [
    ("竞争分析层", C_ACCENT, [
        "4-8 家航司对比雷达图",
        "分维度证据化排名",
        "两家航司 Head-to-Head 深度对比",
        "关键主题时间趋势",
    ]),
    ("运力决策层", C_GREEN, [
        "航线级价格与需求监控（试点）",
        "首版规则建议：Add / Hold / Reduce Flight",
        "机型级别建议（小型 / 中型 / 大型窄体）",
        "推荐出发时段（高峰 / 次高峰 / 非高峰）",
    ]),
    ("业务价值", C_ACCENT2, [
        "更快、更客观的竞争洞察",
        "提前识别服务风险与差异化机会",
        "回答核心运营问题：",
        "  在时间点 t、航线 r 是否该加班次？",
        "  应上多大机型？哪个时段更优？",
    ]),
]

for i, (title, color, items) in enumerate(mvp_features):
    x = 0.4 + i * 4.3
    add_rect(sl, x, 1.9, 4.1, 5.3, C_CARD)
    add_rect(sl, x, 1.9, 4.1, 0.08, color)
    add_text(sl, title, x + 0.15, 2.03, 3.8, 0.5,
             font_size=14, bold=True, color=color)
    add_multiline(sl, ["• " + b for b in items],
                  x + 0.15, 2.6, 3.8, 4.4,
                  font_size=12.5, color=C_LIGHT)

slide_number(sl, 8)

# ══════════════════════════════════════════════════════════════════════════
# SLIDE 9 — Capacity Planner 逻辑
# ══════════════════════════════════════════════════════════════════════════
sl = prs.slides.add_slide(BLANK)
add_bg(sl)
slide_header(sl, "Capacity Planner — 决策逻辑", "Input → Rule Engine → Output")

# Input
add_rect(sl, 0.4, 1.35, 3.3, 5.6, C_CARD)
add_rect(sl, 0.4, 1.35, 0.08, 5.6, C_ORANGE)
add_text(sl, "📥  输入特征", 0.62, 1.48, 3.0, 0.45,
         font_size=13, bold=True, color=C_ORANGE)
add_multiline(sl, [
    "• 航线-时段价格与变化",
    "• 需求代理（搜索热度、",
    "  预订、评论量）",
    "• 供给侧（班次数、座位）",
    "• 竞争对手运力投放",
    "• 运行质量（OTP、取消率）",
    "• 日历因素（季节、节假日）",
], 0.62, 2.0, 3.0, 4.7, font_size=12.5, color=C_LIGHT)

# Arrow
add_text(sl, "→", 3.7, 3.8, 0.5, 0.6,
         font_size=26, bold=True, color=C_MUTED, align=PP_ALIGN.CENTER)

# Rule Engine
add_rect(sl, 4.2, 1.35, 4.5, 5.6, C_CARD)
add_rect(sl, 4.2, 1.35, 0.08, 5.6, C_ACCENT)
add_text(sl, "⚙  规则引擎（可解释）", 4.42, 1.48, 4.15, 0.45,
         font_size=13, bold=True, color=C_ACCENT)
add_multiline(sl, [
    "步骤1: Demand Pressure Score",
    "步骤2: Supply Gap Score",
    "步骤3: Profitability Proxy",
    "步骤4: 运行风险折减",
    "步骤5: Final Score → 决策",
    "",
    "逻辑：",
    "需求高 + 供给缺口正 + 低风险",
    "  → Add Flight ✓",
    "指标中性 → Hold",
    "需求弱 / 高风险 → Reduce",
], 4.42, 2.0, 4.2, 4.7, font_size=12, color=C_LIGHT)

# Arrow
add_text(sl, "→", 8.7, 3.8, 0.5, 0.6,
         font_size=26, bold=True, color=C_MUTED, align=PP_ALIGN.CENTER)

# Output
add_rect(sl, 9.2, 1.35, 3.73, 5.6, C_CARD)
add_rect(sl, 9.2, 1.35, 0.08, 5.6, C_GREEN)
add_text(sl, "📊  输出建议", 9.42, 1.48, 3.45, 0.45,
         font_size=13, bold=True, color=C_GREEN)
add_multiline(sl, [
    "• Add / Hold / Reduce",
    "",
    "机型建议：",
    "• 中等需求 →",
    "  小型窄体机",
    "• 高需求峰时 →",
    "  中/大型窄体机",
    "",
    "时段建议：",
    "• 峰时（需求强+OTP稳）",
    "• 非峰（价格弹性高）",
    "",
    "+ Top-3 依据 + 置信度",
], 9.42, 2.0, 3.35, 4.7, font_size=12, color=C_LIGHT)

slide_number(sl, 9)

# ══════════════════════════════════════════════════════════════════════════
# SLIDE 10 — 可行性分阶段
# ══════════════════════════════════════════════════════════════════════════
sl = prs.slides.add_slide(BLANK)
add_bg(sl)
slide_header(sl, "可行性 — 分阶段实现路径", "能做到吗？可以，分三个阶段。")

phases = [
    ("阶段 1\n课程可交付", C_ACCENT, [
        "✓ 评论 + 票价 + 需求代理数据集成",
        "✓ 规则化 Add/Hold/Reduce 建议",
        "✓ 机型 & 时段启发式规则",
        "✓ Streamlit 可点击 Demo",
        "⏱  本学期内交付",
    ]),
    ("阶段 2\n中期扩展", C_ACCENT2, [
        "→ 航线-时段级时间序列预测",
        "→ 历史数据回测验证",
        "→ 多数据源对齐与校准",
        "→ 自动化数据采集管道",
    ]),
    ("阶段 3\n产品化方向", C_GREEN, [
        "→ 网络级运力优化",
        "→ 机队与时隙约束建模",
        "→ 竞争对手反应情景分析",
        "→ 燃油成本 / 季节性参数化",
    ]),
]

for i, (title, color, items) in enumerate(phases):
    x = 0.5 + i * 4.2
    add_rect(sl, x, 1.35, 4.0, 5.5, C_CARD)
    add_rect(sl, x, 1.35, 0.08, 5.5, color)
    add_text(sl, title, x + 0.18, 1.48, 3.6, 0.7,
             font_size=16, bold=True, color=color)
    add_multiline(sl, items, x + 0.18, 2.3, 3.6, 4.3,
                  font_size=13, color=C_LIGHT)

slide_number(sl, 10)

# ══════════════════════════════════════════════════════════════════════════
# SLIDE 11 — 下一步计划
# ══════════════════════════════════════════════════════════════════════════
sl = prs.slides.add_slide(BLANK)
add_bg(sl)
slide_header(sl, "下一步计划", "行动项 → 下次演示前完成")

actions = [
    ("📌 范围确认",    "明确是否纳入机场维度，锁定 6-7 家目标航司"),
    ("📦 数据采集",    "收集 2 家航司 × 2 条航线的评论、票价、需求代理数据（试点）"),
    ("🧩 维度固化",    "最终确认 6+2 维度定义与 LLM 提示词模板"),
    ("⚙  规则实现",    "实现 Add/Hold/Reduce + 机型建议的规则逻辑"),
    ("🖥  Demo 交付",   "可点击 Streamlit Demo，覆盖 Overview + Capacity Planner"),
]

for i, (icon_title, desc) in enumerate(actions):
    y = 1.3 + i * 1.1
    add_rect(sl, 0.5, y, 12.33, 0.88, C_CARD)
    add_rect(sl, 0.5, y, 0.08, 0.88, C_ACCENT if i % 2 == 0 else C_ACCENT2)
    add_text(sl, icon_title, 0.75, y + 0.1, 2.5, 0.55,
             font_size=14, bold=True, color=C_ACCENT if i % 2 == 0 else C_ACCENT2)
    add_text(sl, desc, 3.35, y + 0.12, 9.3, 0.55, font_size=13.5, color=C_LIGHT)

add_rect(sl, 0.5, 6.85, 12.33, 0.05, C_ACCENT)
add_text(sl, "FlightScope AI  ·  RWTH Aachen  ·  SoSe 2026",
         0.5, 6.95, 12.33, 0.4,
         font_size=11, italic=True, color=C_MUTED, align=PP_ALIGN.CENTER)

slide_number(sl, 11)

# ── Save ───────────────────────────────────────────────────────────────────
out_path = r"c:\AAA_RWTH\Wettbewerbsorientierte Marktanalyse mit Large Language Models-FLUGE\FlightScope_AI_Praesentation.pptx"
prs.save(out_path)
print(f"Saved: {out_path}")
