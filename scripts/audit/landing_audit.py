#!/usr/bin/env python3
"""lhg-landing-page 确定性落地页审计：31 条规则，零第三方依赖。

扫描目标目录的页面文件（html/tsx/jsx/vue），围绕"转化"做确定性检查：
CTA（行动召唤）/ 信任（社会证明）/ 模板相（anti-slop）/ 响应式 /
可访问性 / SEO / 性能 / 诚实 / 区块完整性 / 文案。

输出 JSON 与人类可读报告；有 blocker 时以 exit code 2 退出
（供 hooks 与 CI 使用）。

用法：
    python3 landing_audit.py --target <目录> [--format json|text] [--fail-on blocker|warning|nit]

规则文案均为本项目原创（思路受 UI/UX Pro Max、impeccable、
Anthropic frontend-design 等开源项目启发，未复制任何第三方原文）。
"""

import argparse
import json
import os
import re
import sys

VERSION = "1.0.0"
TOOL = "lhg-landing-page/landing-audit"

SKIP_DIRS = {
    "node_modules", ".next", "dist", "build", ".git", "coverage",
    "__pycache__", "vendor", ".turbo", "out",
}
SCAN_EXTS = {".html", ".htm", ".tsx", ".jsx", ".vue", ".astro"}
TOKEN_FILE_RES = [re.compile(r"token", re.I), re.compile(r"theme", re.I),
                  re.compile(r"globals\.css$", re.I), re.compile(r"tailwind\.config", re.I)]

# CTA 关键词：可点击元素文案含其一即视为行动召唤
CTA_WORDS = [
    "免费", "试用", "立即", "开始", "预约", "报名", "下载", "购买",
    "订阅", "注册", "了解", "查看", "咨询", "开通", "加入", "体验",
    "预订", "下单", "领取",
    "start", "try", "sign", "demo", "download", "buy",
    "subscribe", "book", "contact", "join",
]
CTA_RE = re.compile("|".join(CTA_WORDS), re.I)
CLICKABLE_RE = re.compile(
    r"<button\b[^>]*>(.*?)</button>|<a\b[^>]*>(.*?)</a>|"
    r"<input\b[^>]*type=[\"']?(?:submit|button)[\"']?[^>]*>",
    re.I | re.S,
)


class Finding:
    __slots__ = ("rule_id", "severity", "category", "title", "file", "line", "snippet", "detail")

    def __init__(self, rule_id, severity, category, title, file, line, snippet, detail):
        self.rule_id = rule_id
        self.severity = severity
        self.category = category
        self.title = title
        self.file = file
        self.line = line
        self.snippet = snippet
        self.detail = detail

    def to_dict(self):
        return {
            "rule_id": self.rule_id, "severity": self.severity,
            "category": self.category, "title": self.title,
            "file": self.file, "line": self.line,
            "snippet": self.snippet, "detail": self.detail,
        }


def is_token_file(path):
    base = os.path.basename(path)
    return any(r.search(base) for r in TOKEN_FILE_RES)


def collect_files(target):
    out = []
    for root, dirs, files in os.walk(target):
        dirs[:] = [d for d in dirs if d not in SKIP_DIRS]
        for f in files:
            _, ext = os.path.splitext(f)
            if ext in SCAN_EXTS:
                out.append(os.path.join(root, f))
    return sorted(out)


def read_text(path):
    try:
        with open(path, "r", encoding="utf-8", errors="replace") as fh:
            return fh.read()
    except OSError:
        return ""


def strip_tags(s):
    return re.sub(r"<[^>]+>", "", s).strip()


def clickable_ctas(line):
    """返回该行里文案含 CTA 关键词的可点击元素文案列表。"""
    out = []
    for m in CLICKABLE_RE.finditer(line):
        text = strip_tags(m.group(1) or m.group(2) or "")
        if not text and m.group(0).lower().startswith("<input"):
            vm = re.search(r"value=[\"']([^\"']*)[\"']", m.group(0), re.I)
            text = vm.group(1) if vm else ""
        if text and CTA_RE.search(text):
            out.append(text[:40])
    return out


# ---------------------------------------------------------------- 规则定义

