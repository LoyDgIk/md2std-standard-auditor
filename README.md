# md2std 标准机械审校器

`md2std-standard-auditor` 用于在生成 Word 前检查中文标准 Markdown。它只做确定性、可重复的机械审校，不生成 Word，也不替代人工技术审查。

本项目配合以下工具使用：

- 生成器：[MdToStandardWord](https://github.com/LoyDgIk/MdToStandardWord)
- 标准编写工作流技能：[standard-workflow-skills](https://github.com/LoyDgIk/standard-workflow-skills)

## 校验范围

审校器目前覆盖以下问题：

- 旧交叉引用语法 `{@...}`。
- 标题、表题、图题、公式中手写自动编号。
- LaTeX `\tag{...}` 手写公式编号。
- `{{tbl:...}}`、`{{fig:...}}`、`{{eq:...}}`、`{{std:...}}` 引用语法。
- 表、图、公式锚点类型、ID 格式、重复锚点和未知引用。
- `{{std:...}}` 与“规范性引用文件”章条目的匹配关系。
- 当前 md2std Markdown 契约：显式术语块、无标题条、组合图题、图表通用附加项、图标引、图段、分图组、表内注和表内脚注引用。
- 已移除的旧式图表附加项和旧分图语法。
- 图表通用附加项是否紧跟合法表格或图片目标，以及 `{单位}`、`{来源}` 是否重复。
- `# 范围` 是否存在并位于首个一级章。
- 附录、参考文献、索引的基本顺序。
- 附录中是否错误设置“范围”“规范性引用文件”“术语和定义”等章。
- 规范性引用文件章是否错误分条、使用列表符号、缺少固定导语或与“无引用”说明冲突。
- 规范性引用文件清单顺序是否疑似违反标准类型和编号排序规则。
- 参考文献条目是否手写 `[1]`、`[2]` 等方括号序号。
- 标准编号年份连接号是否疑似误用 `-` 或 `–`；标准编号应使用 `—`，例如 `GB/T 1.1—2020`。
- 参考文献中是否机械列入 GB/T 1.1。
- 资料性附录、条文注、图中的注、表中的注等位置是否疑似出现要求、推荐或禁止类能愿动词。
- 索引字母分组顺序，以及索引项是否疑似归入错误拼音首字母分组。
- 表题后是否紧跟表格，表格是否缺少 `{表：#tbl:id}` 表题。
- 块级公式是否缺少 `#eq:id` 锚点。
- 列项细分是否疑似超过两个层次。
- YAML front matter 是否缺失。

审校器只报告可以通过规则稳定识别的问题。范围表述、技术指标依据、术语定义质量、安全合规等内容，应在标准审校工作流中继续复核。

## 安装

开发安装：

```powershell
python -m pip install -e .
```

## 使用

直接运行模块：

```powershell
python -X utf8 -m md2std_standard_auditor input.md
```

安装后使用命令行入口：

```powershell
md2std-audit input.md
```

默认只在 `error` 级别返回非零退出码。如需让 `warning` 也返回非零退出码：

```powershell
md2std-audit input.md --fail-level warning
```

输出 JSON：

```powershell
md2std-audit input.md --format json
```

## 输出级别

| 级别 | 含义 |
| --- | --- |
| `error` | 明确违反 md2std 输入契约，通常应在生成 Word 前修复。 |
| `warning` | 疑似违反 GB/T 1.1 或项目规则，需要复核。 |
| `info` | 提示性信息。 |

## 项目边界

| 项目 | 职责 |
| --- | --- |
| `MdToStandardWord` / `md2std` | Markdown 到 DOCX 的排版生成。 |
| `md2std-standard-auditor` | Markdown 机械审校，输出结构化问题清单。 |
| `standard-workflow-skills/standard-audit-workflow` | 调用机械审校器，并组织机械规则覆盖不到的清单审查。 |
| `standard-workflow-skills/standard-drafting-workflow` | 组织资料检索、标准编写、审校修订和交付。 |
| `standard-workflow-skills/md2std-standard` | 说明生成器输入契约并提供生成调用脚本。 |
