# -*- coding: utf-8 -*-

from __future__ import annotations

import json
import os
import subprocess
import sys
import tempfile
import unittest

from md2std_standard_auditor import audit_text


VALID_DOC = """---
standard_type: 团体标准
title: 测试标准
---
# 范围

本文件规定了测试要求。

# 规范性引用文件

下列文件中的内容通过文中的规范性引用而构成本文件必不可少的条款。其中，注日期的引用文件，仅该日期对应的版本适用于本文件；不注日期的引用文件，其最新版本（包括所有的修改单）适用于本文件。

{{std:GB/T 11615}} GB/T 11615  地热资源地质勘查规范

# 术语和定义

下列术语和定义适用于本文件。

## 地热温泉  geothermal hot spring

定义内容。

# 要求

见{{tbl:classify:label}}，并符合{{std:GB/T 11615}}的规定。

{表：#tbl:classify} 温泉利用分类

| 类别 | 要求 |
| --- | --- |
| 洗浴 | 合格 |

![流程图 {#fig:flow}](images/flow.png)

按{{eq:depth:label}}计算：

$$H = T_r + h$${#eq:depth}
"""


class AuditorTest(unittest.TestCase):
    def codes(self, text: str) -> set[str]:
        return {issue.code for issue in audit_text(text).issues}

    def test_valid_document_has_no_issues(self):
        self.assertEqual([], audit_text(VALID_DOC).issues)

    def test_normative_reference_registration_supports_aliases_and_foreign_years(self):
        text = """---
title: 测试
---
# 范围

符合{{std:GB/T 1.1}}、{{std:JIS S 6006}}、{{std:ISO 3160-2}}和{{std:EN 71—3:2019}}。

# 规范性引用文件

{{std:GB/T 1.1—2020}} GB/T 1.1—2020  标准化工作导则

{{std:JIS S 6006:2007}} JIS S 6006:2007  铅笔、彩色铅笔及其笔芯

{{std:ISO 3160-2:2015}} ISO 3160-2:2015  表壳体及其附件 金合金覆盖层 第2部分:纯度、厚度、耐腐蚀性能和附着力的测试

{{std:EN 71—3}} EN 71—3:2019  玩具安全 第3部分:特定元素的迁移
"""
        codes = self.codes(text)
        self.assertNotIn("INVALID_STANDARD_REFERENCE", codes)
        self.assertNotIn("UNKNOWN_STANDARD_REFERENCE", codes)

    def test_implicit_normative_reference_registration_warns_but_matches(self):
        text = """---
title: 测试
---
# 范围

符合{{std:GB/T 11615}}。

# 规范性引用文件

GB/T 11615  地热资源地质勘查规范
"""
        issues = audit_text(text).issues
        codes = {issue.code for issue in issues}
        self.assertIn("NORMATIVE_REFERENCE_IMPLICIT_REGISTRATION", codes)
        self.assertNotIn("UNKNOWN_STANDARD_REFERENCE", codes)

    def test_current_md2std_standard_markdown_contract_is_accepted(self):
        text = """---
title: 测试
---
# 范围

见{{fig:subparts:label}}和{{tbl:sample:label}}。

# 术语和定义

下列术语和定义适用于本文件。

{术语：地热温泉 | geothermal hot spring}

定义内容。

[来源：GB/T 11615—2010，3.1，有修改]

# 要求

{无标题条:3} 这是无标题条正文。

{表：#tbl:sample} 表题

| 类型 | 内圆直径〔脚注〕 |
| --- | --- |
| A | 100〔注：普通注内容。〕 |

{单位} 单位为毫米

{脚注} 表脚注的内容。

{来源} 资料来自试验记录。

{图：#fig:subparts} 组合图

{单位} 单位为毫米

{分图组:2}

![第一张分图](images/a.png)

![第二张分图](images/b.png)

{图标引} 第一项说明。

{图段} 段（可包含要求型条款）〔注：图内注内容。〕

{脚注} 图脚注内容。

{来源} 资料来自图样设计文件。

示例：

第一段示例内容。

{示例结束}
"""
        self.assertEqual([], audit_text(text).issues)

    def test_rejects_legacy_refs_manual_numbers_and_formula_tags(self):
        text = """# 4.2 手写标题

按式（{@eq:a}）计算。

{表：#tbl:bad} 表1 手写表号

| A |
| --- |
| 1 |

$$x=1\\tag{1}$${#eq:x}
"""
        codes = self.codes(text)
        self.assertIn("MISSING_FRONT_MATTER", codes)
        self.assertIn("MANUAL_HEADING_NUMBER", codes)
        self.assertIn("LEGACY_REFERENCE", codes)
        self.assertIn("MANUAL_TABLE_NUMBER", codes)
        self.assertIn("FORMULA_TAG", codes)

    def test_rejects_removed_md2std_markers_and_orphan_addons(self):
        text = """---
title: 测试
---
# 范围

{单位} 孤立单位。

{注：旧式正文注。}

{表注：旧表注。}

{图标引1：旧标引。}

{图段：旧图段。}

{分图：missing.png | 旧分图。}

{示例结束}

{无标题条:9} 层级错误。

{表：#tbl:sample} 表题

| 类型 | 内圆直径{脚注a} |
| --- | --- |
| A | 100 |

{单位} 单位为毫米。

{单位} 单位为厘米。

{图标引} 类型不匹配。
"""
        codes = self.codes(text)
        self.assertIn("ADDON_WITHOUT_TARGET", codes)
        self.assertIn("BRACED_NOTE", codes)
        self.assertIn("REMOVED_MD2STD_MARKER", codes)
        self.assertIn("EXAMPLE_END_WITHOUT_START", codes)
        self.assertIn("INVALID_UNTITLED_CLAUSE", codes)
        self.assertIn("OLD_TABLE_CELL_FOOTNOTE_REF", codes)
        self.assertIn("DUPLICATE_ADDON", codes)
        self.assertIn("FIGURE_ADDON_WITHOUT_FIGURE", codes)

    def test_rejects_untitled_clause_in_foundational_sections(self):
        cases = {
            "范围": "# 范围\n\n{无标题条:2} 本文件规定了测试要求。\n",
            "规范性引用文件": "# 规范性引用文件\n\n{无标题条:2} GB/T 1.1  标准化工作导则\n",
            "术语和定义": "# 术语和定义\n\n{无标题条:2} 测试术语。\n",
            "符号和缩略语": "# 符号和缩略语\n\n{无标题条:2} A 为面积。\n",
        }
        for chapter, text in cases.items():
            with self.subTest(chapter=chapter):
                issues = audit_text(text).issues
                self.assertIn("UNTITLED_CLAUSE_IN_FOUNDATIONAL_SECTION", {issue.code for issue in issues})

    def test_checks_normative_reference_default_lead_infos(self):
        missing_lead = """---
title: 测试
---
# 规范性引用文件

{{std:GB/T 11615}} GB/T 11615  地热资源地质勘查规范
"""
        empty = """---
title: 测试
---
# 规范性引用文件
"""
        conflict = """---
title: 测试
---
# 规范性引用文件

本文件没有规范性引用文件。

{{std:GB/T 11615}} GB/T 11615  地热资源地质勘查规范
"""

        missing_issues = audit_text(missing_lead).issues
        self.assertIn("NORMATIVE_REFERENCES_DEFAULT_LEAD_INFO", {issue.code for issue in missing_issues})
        self.assertEqual(
            "info",
            next(issue.severity for issue in missing_issues
                 if issue.code == "NORMATIVE_REFERENCES_DEFAULT_LEAD_INFO"),
        )
        self.assertIn("NORMATIVE_REFERENCES_NONE_INFO", self.codes(empty))

        conflict_codes = self.codes(conflict)
        self.assertIn("NORMATIVE_REFERENCES_CONFLICT", conflict_codes)
        self.assertNotIn("NORMATIVE_REFERENCES_DEFAULT_LEAD_INFO", conflict_codes)

    def test_checks_terms_fixed_lead(self):
        generated_lead = """---
title: 测试
---
# 术语和定义

## 地热温泉  geothermal hot spring

定义内容。
"""
        conflict = """---
title: 测试
---
# 术语和定义

本文件没有需要界定的术语和定义。

{术语：地热温泉 | geothermal hot spring}

定义内容。
"""
        empty = """---
title: 测试
---
# 术语和定义
"""
        lead_without_terms = """---
title: 测试
---
# 术语和定义

下列术语和定义适用于本文件。
"""
        imported_only = """---
title: 测试
---
# 术语和定义

GB/T 11615界定的术语和定义适用于本文件。
"""

        self.assertNotIn("TERMS_LEAD_MISSING", self.codes(generated_lead))
        self.assertIn("TERMS_DEFAULT_LEAD_INFO", self.codes(generated_lead))
        self.assertIn("TERMS_SECTION_CONFLICT", self.codes(conflict))
        self.assertNotIn("TERMS_SECTION_EMPTY", self.codes(empty))
        self.assertIn("TERMS_LEAD_WITHOUT_TERMS", self.codes(lead_without_terms))
        self.assertNotIn("TERMS_SECTION_EMPTY", self.codes(imported_only))

    def test_checks_symbols_fixed_lead(self):
        generated_lead = """---
title: 测试
---
# 符号和缩略语

A —— 面积。
"""
        empty = """---
title: 测试
---
# 符号和缩略语

下列符号适用于本文件。
"""
        valid = """---
title: 测试
---
# 符号和缩略语

下列符号和缩略语适用于本文件。

A —— 面积。
"""

        self.assertNotIn("SYMBOLS_LEAD_MISSING", self.codes(generated_lead))
        self.assertIn("SYMBOLS_SECTION_EMPTY", self.codes(empty))
        self.assertNotIn("SYMBOLS_LEAD_MISSING", self.codes(valid))

    def test_checks_manual_drafting_basis_text(self):
        abbreviated = "本文件按照 GB/T 1.1—2020 起草。"
        expected = "本文件按照GB/T 1.1—2020《标准化工作导则　第1部分：标准化文件的结构和起草规则》的规定起草。"

        self.assertIn("PREFACE_DRAFTING_BASIS_TEXT", self.codes(abbreviated))
        self.assertNotIn("PREFACE_DRAFTING_BASIS_TEXT", self.codes(expected))

    def test_validates_unknown_refs_duplicate_anchors_and_std_refs(self):
        text = """---
title: 测试
---
# 范围

见{{fig:missing}}，符合{{std:GB/T 1.1}}。

![图1 流程 {#fig:flow}](a.png)

![另一个图 {#fig:flow}](b.png)
"""
        codes = self.codes(text)
        self.assertIn("UNKNOWN_REFERENCE", codes)
        self.assertIn("UNKNOWN_STANDARD_REFERENCE", codes)
        self.assertIn("MANUAL_FIGURE_NUMBER", codes)
        self.assertIn("DUPLICATE_ANCHOR", codes)

    def test_rejects_wrong_anchor_types_and_broken_refs(self):
        text = """---
title: 测试
---
# 范围

{{tbl:bad

{表：#fig:wrong} 错误表锚点

| A |
| --- |
| 1 |

![缺少锚点](a.png)

$$x=1$${#x}
"""
        codes = self.codes(text)
        self.assertIn("BROKEN_REFERENCE_BRACES", codes)
        self.assertIn("WRONG_ANCHOR_TYPE", codes)
        self.assertIn("FIGURE_MISSING_ANCHOR", codes)
        self.assertIn("UNTYPED_ANCHOR", codes)

    def test_checks_structure_normative_refs_references_and_appendices(self):
        text = """---
title: 测试
---
# 要求

正文。

# 规范性引用文件

## 不应分条

- GB/T 1.1  标准化工作导则

本文件没有规范性引用文件。

# 附录 资料性 附录标题

## 范围

附录正文。

# 要求补充

正文。

# 参考文献

GB/T 1.1—2020 标准化工作导则

# 索引

## B

- 标准：1

# 后置内容
"""
        codes = self.codes(text)
        self.assertIn("SCOPE_NOT_FIRST_CHAPTER", codes)
        self.assertIn("NORMATIVE_REFERENCES_HAS_CLAUSE", codes)
        self.assertIn("NORMATIVE_REFERENCES_LIST_MARKER", codes)
        self.assertIn("NORMATIVE_REFERENCES_CONFLICT", codes)
        self.assertIn("APPENDIX_FORBIDDEN_SECTION", codes)
        self.assertIn("TECHNICAL_CHAPTER_AFTER_APPENDIX", codes)
        self.assertIn("GBT_1_1_IN_REFERENCES", codes)
        self.assertIn("CONTENT_AFTER_INDEX", codes)

    def test_checks_table_adjacency_formula_anchor_and_list_depth(self):
        text = """---
title: 测试
---
# 范围

{表：#tbl:orphan} 孤立表题

这里不是表格。

| 无题表 |
| --- |
| 内容 |

$$x=1$$

- 一级
      - 三级缩进
"""
        codes = self.codes(text)
        self.assertIn("TABLE_CAPTION_WITHOUT_TABLE", codes)
        self.assertIn("TABLE_MISSING_CAPTION", codes)
        self.assertIn("FORMULA_MISSING_ANCHOR", codes)
        self.assertIn("LIST_NESTING_TOO_DEEP", codes)

    def test_flags_standard_year_separator_and_normative_ref_order(self):
        text = """---
title: 测试
---
# 范围

本文件按照 GB/T 1.1-2020 起草。

# 规范性引用文件

下列文件中的内容通过文中的规范性引用而构成本文件必不可少的条款。其中，注日期的引用文件，仅该日期对应的版本适用于本文件；不注日期的引用文件，其最新版本（包括所有的修改单）适用于本文件。

{{std:DZ/T 0481}} DZ/T 0481  水热型地热资源回灌技术要求

{{std:GB/T 11615}} GB/T 11615  地热资源地质勘查规范
"""
        codes = self.codes(text)
        self.assertIn("STANDARD_YEAR_SEPARATOR", codes)
        self.assertIn("NORMATIVE_REFERENCES_ORDER", codes)

    def test_flags_ai_review_candidates_that_are_mechanically_visible(self):
        text = """---
title: 测试
---
# 范围

注：该说明应改写为陈述。

# 附录 资料性 估算方法

估算结果宜用于方案比选，不宜单独作为安全边界。

# 参考文献

[1] GB/T 1.1—2020  标准化工作导则 第1部分：标准化文件的结构和起草规则

# 索引

## X

- 允许开采量：3.1
"""
        codes = self.codes(text)
        self.assertIn("NOTE_MODAL_VERB", codes)
        self.assertIn("INFORMATIVE_APPENDIX_MODAL_VERB", codes)
        self.assertIn("GBT_1_1_IN_REFERENCES", codes)
        self.assertIn("MANUAL_REFERENCE_NUMBER", codes)
        self.assertIn("INDEX_ITEM_GROUP_MISMATCH", codes)

    def test_cli_json_output(self):
        fd, path = tempfile.mkstemp(suffix=".md")
        os.close(fd)
        try:
            with open(path, "w", encoding="utf-8") as f:
                f.write(VALID_DOC)
            proc = subprocess.run(
                [sys.executable, "-m", "md2std_standard_auditor", path, "--format", "json"],
                check=False,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                encoding="utf-8",
            )
            self.assertEqual(0, proc.returncode, proc.stderr)
            payload = json.loads(proc.stdout)
            self.assertTrue(payload["ok"])
            self.assertEqual([], payload["issues"])
        finally:
            if os.path.exists(path):
                os.remove(path)


if __name__ == "__main__":
    unittest.main()