def _line_hits(rule_id, lines, text, path, ctx, pattern, flags=0):
    rule = _RULE_BY_ID[rule_id]
    rx = re.compile(pattern, flags)
    return [
        Finding(rule["id"], rule["severity"], rule["category"], rule["title"],
                path, i + 1, lines[i].strip()[:160], rule["detail"])
        for i, ln in enumerate(lines) if rx.search(ln)
    ]


RULES = []
_RULE_BY_ID = {}


def rule(rule_id, severity, category, title, detail):
    def deco(fn):
        r = {"id": rule_id, "severity": severity, "category": category,
             "title": title, "detail": detail}
        _RULE_BY_ID[rule_id] = r
        r["check"] = fn
        RULES.append(r)
        return fn
    return deco


# ---------------- CTA（行动召唤） ----------------

@rule("LP-CTA-001", "blocker", "CTA", "全页无行动召唤",
      "整个页面找不到一个带行动词的可点击按钮/链接。落地页的唯一目的就是让人行动，"
      "没有 CTA 等于没有落地页。至少在首屏放一个主 CTA。")
def r_cta_001(lines, text, path, ctx):
    for ln in lines:
        if clickable_ctas(ln):
            return []
    rule = _RULE_BY_ID["LP-CTA-001"]
    return [Finding(rule["id"], rule["severity"], rule["category"], rule["title"],
                    path, 1, "", rule["detail"])]


@rule("LP-CTA-002", "warning", "CTA", "首屏 CTA 过多",
      "首屏出现 3 个及以上行动按钮会稀释注意力，用户不知道该点哪个。"
      "首屏只保留 1 个主 CTA（视觉最突出），次 CTA 最多 1 个且弱化处理。")
def r_cta_002(lines, text, path, ctx):
    hits = []
    for i, ln in enumerate(lines[:80]):
        for cta in clickable_ctas(ln):
            hits.append((i + 1, cta))
    if len(hits) >= 3:
        rule = _RULE_BY_ID["LP-CTA-002"]
        return [Finding(rule["id"], rule["severity"], rule["category"], rule["title"],
                        path, hits[0][0],
                        "首屏发现 %d 个 CTA：%s" % (len(hits), " / ".join(h[1] for h in hits[:4])),
                        rule["detail"])]
    return []


@rule("LP-CTA-003", "warning", "CTA", "表单字段过多",
      "转化表单超过 3 个字段，每多一个字段转化率就掉一截。只留行动必需的字段，"
      "其余信息等用户进来后再收集。")
def r_cta_003(lines, text, path, ctx):
    rule = _RULE_BY_ID["LP-CTA-003"]
    out = []
    for m in re.finditer(r"<form\b[^>]*>(.*?)</form>", text, re.I | re.S):
        body = m.group(1)
        n = len(re.findall(r"<(?:input|select|textarea)\b", body, re.I))
        n -= len(re.findall(r"<input\b[^>]*type=[\"']?hidden", body, re.I))
        if n > 3:
            line_no = text[:m.start()].count("\n") + 1
            out.append(Finding(rule["id"], rule["severity"], rule["category"], rule["title"],
                               path, line_no, "表单含 %d 个可见字段" % n, rule["detail"]))
    return out


@rule("LP-CTA-004", "warning", "CTA", "死链 CTA",
      "href=\"#\" 或 javascript:; 的按钮点下去毫无反应，是转化漏斗里的黑洞。"
      "每个 CTA 都必须有真实去向（锚点、表单、外部链接）。")
def r_cta_004(lines, text, path, ctx):
    # 只拦截完全空的 href="#"；#xxx 是合法页内锚点
    return _line_hits("LP-CTA-004", lines, text, path, ctx,
                      r"<a\b[^>]*href=[\"']#[\"']|"
                      r"<a\b[^>]*href=[\"']javascript:(?:;|void\(0\));?[\"']", re.I)


@rule("LP-CTA-005", "nit", "CTA", "CTA 文案无力",
      "「点击」「提交」「确定」这类文案没有给出行动的理由。好文案=动词+利益，"
      "如「免费试用 14 天」「领取课程大纲」。")
