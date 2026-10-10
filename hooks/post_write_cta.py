#!/usr/bin/env python3
"""lhg-landing-page 硬门②（警告级，不拦截）：写完落地页文件后提醒做转化自查。

触发：PostToolUse / Write|Edit。只对页面文件（html/tsx/jsx/vue/astro）
做一次性提醒，永远 exit 0、不拦截写入。

逃生方式：LHG_LP_HOOKS_OFF=1（环境变量）可关闭本提醒；
或 /plugin disable lhg-landing-page 停用整个插件。
零第三方依赖。
"""

import json
import os
import sys

PAGE_EXTS = {".html", ".htm", ".tsx", ".jsx", ".vue", ".astro"}


def main() -> int:
    if os.environ.get("LHG_LP_HOOKS_OFF") == "1":
        return 0

    try:
        raw = sys.stdin.read()
        payload = json.loads(raw) if raw.strip() else {}
    except Exception:
        return 0

    tool_input = payload.get("tool_input", {}) or {}
    file_path = tool_input.get("file_path", "") or ""
    if not file_path:
        return 0

    _, ext = os.path.splitext(file_path)
    if ext not in PAGE_EXTS:
        return 0

    msg = (
        "转化提醒（lhg-landing-page）：%s 是页面文件，写完后建议做一次转化自查：\n"
        "1) 首屏 CTA 是否唯一突出、文案是否为「动词+利益」；\n"
        "2) 跑 python3 ${CLAUDE_PLUGIN_ROOT}/scripts/audit/landing_audit.py --target <页面目录>；\n"
        "3) 或直接 /lhg-landing-page:audit（含人工评审清单）。\n"
        "关闭本提醒：export LHG_LP_HOOKS_OFF=1（当前会话有效）。"
    ) % file_path
    out = {
        "hookSpecificOutput": {
            "hookEventName": "PostToolUse",
            "additionalContext": msg,
        }
    }
    sys.stdout.write(json.dumps(out, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    sys.exit(main())
