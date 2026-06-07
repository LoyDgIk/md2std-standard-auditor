# md2std Standard Auditor

`md2std-standard-auditor` 是独立的中文标准 Markdown 审校器。它不生成 Word，不替代 `md2std` 排版生成器，只在转换前检查 `md2std` Markdown 是否违反 Skill 中已有的基础校验规则。

## 当前校验范围

- 禁止旧交叉引用语法 `{@...}`。
- 禁止在标题、表题、图题、公式中手写生成编号。
- 禁止 LaTeX `\tag{...}`。
- 校验 `{{tbl:...}}`、`{{fig:...}}`、`{{eq:...}}`、`{{std:...}}` 语法。
- 校验表、图、公式锚点类型和 ID 格式。
- 校验表、图、公式锚点重复和未知引用。
- 校验 `{{std:...}}` 是否能在“规范性引用文件”章中找到对应标准号。
- 检查 `# 范围` 是否存在并位于首个一级章。
- 检查附录、参考文献、索引的基本顺序。
- 检查附录中是否错误设置“范围”“规范性引用文件”“术语和定义”等章。
- 检查规范性引用文件章是否错误分条、使用列表符号、缺少固定导语或与“无引用”说明冲突。
- 检查参考文献是否使用 `[1]`、`[2]` 形式连续编号。
- 检查表题后是否紧跟表格，以及表格是否缺少 `{表：#tbl:id}` 表题。
- 检查块级公式是否缺少 `#eq:id` 锚点。
- 提醒列项细分疑似超过两个层次。
- 提醒缺少 YAML front matter。

这些规则来自 `md2std-standard-skill` 的现有 validation checklist。更完整的 GB/T 1.1-2020 语义审校可以在后续版本继续扩展。

## 使用

开发安装：

```powershell
python -m pip install -e .
```

直接运行模块：

```powershell
python -X utf8 -m md2std_standard_auditor input.md
```

安装后使用命令：

```powershell
md2std-audit input.md
```

默认只在 `error` 级别返回非零退出码。如需让 warning 也失败：

```powershell
md2std-audit input.md --fail-level warning
```

输出 JSON：

```powershell
md2std-audit input.md --format json
```

## 与 md2std 的边界

- `md2std`：Markdown -> Word 排版生成器。
- `md2std-standard-auditor`：Markdown -> 审校报告。
- `md2std-standard-skill`：面向 Codex 的规则说明和调用包装。