def r_cta_005(lines, text, path, ctx):
    rule = _RULE_BY_ID["LP-CTA-005"]
    rx = re.compile(r"<(?:button|a)\b[^>]*>\s*(?:点击|提交|确定|click|submit|ok)\s*</(?:button|a)>", re.I)
    return [
        Finding(rule["id"], rule["severity"], rule["category"], rule["title"],
                path, i + 1, lines[i].strip()[:160], rule["detail"])
        for i, ln in enumerate(lines) if rx.search(ln)
    ]


# ---------------- 信任（社会证明） ----------------

@rule("LP-TRU-001", "warning", "信任", "缺少社会证明",
      "页面没有任何用户评价、客户案例、合作伙伴或媒体背书。陌生人凭什么信你？"
      "至少加一个：真实用户评价、客户 logo 墙、媒体报道、获奖/认证。")
def r_tru_001(lines, text, path, ctx):
    if re.search(r"用户评价|客户评价|testimonial|合作伙伴|成功案例|口碑|媒体报道|获奖|"
                 r"trusted by|客户墙|review", text, re.I):
        return []
    rule = _RULE_BY_ID["LP-TRU-001"]
    return [Finding(rule["id"], rule["severity"], rule["category"], rule["title"],
                    path, 1, "", rule["detail"])]


@rule("LP-TRU-002", "blocker", "信任", "可疑的数字声明",
      "「100万+用户」「99%好评率」这类数字没有真实来源就是编造，被较真用户抓到"
      "整个页面的信任直接归零。数字要么有出处，要么删掉，换成诚实表述。")
def r_tru_002(lines, text, path, ctx):
    return _line_hits("LP-TRU-002", lines, text, path, ctx,
                      r"\d+\s*万\s*\+?\s*(?:用户|客户|学员|下载|订阅)|"
                      r"\d+\s*%\s*(?:好评|满意|推荐|续费)", re.I)


@rule("LP-TRU-003", "warning", "信任", "虚假紧迫感",
      "「仅剩3个名额」「马上截止」——如果是真的限量没问题，如果是编出来催单，"
      "被识破后信任崩盘。紧迫感必须真实，否则删掉。")
def r_tru_003(lines, text, path, ctx):
    return _line_hits("LP-TRU-003", lines, text, path, ctx,
                      r"仅剩\s*\d+|最后\s*\d+\s*(?:个|名|天|小时)|马上截止|"
                      r"错过再等|限时\s*\d+\s*天", re.I)


@rule("LP-TRU-004", "warning", "信任", "无联系方式",
      "页面找不到电话、邮箱、微信或「联系我们」入口。用户有疑问时无处可问，"
      "等于主动关掉了高意向流量的后门。页脚至少留一个真实联系方式。")
def r_tru_004(lines, text, path, ctx):
    if re.search(r"电话|手机|邮箱|微信|联系我们|contact|tel:|mailto:", text, re.I):
        return []
    rule = _RULE_BY_ID["LP-TRU-004"]
    return [Finding(rule["id"], rule["severity"], rule["category"], rule["title"],
                    path, 1, "", rule["detail"])]


# ---------------- 模板相（anti-slop） ----------------

@rule("LP-SLP-001", "blocker", "模板相", "紫粉渐变",
      "紫→粉渐变配深色背景是 AI 生成落地页最泛滥的配色，用户一眼可辨。"
      "渐变只用在小面积点缀，且必须取自品牌色系。")
def r_slp_001(lines, text, path, ctx):
    hits = _line_hits("LP-SLP-001", lines, text, path, ctx,
                      r"from-(purple|violet|fuchsia|pink)-\d|via-(purple|violet|fuchsia|pink)-\d|"
                      r"to-(purple|violet|fuchsia|pink)-\d")
    hits += _line_hits("LP-SLP-001", lines, text, path, ctx,
                       r"linear-gradient\([^)]*#(?:a855f7|8b5cf6|d946ef|ec4899|c084fc|e879f9|a78bfa)", re.I)
    return hits


@rule("LP-SLP-002", "blocker", "模板相", "lorem ipsum 残留",
      "Lorem ipsum 是「文案还没写」的墓碑，出现在发布版页面等于告诉用户这是半成品。"
      "没有真实文案就用诚实占位（「文案待补充」），不许留拉丁文。")
