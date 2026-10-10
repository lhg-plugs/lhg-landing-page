# 灵感来源与致谢（Attribution）

本插件的**方法论灵感**来自以下优秀的开源项目，**所有实现代码、检测规则与文案均为原创**，
未复制任何第三方的原文案与代码。

| 项目 | 作者 / 组织 | 许可 | 链接 | 借鉴了什么思路 |
|---|---|---|---|---|
| ui-ux-pro-max-skill（UI/UX Pro Max） | Next Level Builder | MIT | https://github.com/nextlevelbuilder/ui-ux-pro-max-skill | "先定设计系统再写代码"的方法论：产品→风格→配色→字体→落地页模式→推理规则的决策链；交付前 checklist 的问题意识。本插件 `lhg-lp-design` 的设计语言流程受其启发，**文案全部原创** |
| impeccable | Paul Bakaus（Renaissance Geek） | Apache-2.0 | https://github.com/pbakaus/impeccable | "确定性检测规则 + 设计令牌沉淀"的架构思想；本插件审计脚本的规则引擎模式受其启发，**规则条目全部自研** |
| skills（官方技能库） | Anthropic | Apache-2.0 | https://github.com/anthropics/skills | `frontend-design` 的"从产品自身世界取材、避开 AI 模板相"等设计指导思想；本插件 anti-slop 规则的问题意识受其启发，**规则文案全部原创** |

## 声明

1. **借鉴思路，实现与文案均为原创**：以上项目的具体文案、规则原文、代码实现均未被复制。
   本插件的 skill 方法论文案、审计规则、命令流程均为独立撰写。
2. **许可合规**：上述项目均为 MIT / Apache-2.0 许可，允许在保留声明的前提下进行思路借鉴与二次创作。
   本文件即为保留声明的一部分。
3. **商标与归属**：各项目名称与作者署名归其各自所有者所有。

## 本插件自身的许可

本插件原创部分采用 MIT 许可（见 `LICENSE` 文件），版权所有：刘洪光（https://github.com/lhg-skills）。
