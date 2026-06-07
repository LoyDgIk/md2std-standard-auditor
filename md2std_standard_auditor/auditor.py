# -*- coding: utf-8 -*-
"""Core Markdown audit rules migrated from the md2std standard skill checklist."""

from __future__ import annotations

from dataclasses import dataclass
import re
from pathlib import Path
from typing import Iterable


SEVERITY_ORDER = {"info": 0, "warning": 1, "error": 2}


@dataclass(frozen=True)
class Issue:
    code: str
    severity: str
    line: int
    message: str
    hint: str = ""


@dataclass(frozen=True)
class AuditResult:
    source: str
    issues: list[Issue]

    @property
    def ok(self) -> bool:
        return not any(issue.severity == "error" for issue in self.issues)

    def has_issues_at_or_above(self, level: str) -> bool:
        threshold = SEVERITY_ORDER[level]
        return any(SEVERITY_ORDER[issue.severity] >= threshold for issue in self.issues)


_FRONT_MATTER_RE = re.compile(r"^\ufeff?---\s*\n.*?\n---\s*\n?", re.S)
_HEADING_RE = re.compile(r"^(#{1,6})\s+(.+?)\s*$")
_MANUAL_HEADING_NUMBER_RE = re.compile(
    r"^(?:\d+(?:\.\d+)*|[A-Z]\.\d+(?:\.\d+)*)\s+\S"
)
_MANUAL_APPENDIX_HEADING_RE = re.compile(r"^附录\s*[A-ZＡ-Ｚ](?:\s|[（(]|$)")
_LEGACY_REF_RE = re.compile(r"\{@[^}]+\}")
_REF_RE = re.compile(r"\{\{([^{}]+)\}\}")
_ANY_REF_BRACE_RE = re.compile(r"\{\{|\}\}")
_ANCHOR_RE = re.compile(r"\{#([^}\s]+)\}")
_ANCHOR_ID_RE = re.compile(r"^[A-Za-z][A-Za-z0-9_.-]*$")
_TABLE_CAPTION_RE = re.compile(r"^\s*\{\s*表\s*[:：]\s*#([^}\s]+)\s*\}\s+(.+?)\s*$")
_TABLE_CAPTION_MARKER_RE = re.compile(r"^\s*(?:\{\s*)?表\s*[:：]")
_IMAGE_RE = re.compile(r"!\[([^\]]*)\]\(([^)]*)\)")
_INLINE_DISPLAY_FORMULA_RE = re.compile(r"\$\$(.+?)\$\$\s*(?:\{#([^}]+)\})?")
_FORMULA_TAG_RE = re.compile(r"\\tag\s*\{?")
_VISIBLE_TABLE_LABEL_RE = re.compile(r"^表\s*(?:[A-ZＡ-Ｚ]\s*[.．]\s*)?\d+(?:[.．]\d+)?(?:\s|　|$)")
_VISIBLE_FIGURE_LABEL_RE = re.compile(r"^图\s*(?:[A-ZＡ-Ｚ]\s*[.．]\s*)?\d+(?:[.．]\d+)?(?:\s|　|$)")
_NORMATIVE_REF_RE = re.compile(r"^\s*([A-Z][A-Z/]*\s+\d[\w.\-—–]*)(?:\s{2,}|　+)(.+)$")
_LIST_ITEM_RE = re.compile(r"^(\s*)(?:[-+*]|\d+[.)])\s+")
_REFERENCE_ITEM_RE = re.compile(r"^\s*[\[［]\d+[\]］]")

_NORMATIVE_REF_LEAD = (
    "下列文件中的内容通过文中的规范性引用而构成本文件必不可少的条款。"
    "其中，注日期的引用文件，仅该日期对应的版本适用于本文件；"
    "不注日期的引用文件，其最新版本"
)
_NORMATIVE_REF_NONE = "本文件没有规范性引用文件"
_FORBIDDEN_APPENDIX_HEADINGS = {"范围", "规范性引用文件", "术语和定义"}

_ALLOWED_REF_TYPES = {"tbl", "fig", "eq", "std"}
_ALLOWED_REF_MODES = {"num", "label", "full"}


def audit_file(path: str | Path) -> AuditResult:
    file_path = Path(path)
    text = file_path.read_text(encoding="utf-8")
    return audit_text(text, source=str(file_path))