def r_slp_002(lines, text, path, ctx):
    return _line_hits("LP-SLP-002", lines, text, path, ctx, r"lorem ipsum", re.I)


@rule("LP-SLP-003", "warning", "模板相", "硬编码色值",
      "组件里直接写十六进制色值，换主题时要全文搜索替换。颜色必须走设计令牌"
      "（CSS 变量或主题配置），令牌定义文件本身除外。")
def r_slp_003(lines, text, path, ctx):
    if is_token_file(path):
        return []
    return _line_hits("LP-SLP-003", lines, text, path, ctx,
                      r"#(?:[0-9a-fA-F]{6}|[0-9a-fA-F]{3})\b")


@rule("LP-SLP-004", "nit", "模板相", "渐变标题字",
      "大标题用彩虹渐变字是 AI 模板味重灾区，且可读性差。标题用纯色，"
      "强调靠字重和字号对比。")
def r_slp_004(lines, text, path, ctx):
    rule = _RULE_BY_ID["LP-SLP-004"]
    return [
        Finding(rule["id"], rule["severity"], rule["category"], rule["title"],
                path, i + 1, lines[i].strip()[:160], rule["detail"])
        for i, ln in enumerate(lines)
        if "bg-clip-text" in ln and "gradient" in ln
    ]


@rule("LP-SLP-005", "warning", "模板相", "emoji 泛滥",
      "单行出现 6 个以上 emoji 是典型的 AI 生成痕迹。emoji 是调料不是主菜，"
      "一屏最多点缀 1-2 个。")
def r_slp_005(lines, text, path, ctx):
    rule = _RULE_BY_ID["LP-SLP-005"]
    rx = re.compile(r"[\U0001F300-\U0001FAFF\u2600-\u27BF\u2B00-\u2BFF]")
    return [
        Finding(rule["id"], rule["severity"], rule["category"], rule["title"],
                path, i + 1, lines[i].strip()[:80], rule["detail"])
        for i, ln in enumerate(lines) if len(rx.findall(ln)) >= 6
    ]


# ---------------- 响应式 ----------------

@rule("LP-RSP-001", "warning", "响应式", "固定大宽度",
      "w-[900px] 以上的固定宽度在手机上直接撑破布局。用 max-w-* + 响应式断点代替，"
      "让容器随屏幕收缩。")
def r_rsp_001(lines, text, path, ctx):
    rule = _RULE_BY_ID["LP-RSP-001"]
    out = []
    for i, ln in enumerate(lines):
        for m in re.finditer(r"w-\[(\d+)px\]", ln):
            if int(m.group(1)) >= 900:
                out.append(Finding(rule["id"], rule["severity"], rule["category"], rule["title"],
                                   path, i + 1, ln.strip()[:160], rule["detail"]))
    return out


@rule("LP-RSP-002", "warning", "响应式", "min-width 溢出风险",
      "min-width 写死 400px 以上的值，手机端（390px 宽）必定出现横向滚动条。"
      "横向滚动是移动端体验杀手，改用 min() 或响应式断点。")
def r_rsp_002(lines, text, path, ctx):
    rule = _RULE_BY_ID["LP-RSP-002"]
    out = []
    for i, ln in enumerate(lines):
        for m in re.finditer(r"min-width\s*:\s*(\d+)px", ln, re.I):
            if int(m.group(1)) >= 400:
                out.append(Finding(rule["id"], rule["severity"], rule["category"], rule["title"],
                                   path, i + 1, ln.strip()[:160], rule["detail"]))
    return out


# ---------------- 可访问性 ----------------

def _img_tags(text):
    """返回 (tag, line_no) 列表；标签可能跨多行，逐行检查会漏判。"""
    out = []
    for m in re.finditer(r"<img\b[^>]*>", text, re.I | re.S):
        line_no = text[:m.start()].count("\n") + 1
        out.append((m.group(0), line_no))
    return out


@rule("LP-A11Y-001", "warning", "可访问性", "图片缺 alt",
      "img 没有 alt 属性：读屏用户完全不知道这是什么图，SEO 也丢分。"
      "装饰图 alt 留空（alt=\"\"），内容图写清描述。")
