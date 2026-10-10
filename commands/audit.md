---
description: 落地页转化体检：跑确定性审计脚本 + 人工评审清单，输出分级报告并自动修复 blocker。
argument-hint: [页面目录] [--fix]
---

# /lhg-landing-page:audit —— 落地页转化体检

用户输入在 `$ARGUMENTS` 中：`[页面目录] [--fix]`。目录缺省为当前项目根目录。

## 流程（加载 lhg-lp-audit 全程指导）

### 1. 跑脚本
```bash
python3 ${CLAUDE_PLUGIN_ROOT}/scripts/audit/landing_audit.py --target <目录> --format text
```
记下 blocker / warning / nit 的数量与明细（含文件、行号、规则说明）。

### 2. 分级与修复
- blocker：逐条修。`--fix` 缺省即自动修（最小改动原则）；修一条用脚本复查一条。
- 修不掉的（如需用户提供真实文案/图片）→ 列入"需人工处理"，不许为清零改规则。
- warning：修掉或写豁免理由（+有效期）；nit：顺手修。

### 3. 人工评审（lhg-lp-audit 第 5 节）
脚本抓不到的，人工过一遍：
- 首屏 3 秒测试：遮住 logo，3 秒内能说出"这是干什么的、给谁的"吗
- 视觉层级：CTA 是不是全页最显眼的元素
- 移动端实测：390px 下首屏完整、无横向滚动、按钮可点
- 表单实测：从填到提交走一遍，报错信息是否友好
- 文案真实性：每个数字、每条评价都能找到出处吗

### 4. 输出报告
按 `lhg-lp-audit` 第 6 节模板输出自查报告，存为 `docs/audit-YYYYMMDD.md`，
结论写清"通过 / 不通过"。

## 硬规则
- 有 blocker 就说"通过" → 不许。
- 为清零改脚本规则或阈值 → 这是作弊，不许。