def audit_text(text: str, source: str = "<string>") -> AuditResult:
    auditor = _Auditor(text)
    return AuditResult(source=source, issues=auditor.run())


class _Auditor:
    def __init__(self, text: str):
        self.text = text
        self.lines = text.splitlines()
        self.issues: list[Issue] = []
        self.anchors: dict[tuple[str, str], int] = {}
        self.normative_refs: set[str] = set()
        self.heading_entries: list[tuple[int, int, str]] = []

    def run(self) -> list[Issue]:
        self._check_front_matter()
        self._collect_headings()
        self._collect_normative_refs()
        self._check_document_structure()
        self._check_normative_reference_section()
        self._check_reference_section()
        self._scan_lines()
        self._scan_references()
        self.issues.sort(key=lambda issue: (issue.line, SEVERITY_ORDER[issue.severity], issue.code))
        return self.issues

    def _issue(self, code: str, severity: str, line: int, message: str, hint: str = ""):
        self.issues.append(Issue(code, severity, max(line, 1), message, hint))

    def _check_front_matter(self):
        if not _FRONT_MATTER_RE.match(self.text):
            self._issue(
                "MISSING_FRONT_MATTER",
                "warning",
                1,
                "缺少 YAML front matter；封面和前言元数据应集中写在文档顶部。",
                "在文档开头添加 `---` 包围的 YAML 元数据块。",
            )

    def _collect_normative_refs(self):
        in_normrefs = False
        for line_no, line in enumerate(self.lines, start=1):
            heading = _HEADING_RE.match(line)
            if heading and len(heading.group(1)) == 1:
                in_normrefs = heading.group(2).strip() == "规范性引用文件"
                continue
            if not in_normrefs:
                continue
            match = _NORMATIVE_REF_RE.match(self._strip_list_marker(line))
            if match:
                self.normative_refs.add(match.group(1).strip())

    def _collect_headings(self):
        for line_no, line in enumerate(self.lines, start=1):
            match = _HEADING_RE.match(line)
            if not match:
                continue
            self.heading_entries.append((line_no, len(match.group(1)), match.group(2).strip()))

    def _check_document_structure(self):
        top_headings = [(line, title) for line, level, title in self.heading_entries if level == 1]
        if not any(title == "范围" for _, title in top_headings):
            self._issue(
                "MISSING_SCOPE_CHAPTER",
                "warning",
                1,
                "未找到一级章 `# 范围`。",
                "完整标准文件通常应以 `# 范围` 作为第 1 章。",
            )
        if top_headings and top_headings[0][1] != "范围":
            self._issue(
                "SCOPE_NOT_FIRST_CHAPTER",
                "warning",
                top_headings[0][0],
                "第一个一级章不是 `范围`。",
                "完整标准文件中 `范围` 应设置为第 1 章。",
            )

        appendix_started = False
        references_seen = False
        index_seen = False
        for line_no, level, title in self.heading_entries:
            if index_seen and level == 1:
                self._issue(
                    "CONTENT_AFTER_INDEX",
                    "error",
                    line_no,
                    "`索引` 应作为文件的最后一个要素。",
                    "将该内容移到索引之前，或删除索引后的额外标题。",
                )
                continue
            if level == 1 and title == "索引":
                index_seen = True
                continue
            if level == 1 and title == "参考文献":
                references_seen = True
                continue
            if level == 1 and self._is_appendix_heading(title):
                appendix_started = True
                if references_seen:
                    self._issue(
                        "APPENDIX_AFTER_REFERENCES",
                        "error",
                        line_no,
                        "附录出现在参考文献之后。",
                        "附录应位于正文之后、参考文献之前。",
                    )
                continue
            if appendix_started:
                if level == 1:
                    self._issue(
                        "TECHNICAL_CHAPTER_AFTER_APPENDIX",
                        "error",
                        line_no,
                        "附录之后又出现了正文技术章：%s。" % title,
                        "附录之后只应继续其他附录、参考文献或索引。",
                    )
                elif title in _FORBIDDEN_APPENDIX_HEADINGS:
                    self._issue(
                        "APPENDIX_FORBIDDEN_SECTION",
                        "error",
                        line_no,
                        "附录中不应设置 `%s`。" % title,
                        "GB/T 1.1-2020 规定附录中不准许设置范围、规范性引用文件、术语和定义等内容。",
                    )

    def _check_normative_reference_section(self):
        section = self._section_lines("规范性引用文件")
        if not section:
            return
        non_empty = [(line_no, line.strip()) for line_no, line in section if line.strip()]
        has_none_text = any(_NORMATIVE_REF_NONE in line for _, line in non_empty)
        has_entries = any(_NORMATIVE_REF_RE.match(self._strip_list_marker(line)) for _, line in non_empty)
        has_lead = any(_NORMATIVE_REF_LEAD in line for _, line in non_empty)

        if has_entries and not has_lead:
            self._issue(
                "NORMATIVE_REFERENCES_LEAD_MISSING",
                "warning",
                non_empty[0][0] if non_empty else 1,
                "规范性引用文件章有清单条目，但缺少 GB/T 1.1-2020 固定导语。",
                "在清单前加入“下列文件中的内容通过文中的规范性引用而构成本文件必不可少的条款……”导语。",
            )
        if not has_entries and not has_none_text:
            self._issue(
                "NORMATIVE_REFERENCES_EMPTY",
                "warning",
                non_empty[0][0] if non_empty else self._heading_line("规范性引用文件"),
                "规范性引用文件章既没有清单条目，也没有“本文件没有规范性引用文件。”说明。",
                "补充引用文件清单，或写明“本文件没有规范性引用文件。”。",
            )
        if has_entries and has_none_text:
            self._issue(
                "NORMATIVE_REFERENCES_CONFLICT",
                "error",
                non_empty[0][0],
                "规范性引用文件章同时包含“无引用”说明和引用文件清单。",
                "二者只能保留一种。",
            )

        for line_no, line in section:
            stripped = line.strip()
            if not stripped:
                continue
            if _HEADING_RE.match(line):
                self._issue(
                    "NORMATIVE_REFERENCES_HAS_CLAUSE",
                    "error",
                    line_no,
                    "规范性引用文件章不应分条。",
                    "删除该章下的子标题，把引用文件作为段落清单列出。",
                )
                continue
            if _LIST_ITEM_RE.match(line):
                self._issue(
                    "NORMATIVE_REFERENCES_LIST_MARKER",
                    "error",
                    line_no,
                    "规范性引用文件清单不应使用列表符号或序号。",
                    "每个引用文件应作为独立段落，且不加序号。",
                )

    def _check_reference_section(self):
        section = self._section_lines("参考文献")
        if not section:
            return
        expected = 1
        for line_no, line in section:
            stripped = line.strip()
            if not stripped or _HEADING_RE.match(line):
                continue
            match = _REFERENCE_ITEM_RE.match(stripped)
            if not match:
                self._issue(
                    "REFERENCE_ITEM_UNNUMBERED",
                    "warning",
                    line_no,
                    "参考文献条目未使用方括号序号。",
                    "参考文献宜写成 `[1] GB/T 1.1—2020 ...`。",
                )
                continue
            number_text = re.search(r"\d+", match.group(0))
            if number_text and int(number_text.group(0)) != expected:
                self._issue(
                    "REFERENCE_ITEM_ORDER",
                    "warning",
                    line_no,
                    "参考文献序号不是连续顺序，期望 [%d]。" % expected,
                    "按出现顺序从 `[1]` 开始连续编号。",
                )
            expected += 1

    def _scan_lines(self):
        for line_no, line in enumerate(self.lines, start=1):
            self._check_heading(line_no, line)
            self._check_table_caption(line_no, line)
            self._check_table_without_caption(line_no, line)
            self._check_images(line_no, line)
            self._check_formulas(line_no, line)
            self._check_list_nesting(line_no, line)
            self._check_untyped_anchors(line_no, line)
            if _LEGACY_REF_RE.search(line):
                self._issue(
                    "LEGACY_REFERENCE",
                    "error",
                    line_no,
                    "旧交叉引用语法 `{@...}` 已废弃。",
                    "改用 `{{tbl:id}}`、`{{fig:id}}`、`{{eq:id}}` 或 `{{std:标准号}}`。",
                )

    def _check_heading(self, line_no: int, line: str):
        match = _HEADING_RE.match(line)
        if not match:
            return
        title = match.group(2).strip()
        if _MANUAL_HEADING_NUMBER_RE.match(title):
            self._issue(
                "MANUAL_HEADING_NUMBER",
                "error",
                line_no,
                "标题中疑似手写了章条编号。",
                "删除可见编号，只保留标题文本，让 md2std/Word 样式自动编号。",
            )
        if _MANUAL_APPENDIX_HEADING_RE.match(title):
            self._issue(
                "MANUAL_APPENDIX_NUMBER",
                "error",
                line_no,
                "附录标题中疑似手写了附录字母编号。",
                "写成 `# 附录 规范性 附录标题` 或 `# 附录 资料性 附录标题`。",
            )

    def _check_table_caption(self, line_no: int, line: str):
        match = _TABLE_CAPTION_RE.match(line)
        if not match:
            if _TABLE_CAPTION_MARKER_RE.match(line):
                self._issue(
                    "INVALID_TABLE_CAPTION",
                    "error",
                    line_no,
                    "表题标记格式不符合 md2std 契约。",
                    "表题应写成 `{表：#tbl:id} 标题`，标题中不要写表号。",
                )
            return
        local_id = self._parse_typed_anchor(match.group(1), "tbl", "表题", line_no)
        if local_id:
            self._add_anchor("tbl", local_id, line_no)
        next_line = self._next_non_empty_line(line_no)
        if next_line is None or not self._is_table_start(next_line[1]):
            self._issue(
                "TABLE_CAPTION_WITHOUT_TABLE",
                "error",
                line_no,
                "表题后没有紧跟表格。",
                "将 GFM 表格或 `<table>` 放在表题标记之后。",
            )
        title = match.group(2).strip()
        if _VISIBLE_TABLE_LABEL_RE.match(title):
            self._issue(
                "MANUAL_TABLE_NUMBER",
                "error",
                line_no,
                "表题中疑似手写了表号。",
                "表题只写纯标题，例如 `{表：#tbl:demo} 测试结果`。",
            )

    def _check_table_without_caption(self, line_no: int, line: str):
        if not self._is_table_start(line):
            return
        previous = self._previous_non_empty_line(line_no)
        if previous is not None and self._is_table_start(previous[1]):
            return
        if previous is None or not _TABLE_CAPTION_RE.match(previous[1]):
            self._issue(
                "TABLE_MISSING_CAPTION",
                "warning",
                line_no,
                "发现未带 `{表：#tbl:id}` 表题的表格。",
                "在表格前添加 `{表：#tbl:id} 表题`，让 md2std 自动生成表号。",
            )

    def _check_images(self, line_no: int, line: str):
        for match in _IMAGE_RE.finditer(line):
            alt = match.group(1).strip()
            anchors = list(_ANCHOR_RE.finditer(alt))
            if not anchors:
                self._issue(
                    "FIGURE_MISSING_ANCHOR",
                    "warning",
                    line_no,
                    "图片缺少 `#fig:id` 类型化锚点。",
                    "在 alt 文本中添加锚点，例如 `![流程图 {#fig:flow}](images/flow.png)`。",
                )
            for anchor in anchors:
                local_id = self._parse_typed_anchor(anchor.group(1), "fig", "图题", line_no)
                if local_id:
                    self._add_anchor("fig", local_id, line_no)
            title = _ANCHOR_RE.sub("", alt).strip()
            if _VISIBLE_FIGURE_LABEL_RE.match(title):
                self._issue(
                    "MANUAL_FIGURE_NUMBER",
                    "error",
                    line_no,
                    "图题中疑似手写了图号。",
                    "图题只写纯标题，例如 `![流程图 {#fig:flow}](images/flow.png)`。",
                )

    def _check_formulas(self, line_no: int, line: str):
        if _FORMULA_TAG_RE.search(line):
            self._issue(
                "FORMULA_TAG",
                "error",
                line_no,
                "公式中不应使用 LaTeX `\\tag{...}` 手写编号。",
                "删除 `\\tag`，使用 `$$...$${#eq:id}` 锚点并让 md2std 自动编号。",
            )
        stripped = line.strip()
        if stripped.startswith("$$") and stripped.endswith("$$") and "{#" not in stripped:
            self._issue(
                "FORMULA_MISSING_ANCHOR",
                "warning",
                line_no,
                "块级公式缺少 `#eq:id` 类型化锚点。",
                "写成 `$$...$${#eq:id}`，便于公式编号和交叉引用。",
            )
        for match in _INLINE_DISPLAY_FORMULA_RE.finditer(line):
            raw_anchor = match.group(2)
            if raw_anchor:
                local_id = self._parse_typed_anchor(raw_anchor, "eq", "公式", line_no)
                if local_id:
                    self._add_anchor("eq", local_id, line_no)

    def _check_list_nesting(self, line_no: int, line: str):
        match = _LIST_ITEM_RE.match(line)
        if not match:
            return
        indent = len(match.group(1).replace("\t", "    "))
        if indent >= 6:
            self._issue(
                "LIST_NESTING_TOO_DEEP",
                "warning",
                line_no,
                "列项细分疑似超过两个层次。",
                "GB/T 1.1-2020 规定列项细分不宜超过两个层次。",
            )

    def _check_untyped_anchors(self, line_no: int, line: str):
        for match in _ANCHOR_RE.finditer(line):
            anchor = match.group(1)
            if ":" not in anchor:
                self._issue(
                    "UNTYPED_ANCHOR",
                    "error",
                    line_no,
                    "锚点缺少类型前缀。",
                    "使用 `#tbl:id`、`#fig:id` 或 `#eq:id`。",
                )

    def _scan_references(self):
        for match in _REF_RE.finditer(self.text):
            line_no = self._line_number(match.start())
            self._check_reference(line_no, match.group(1).strip(), match.group(0))
        self._check_broken_reference_braces()

    def _check_reference(self, line_no: int, raw: str, token: str):
        parts = [part.strip() for part in raw.split(":")]
        ref_type = parts[0] if parts else ""
        if ref_type not in _ALLOWED_REF_TYPES:
            self._issue(
                "UNKNOWN_REFERENCE_TYPE",
                "error",
                line_no,
                "未知交叉引用类型：%s。" % (ref_type or token),
                "支持 `tbl`、`fig`、`eq`、`std`。",
            )
            return
        if ref_type == "std":
            if len(parts) != 2 or not parts[1]:
                self._issue(
                    "INVALID_STANDARD_REFERENCE",
                    "error",
                    line_no,
                    "规范性引用文件引用格式不正确。",
                    "写成 `{{std:GB/T 11615}}`，并确保标准号在“规范性引用文件”章中列出。",
                )
                return
            target = parts[1]
            if target not in self.normative_refs:
                self._issue(
                    "UNKNOWN_STANDARD_REFERENCE",
                    "error",
                    line_no,
                    "规范性引用文件未在“规范性引用文件”章中列出：%s。" % target,
                    "补充对应清单条目，或修正 `{{std:...}}` 中的标准号文本。",
                )
            return
        if len(parts) not in (2, 3) or not parts[1]:
            self._issue(
                "INVALID_REFERENCE",
                "error",
                line_no,
                "图表公式引用格式不正确：%s。" % token,
                "写成 `{{%s:id}}`、`{{%s:id:label}}` 或 `{{%s:id:full}}`。" % (ref_type, ref_type, ref_type),
            )
            return
        target = parts[1]
        mode = parts[2] if len(parts) == 3 else "num"
        if mode not in _ALLOWED_REF_MODES:
            self._issue(
                "INVALID_REFERENCE_MODE",
                "error",
                line_no,
                "交叉引用修饰符不支持：%s。" % mode,
                "只支持 `num`、`label`、`full`。",
            )
        if not _ANCHOR_ID_RE.match(target):
            self._issue(
                "INVALID_REFERENCE_ID",
                "error",
                line_no,
                "交叉引用 ID 格式不正确：%s。" % target,
                "ID 需以字母开头，只包含字母、数字、下划线、点和连字符。",
            )
            return
        if (ref_type, target) not in self.anchors:
            self._issue(
                "UNKNOWN_REFERENCE",
                "error",
                line_no,
                "找不到交叉引用目标：{{%s:%s}}。" % (ref_type, target),
                "确认对应 `{#%s:%s}` 锚点存在且类型一致。" % (ref_type, target),
            )

    def _check_broken_reference_braces(self):
        covered_ranges = [match.span() for match in _REF_RE.finditer(self.text)]
        for match in _ANY_REF_BRACE_RE.finditer(self.text):
            if any(start <= match.start() < end for start, end in covered_ranges):
                continue
            self._issue(
                "BROKEN_REFERENCE_BRACES",
                "error",
                self._line_number(match.start()),
                "疑似不完整或嵌套错误的双花括号交叉引用。",
                "检查 `{{...}}` 是否成对，且内部不要再嵌套花括号。",
            )

    def _parse_typed_anchor(self, raw: str, expected_type: str, context: str, line_no: int) -> str:
        if ":" not in raw:
            self._issue(
                "UNTYPED_ANCHOR",
                "error",
                line_no,
                "%s 锚点缺少类型前缀：#%s。" % (context, raw),
                "写成 `#%s:id`。" % expected_type,
            )
            return ""
        ref_type, local_id = [part.strip() for part in raw.split(":", 1)]
        if ref_type != expected_type:
            self._issue(
                "WRONG_ANCHOR_TYPE",
                "error",
                line_no,
                "%s 锚点类型应为 `#%s:id`，实际为 `#%s`。" % (context, expected_type, raw),
                "修正锚点类型或移动到正确的图、表、公式位置。",
            )
            return ""
        if not _ANCHOR_ID_RE.match(local_id):
            self._issue(
                "INVALID_ANCHOR_ID",
                "error",
                line_no,
                "%s 锚点 ID 格式不正确：%s。" % (context, local_id),
                "ID 需以字母开头，只包含字母、数字、下划线、点和连字符。",
            )
            return ""
        return local_id

    def _add_anchor(self, ref_type: str, local_id: str, line_no: int):
        key = (ref_type, local_id)
        if key in self.anchors:
            self._issue(
                "DUPLICATE_ANCHOR",
                "error",
                line_no,
                "重复的 %s 锚点 ID：%s。" % (ref_type, local_id),
                "同一类型的锚点 ID 必须唯一；首次出现于第 %d 行。" % self.anchors[key],
            )
            return
        self.anchors[key] = line_no

    def _line_number(self, position: int) -> int:
        return self.text.count("\n", 0, position) + 1

    def _heading_line(self, title: str) -> int:
        for line_no, level, heading_title in self.heading_entries:
            if level == 1 and heading_title == title:
                return line_no
        return 1

    def _section_lines(self, title: str) -> list[tuple[int, str]]:
        start_index = None
        for idx, (line_no, level, heading_title) in enumerate(self.heading_entries):
            if level == 1 and heading_title == title:
                start_index = (idx, line_no)
                break
        if start_index is None:
            return []
        heading_idx, start_line = start_index
        end_line = len(self.lines) + 1
        for line_no, level, _ in self.heading_entries[heading_idx + 1:]:
            if level == 1:
                end_line = line_no
                break
        return [
            (line_no, self.lines[line_no - 1])
            for line_no in range(start_line + 1, end_line)
        ]

    def _is_appendix_heading(self, title: str) -> bool:
        return title.startswith("附录")

    def _next_non_empty_line(self, line_no: int) -> tuple[int, str] | None:
        for next_no in range(line_no + 1, len(self.lines) + 1):
            line = self.lines[next_no - 1]
            if line.strip():
                return next_no, line
        return None

    def _previous_non_empty_line(self, line_no: int) -> tuple[int, str] | None:
        for previous_no in range(line_no - 1, 0, -1):
            line = self.lines[previous_no - 1]
            if line.strip():
                return previous_no, line
        return None

    def _is_table_start(self, line: str) -> bool:
        stripped = line.strip().lower()
        return stripped.startswith("|") or stripped.startswith("<table")

    def _strip_list_marker(self, line: str) -> str:
        return _LIST_ITEM_RE.sub("", line, count=1)


def issue_dicts(issues: Iterable[Issue]) -> list[dict[str, object]]:
    return [
        {
            "code": issue.code,
            "severity": issue.severity,
            "line": issue.line,
            "message": issue.message,
            "hint": issue.hint,
        }
        for issue in issues
    ]