def r_a11y_001(lines, text, path, ctx):
    rule = _RULE_BY_ID["LP-A11Y-001"]
    return [
        Finding(rule["id"], rule["severity"], rule["category"], rule["title"],
                path, ln, tag.replace("\n", " ")[:160], rule["detail"])
        for tag, ln in _img_tags(text)
        if not re.search(r"\balt=", tag, re.I)
    ]


@rule("LP-A11Y-002", "nit", "可访问性", "表单控件无标签",
      "input 没有 label、aria-label 或 placeholder，用户（尤其读屏用户）不知道要填什么。"
      "每个输入框配一个可见 label。")
def r_a11y_002(lines, text, path, ctx):
    rule = _RULE_BY_ID["LP-A11Y-002"]
    out = []
    for i, ln in enumerate(lines):
        for m in re.finditer(r"<input\b[^>]*>", ln, re.I):
            tag = m.group(0)
            if re.search(r"type=[\"']?(?:hidden|submit|button|checkbox|radio|range)", tag, re.I):
                continue
            if not re.search(r"aria-label=|placeholder=|<label", tag + ln, re.I):
                out.append(Finding(rule["id"], rule["severity"], rule["category"], rule["title"],
                                   path, i + 1, tag[:120], rule["detail"]))
    return out


# ---------------- SEO ----------------

@rule("LP-SEO-001", "warning", "SEO", "缺少 title",
      "页面没有 <title>，搜索结果和浏览器标签页都显示空白/URL。"
      "标题格式建议：产品名 + 核心价值，一句话讲清。")
def r_seo_001(lines, text, path, ctx):
    if re.search(r"<title>[^<]+</title>", text, re.I):
        return []
    rule = _RULE_BY_ID["LP-SEO-001"]
    return [Finding(rule["id"], rule["severity"], rule["category"], rule["title"],
                    path, 1, "", rule["detail"])]


@rule("LP-SEO-002", "warning", "SEO", "缺少 meta description",
      "没有 description，搜索引擎只能随机抓取正文做摘要，点击率吃亏。"
      "写 60-150 字，包含核心关键词和行动召唤。")
def r_seo_002(lines, text, path, ctx):
    if re.search(r"<meta\b[^>]*name=[\"']description[\"']", text, re.I):
        return []
    rule = _RULE_BY_ID["LP-SEO-002"]
    return [Finding(rule["id"], rule["severity"], rule["category"], rule["title"],
                    path, 1, "", rule["detail"])]


@rule("LP-SEO-003", "warning", "SEO", "多个 h1",
      "一个页面只能有一个 h1（页面的主题句）。多个 h1 让搜索引擎和读屏软件"
      "分不清重点，其余标题降级为 h2。")
def r_seo_003(lines, text, path, ctx):
    n = len(re.findall(r"<h1\b", text, re.I))
    if n > 1:
        rule = _RULE_BY_ID["LP-SEO-003"]
        return [Finding(rule["id"], rule["severity"], rule["category"], rule["title"],
                        path, 1, "发现 %d 个 <h1>" % n, rule["detail"])]
    return []


@rule("LP-SEO-004", "warning", "SEO", "h1 缺失或过长",
      "没有 h1 等于没有主题句；h1 超过 40 字则重点淹没在废话里。"
      "h1 一句话讲清「这是什么、给谁、有什么用」。")
def r_seo_004(lines, text, path, ctx):
    rule = _RULE_BY_ID["LP-SEO-004"]
    hs = re.findall(r"<h1\b[^>]*>(.*?)</h1>", text, re.I | re.S)
    if not hs:
        return [Finding(rule["id"], rule["severity"], rule["category"], rule["title"],
                        path, 1, "未找到 <h1>", rule["detail"])]
    out = []
    for h in hs:
        t = strip_tags(h)
        if len(t) > 40:
            line_no = text.find(h)
            out.append(Finding(rule["id"], rule["severity"], rule["category"], rule["title"],
                               path, text[:line_no].count("\n") + 1,
                               "h1 长 %d 字：%s…" % (len(t), t[:40]), rule["detail"]))
    return out


