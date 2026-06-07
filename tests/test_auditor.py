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

GB/T 11615  地热资源地质勘查规范

# 术语和定义

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
        self.assertIn("REFERENCE_ITEM_UNNUMBERED", codes)
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