@rule("LP-SEO-005", "nit", "SEO", "无语义化标签",
      "全页都是 div，搜索引擎和读屏软件看不到页面结构。"
      "至少用上 header / main / section / footer。")
def r_seo_005(lines, text, path, ctx):
    if re.search(r"<(?:header|main|section|article|nav|footer)\b", text, re.I):
        return []
    rule = _RULE_BY_ID["LP-SEO-005"]
    return [Finding(rule["id"], rule["severity"], rule["category"], rule["title"],
                    path, 1, "", rule["detail"])]


# ---------------- 性能 ----------------

@rule("LP-PERF-001", "nit", "性能", "图片未懒加载",
      "首屏外的图片不加 loading=\"lazy\"，首屏加载时间白白增加。"
      "首屏大图保持 eager，其余全部 lazy。")
def r_perf_001(lines, text, path, ctx):
    rule = _RULE_BY_ID["LP-PERF-001"]
    return [
        Finding(rule["id"], rule["severity"], rule["category"], rule["title"],
                path, ln, tag.replace("\n", " ")[:160], rule["detail"])
        for tag, ln in _img_tags(text)
        if not re.search(r"\bloading=", tag, re.I)
    ]


@rule("LP-PERF-002", "nit", "性能", "无响应式图片",
      "img 没有 srcset，手机用户被迫下载桌面端大图，流量和速度双输。"
      "至少提供 1x / 2x 两档，或用 picture 做断点切换。")
def r_perf_002(lines, text, path, ctx):
    rule = _RULE_BY_ID["LP-PERF-002"]
    return [
        Finding(rule["id"], rule["severity"], rule["category"], rule["title"],
                path, ln, tag.replace("\n", " ")[:160], rule["detail"])
        for tag, ln in _img_tags(text)
        if not re.search(r"\bsrcset=", tag, re.I)
    ]


# ---------------- 诚实 ----------------

@rule("LP-HON-001", "warning", "诚实", "TODO/待补充残留",
      "TODO、FIXME、「待补充」出现在发布版页面，等于把半成品端给用户看。"
      "发布前全文搜索一遍，要么补上真实内容，要么删掉该区块。")
def r_hon_001(lines, text, path, ctx):
    return _line_hits("LP-HON-001", lines, text, path, ctx,
                      r"TODO|FIXME|待补充|TBD")


# ---------------- 区块完整性 ----------------

@rule("LP-SEC-001", "nit", "区块", "缺少 FAQ",
      "没有常见问题区，用户最后的疑虑无处打消。FAQ 是转化漏斗的最后一道保险，"
      "把销售/客服被问得最多的问题列 4-8 条。")
def r_sec_001(lines, text, path, ctx):
    if re.search(r"常见问题|FAQ|问答", text, re.I):
        return []
    rule = _RULE_BY_ID["LP-SEC-001"]
    return [Finding(rule["id"], rule["severity"], rule["category"], rule["title"],
                    path, 1, "", rule["detail"])]


@rule("LP-SEC-002", "nit", "区块", "缺少定价",
      "页面只谈价值不谈价格，用户要带着疑问去别处找答案——很可能一去不回。"
      "即使价格未定，也放一个「价格待定 / 联系获取报价」区块。")
def r_sec_002(lines, text, path, ctx):
    if re.search(r"定价|价格|套餐|pricing|收费|报价", text, re.I):
        return []
    rule = _RULE_BY_ID["LP-SEC-002"]
    return [Finding(rule["id"], rule["severity"], rule["category"], rule["title"],
                    path, 1, "", rule["detail"])]


@rule("LP-SEC-003", "nit", "区块", "缺少页脚",
      "没有 footer，版权、备案、联系方式、次级导航无处安放，页面像没写完。"
      "页脚是信任的最后一块拼图。")
def r_sec_003(lines, text, path, ctx):
    if re.search(r"<footer\b", text, re.I):
        return []
    rule = _RULE_BY_ID["LP-SEC-003"]
    return [Finding(rule["id"], rule["severity"], rule["category"], rule["title"],
                    path, 1, "", rule["detail"])]


# ---------------- 导航 ----------------

@rule("LP-NAV-001", "nit", "导航", "页眉无 CTA",
      "用户滚动页面时，页眉是唯一常驻的行动入口。页眉没有 CTA 等于浪费了"
      "全页曝光最高的位置。页眉右侧固定放一个主 CTA。")
def r_nav_001(lines, text, path, ctx):
    m = re.search(r"<header\b[^>]*>(.*?)</header>", text, re.I | re.S)
    if not m:
        rule = _RULE_BY_ID["LP-NAV-001"]
        return [Finding(rule["id"], rule["severity"], rule["category"], rule["title"],
                        path, 1, "未找到语义化 <header>", rule["detail"])]
    if CTA_RE.search(strip_tags(m.group(0))):
        return []
    # header 内可点击元素文案是否含 CTA 词
    for ln in m.group(0).split("\n"):
        if clickable_ctas(ln):
            return []
    rule = _RULE_BY_ID["LP-NAV-001"]
    line_no = text[:m.start()].count("\n") + 1
    return [Finding(rule["id"], rule["severity"], rule["category"], rule["title"],
                    path, line_no, "", rule["detail"])]


# ---------------- 文案 ----------------

@rule("LP-CPY-001", "warning", "文案", "首屏标题空洞",
      "「欢迎来到我们的网站」这类标题没有传递任何价值信息，用户 3 秒内"
      "不知道这是干什么的就会关掉。标题必须回答：这是什么、给谁、有什么用。")
def r_cpy_001(lines, text, path, ctx):
    return _line_hits("LP-CPY-001", "\n".join(lines[:60]).split("\n"), text, path, ctx,
                      r"欢迎来到|欢迎使用本|我们致力于为您")


# ---------------------------------------------------------------- 运行器

def run(target):
    files = collect_files(target)
    findings = []
    for path in files:
        text = read_text(path)
        if not text.strip():
            continue
        lines = text.split("\n")
        rel = os.path.relpath(path, target)
        ctx = {"is_token_file": is_token_file(path)}
        for r in RULES:
            try:
                for f in r["check"](lines, text, path, ctx) or []:
                    f.file = rel
                    findings.append(f)
            except Exception:
                continue  # 单条规则异常不影响整体
    return files, findings


def main(argv=None):
    ap = argparse.ArgumentParser(description="lhg-landing-page 确定性落地页审计")
    ap.add_argument("--target", default=".", help="扫描目录")
    ap.add_argument("--format", choices=["json", "text"], default="text")
    ap.add_argument("--fail-on", choices=["blocker", "warning", "nit"], default="blocker")
    args = ap.parse_args(argv)

    target = os.path.abspath(args.target)
    if not os.path.isdir(target):
        print("target 不是目录：%s" % args.target, file=sys.stderr)
        return 1

    files, findings = run(target)
    sev_rank = {"blocker": 3, "warning": 2, "nit": 1}
    counts = {"blocker": 0, "warning": 0, "nit": 0}
    for f in findings:
        counts[f.severity] = counts.get(f.severity, 0) + 1

    result = {
        "tool": TOOL,
        "version": VERSION,
        "target": args.target,
        "summary": {
            "files_scanned": len(files),
            "rules_run": len(RULES),
            "blocker": counts["blocker"],
            "warning": counts["warning"],
            "nit": counts["nit"],
        },
        "findings": [f.to_dict() for f in sorted(
            findings, key=lambda x: (-sev_rank.get(x.severity, 0), x.file, x.line))],
    }

    if args.format == "json":
        print(json.dumps(result, ensure_ascii=False, indent=2))
    else:
        s = result["summary"]
        print("落地页审计：扫描 %d 文件，运行 %d 条规则" % (s["files_scanned"], s["rules_run"]))
        print("blocker=%d warning=%d nit=%d" % (s["blocker"], s["warning"], s["nit"]))
        for f in result["findings"]:
            print("[%s][%s] %s:%d %s" % (
                f["severity"].upper(), f["rule_id"], f["file"], f["line"], f["title"]))
            print("    %s" % f["detail"])
            if f["snippet"]:
                print("    → %s" % f["snippet"])

    level = sev_rank[args.fail_on]
    bad = any(sev_rank.get(f.severity, 0) >= level for f in findings)
    return 2 if bad else 0


if __name__ == "__main__":
    sys.exit(main())
