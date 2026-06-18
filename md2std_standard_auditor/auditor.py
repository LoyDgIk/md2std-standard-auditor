# -*- coding: utf-8 -*-
"""Core Markdown audit rules migrated from the md2std standard skill checklist."""

from __future__ import annotations

from dataclasses import dataclass
import re
from pathlib import Path
from typing import Iterable

from .normative_refs import (
    normalize_standard_id,
    parse_implicit_ref_entry,
    parse_ref_registration,
    standard_aliases,
)

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
_FIGURE_CAPTION_RE = re.compile(r"^\s*\{\s*图\s*[:：]\s*#([^}\s]+)\s*\}\s+(.+?)\s*$")
_FIGURE_CAPTION_MARKER_RE = re.compile(r"^\s*(?:\{\s*)?图\s*[:：]")
_IMAGE_RE = re.compile(r"!\[([^\]]*)\]\(([^)]*)\)")
_INLINE_DISPLAY_FORMULA_RE = re.compile(r"\$\$(.+?)\$\$\s*(?:\{#([^}]+)\})?")
_FORMULA_TAG_RE = re.compile(r"\\tag\s*\{?")
_VISIBLE_TABLE_LABEL_RE = re.compile(r"^表\s*(?:[A-ZＡ-Ｚ]\s*[.．]\s*)?\d+(?:[.．]\d+)?(?:\s|　|$)")
_VISIBLE_FIGURE_LABEL_RE = re.compile(r"^图\s*(?:[A-ZＡ-Ｚ]\s*[.．]\s*)?\d+(?:[.．]\d+)?(?:\s|　|$)")
_LIST_ITEM_RE = re.compile(r"^(\s*)(?:[-+*]|\d+[.)])\s+")
_REFERENCE_ITEM_RE = re.compile(r"^\s*[\[［]\d+[\]］]")
_STANDARD_YEAR_HYPHEN_RE = re.compile(
    r"\b([A-Z][A-Z0-9]*(?:/[A-Z0-9]+)*\s+\d[\w.]*)([-–])(\d{4})\b"
)
_STANDARD_CODE_RE = re.compile(r"^([A-Z][A-Z0-9]*(?:/[A-Z0-9]+)*)\s+(\d+(?:\.\d+)*)")
_GBT_1_1_RE = re.compile(r"GB/T\s*1\.1(?:\s*[—-]\s*2020)?")
_NOTE_LEAD_RE = re.compile(r"^\s*(?:\|\s*)?注(?:\d+)?[：:]")
_MODAL_VERB_RE = re.compile(
    r"不应|不宜|不必|不得|必须|应当|"
    r"(?<![相适反响供])应(?!急|用|对|力|变|响|聘|邀|届|收|答|付|接|试|验|景)|"
    r"(?<!适)宜"
)
_INDEX_GROUP_RE = re.compile(r"^[A-Z]$")
_INDEX_ITEM_RE = re.compile(r"^\s*[-+*]\s+(.+?)[：:]\s*")
_GENERIC_ADDON_RE = re.compile(r"^\s*\{\s*(单位|来源|脚注)\s*\}\s*(.*?)\s*$")
_FIGURE_KEY_ITEM_RE = re.compile(r"^\s*\{\s*图标引\s*\}\s*(.*?)\s*$")
_FIGURE_BODY_PARAGRAPH_RE = re.compile(r"^\s*\{\s*图段\s*\}\s*(.*?)\s*$")
_SUBFIGURE_GROUP_RE = re.compile(r"^\s*\{\s*分图组\s*[:：]\s*(\d+)\s*\}\s*$")
_TERM_MARKER_RE = re.compile(r"^\s*\{\s*术语\s*[:：]\s*(.+?)\s*\}\s*$")
_UNTITLED_CLAUSE_RE = re.compile(r"^\s*\{\s*无标题条\s*[:：]\s*([2-6])\s*\}\s*(\S.*)$", re.S)
_UNTITLED_MARKER_RE = re.compile(r"^\s*\{\s*无标题条\b")
_EXAMPLE_RE = re.compile(r"^\s*示例\s*(\d+)?\s*[:：]")
_EXAMPLE_END_RE = re.compile(r"^\s*\{\s*示例结束\s*\}\s*$")
_BRACED_NOTE_RE = re.compile(r"^\s*\{\s*注\s*\d*\s*[:：].*?\}\s*$")
_OLD_TABLE_CELL_FOOTNOTE_RE = re.compile(r"\{\s*脚注[A-Za-z]*\s*\}")
_REMOVED_MARKERS = (
    (re.compile(r"^\s*\{\s*表注\s*\d*\s*[:：].*?\}\s*$"), "表注语法已移除。", "把普通注写在被注释内容所在单元格内，例如 `段内容〔注：...〕`。"),
    (re.compile(r"^\s*\{\s*图注\s*\d*\s*[:：].*?\}\s*$"), "图注语法已移除。", "图内段落普通注写成 `{图段} 段内容〔注：...〕`；正文注写成 `注：...`。"),
    (re.compile(r"^\s*\{\s*表单位\s*[:：].*?\}\s*$"), "表单位语法已移除。", "图表单位统一写成紧跟表或图的 `{单位} ...`。"),
    (re.compile(r"^\s*\{\s*图单位\s*[:：].*?\}\s*$"), "图单位语法已移除。", "图表单位统一写成紧跟表或图的 `{单位} ...`。"),
    (re.compile(r"^\s*\{\s*表来源\s*[:：].*?\}\s*$"), "表来源语法已移除。", "图表来源统一写成紧跟表或图的 `{来源} ...`。"),
    (re.compile(r"^\s*\{\s*图来源\s*[:：].*?\}\s*$"), "图来源语法已移除。", "图表来源统一写成紧跟表或图的 `{来源} ...`。"),
    (re.compile(r"^\s*\{\s*表脚注\s*[A-Za-z]*\s*[:：].*?\}\s*$"), "表脚注旧语法已移除。", "表格脚注引用点写 `〔脚注〕`，脚注内容写成紧跟表的 `{脚注} ...`。"),
    (re.compile(r"^\s*\{\s*图脚注\s*[A-Za-z]*\s*[:：].*?\}\s*$"), "图脚注旧语法已移除。", "图脚注内容写成紧跟图的 `{脚注} ...`。"),
    (re.compile(r"^\s*\{\s*分图\s*[:：].*?\}\s*$"), "分图旧语法已移除。", "组合分图写成 `{图：#fig:id} 图题`、`{分图组:2}`，后接连续 Markdown 图片。"),
    (re.compile(r"^\s*\{\s*分图组\s*[:：]\s*\d+\s*[|｜].*?\}\s*$"), "分图组内容不应写进标记内。", "写成独立 `{分图组:2}`，后面连续放置 Markdown 图片。"),
    (re.compile(r"^\s*\{\s*图标引\s*[0-9A-Za-z]+\s*[:：].*?\}\s*$"), "图标引不再手写编号。", "写成 `{图标引} 说明的内容`，编号由生成器自动处理。"),
    (re.compile(r"^\s*\{\s*图段\s*[:：].*?\}\s*$"), "图段旧语法已移除。", "写成 `{图段} 图内段落内容`，不要把内容写进 `{}`。"),
)
_PINYIN_INITIAL_RANGES = (
    (-20319, -20284, "A"),
    (-20283, -19776, "B"),
    (-19775, -19219, "C"),
    (-19218, -18711, "D"),
    (-18710, -18527, "E"),
    (-18526, -18240, "F"),
    (-18239, -17923, "G"),
    (-17922, -17418, "H"),
    (-17417, -16475, "J"),
    (-16474, -16213, "K"),
    (-16212, -15641, "L"),
    (-15640, -15166, "M"),
    (-15165, -14923, "N"),
    (-14922, -14915, "O"),
    (-14914, -14631, "P"),
    (-14630, -14150, "Q"),
    (-14149, -14091, "R"),
    (-14090, -13319, "S"),
    (-13318, -12839, "T"),
    (-12838, -12557, "W"),
    (-12556, -11848, "X"),
    (-11847, -11056, "Y"),
    (-11055, -10247, "Z"),
)

_NORMATIVE_REF_LEAD = (
    "下列文件中的内容通过文中的规范性引用而构成本文件必不可少的条款。"
    "其中，注日期的引用文件，仅该日期对应的版本适用于本文件；"
    "不注日期的引用文件，其最新版本"
)
_NORMATIVE_REF_NONE = "本文件没有规范性引用文件"
_TERMS_NONE = "本文件没有需要界定的术语和定义"
_TERMS_LOCAL_LEAD = "下列术语和定义适用于本文件"
_TERMS_IMPORTED_LEAD_RE = re.compile(r"界定的术语和定义适用于本文件")
_TERMS_IMPORTED_AND_LOCAL_LEAD_RE = re.compile(r"界定的以及下列术语和定义适用于本文件")
_SYMBOLS_LEADS = (
    "下列符号适用于本文件",
    "下列缩略语适用于本文件",
    "下列符号和缩略语适用于本文件",
)
_DRAFTING_BASIS_EXPECTED = (
    "本文件按照GB/T 1.1—2020《标准化工作导则　第1部分："
    "标准化文件的结构和起草规则》的规定起草。"
)
_DRAFTING_BASIS_RE = re.compile(r"^\s*(?:-\s*)?本文件.*GB/T\s*1\.1.*起草")
_FORBIDDEN_APPENDIX_HEADINGS = {"范围", "规范性引用文件", "术语和定义"}
_FOUNDATIONAL_UNTITLED_CHAPTERS = {"范围", "规范性引用文件", "术语和定义", "符号和缩略语"}

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
        self.normative_ref_entries: list[tuple[int, str]] = []
        self.heading_entries: list[tuple[int, int, str]] = []
        self.subfigure_image_lines: set[int] = set()

    def run(self) -> list[Issue]:
        self._check_front_matter()
        self._collect_headings()
        self._collect_normative_refs()
        self._check_document_structure()
        self._check_normative_reference_section()
        self._check_normative_reference_order()
        self._check_terms_section()
        self._check_symbols_section()
        self._check_reference_section()
        self._check_index_section()
        self._check_informative_appendix_modal_verbs()
        self._check_md2std_block_markers()
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
            entry = self._parse_normative_ref_line(line)
            if entry is None:
                continue
            if not entry.explicit:
                self._issue(
                    "NORMATIVE_REFERENCE_IMPLICIT_REGISTRATION",
                    "warning",
                    line_no,
                    "规范性引用文件条目使用了旧版自动识别：%s。" % entry.code,
                    "推荐改为行首显式注册，例如 `{{std:%s}} %s`。" % (entry.target, entry.content),
                )
            self.normative_ref_entries.append((line_no, entry.code))
            for alias in standard_aliases(entry.target, entry.code):
                self.normative_refs.add(alias)

    def _parse_normative_ref_line(self, line: str):
        text = self._strip_list_marker(line).strip()
        entry = parse_ref_registration(text)
        if entry is not None:
            return entry
        return parse_implicit_ref_entry(text)

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
                        "GB/T 1.1—2020 规定附录中不准许设置范围、规范性引用文件、术语和定义等内容。",
                    )

    def _check_normative_reference_section(self):
        if not self._has_top_section("规范性引用文件"):
            return
        section = self._section_lines("规范性引用文件")
        non_empty = [(line_no, line.strip()) for line_no, line in section if line.strip()]
        has_none_text = any(_NORMATIVE_REF_NONE in line for _, line in non_empty)
        has_entries = any(self._parse_normative_ref_line(line) is not None for _, line in non_empty)
        has_lead = any(_NORMATIVE_REF_LEAD in line for _, line in non_empty)

        if has_entries and has_none_text:
            self._issue(
                "NORMATIVE_REFERENCES_CONFLICT",
                "error",
                non_empty[0][0],
                "规范性引用文件章同时包含“无引用”说明和引用文件清单。",
                "二者只能保留一种。",
            )
        if has_entries and not has_none_text and not has_lead:
            self._issue(
                "NORMATIVE_REFERENCES_DEFAULT_LEAD_INFO",
                "info",
                non_empty[0][0] if non_empty else 1,
                "规范性引用文件章有清单条目但未手写固定导语，生成器将使用默认导语。",
                "如需手写，应使用 GB/T 1.1 固定导语，不要自行改写。",
            )
        if not has_entries and not has_none_text:
            self._issue(
                "NORMATIVE_REFERENCES_NONE_INFO",
                "info",
                non_empty[0][0] if non_empty else self._heading_line("规范性引用文件"),
                "规范性引用文件章没有清单条目，生成器将使用“本文件没有规范性引用文件。”。",
                "如实际存在规范性引用文件，请补充引用文件清单。",
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

    def _check_normative_reference_order(self):
        section = self._section_lines("规范性引用文件")
        entries: list[tuple[tuple[object, ...], int, str]] = []
        for line_no, line in section:
            entry = self._parse_normative_ref_line(line)
            if entry is None:
                continue
            code = entry.code
            entries.append((self._normative_ref_sort_key(code), line_no, code))
        expected = sorted(entries, key=lambda item: item[0])
        for actual, wanted in zip(entries, expected):
            if actual[2] == wanted[2]:
                continue
            self._issue(
                "NORMATIVE_REFERENCES_ORDER",
                "warning",
                actual[1],
                "规范性引用文件清单顺序疑似不符合 GB/T 1.1 排列规则。",
                "按标准类型排序；同类中国家标准、ISO、IEC 按顺序号，行业/地方/团体等先按代号再按顺序号。当前条目 `%s` 的位置应复核。"
                % actual[2],
            )
            break

    def _check_terms_section(self):
        if not self._has_top_section("术语和定义"):
            return
        section = self._section_lines("术语和定义")
        non_empty = [(line_no, line.strip()) for line_no, line in section if line.strip()]
        has_entries = any(self._is_term_entry_line(line) for _, line in non_empty)
        has_none_text = any(_TERMS_NONE in line for _, line in non_empty)
        has_local_lead = any(_TERMS_LOCAL_LEAD in line for _, line in non_empty)
        has_imported_lead = any(_TERMS_IMPORTED_LEAD_RE.search(line) for _, line in non_empty)
        has_imported_and_local_lead = any(
            _TERMS_IMPORTED_AND_LOCAL_LEAD_RE.search(line) for _, line in non_empty
        )

        if has_entries and has_none_text:
            self._issue(
                "TERMS_SECTION_CONFLICT",
                "error",
                non_empty[0][0],
                "术语和定义章同时包含“无术语”说明和术语条目。",
                "二者只能保留一种；有术语条目时删除“本文件没有需要界定的术语和定义。”。",
            )
            return
        if has_entries and not (has_local_lead or has_imported_lead or has_imported_and_local_lead):
            line_no = next((ln for ln, line in non_empty if self._is_term_entry_line(line)), non_empty[0][0])
            self._issue(
                "TERMS_DEFAULT_LEAD_INFO",
                "info",
                line_no,
                "术语和定义章未手写导语，生成器将使用默认导语。",
                "若同时引用外部术语，手动使用“……界定的以及下列术语和定义适用于本文件。”。",
            )
        if not has_entries and has_local_lead:
            line_no = next((ln for ln, line in non_empty if _TERMS_LOCAL_LEAD in line), non_empty[0][0])
            self._issue(
                "TERMS_LEAD_WITHOUT_TERMS",
                "warning",
                line_no,
                "术语和定义章写了“下列术语和定义适用于本文件”，但未列出术语条目。",
                "补充术语条目；如无术语，改为“本文件没有需要界定的术语和定义。”。",
            )

    def _check_symbols_section(self):
        if not self._has_top_section("符号和缩略语"):
            return
        section = self._section_lines("符号和缩略语")
        non_empty = [(line_no, line.strip()) for line_no, line in section if line.strip()]
        content_lines = [
            (line_no, line)
            for line_no, line in non_empty
            if not _HEADING_RE.match(line) and not self._starts_with_any(line, _SYMBOLS_LEADS)
        ]

        if not content_lines:
            self._issue(
                "SYMBOLS_SECTION_EMPTY",
                "warning",
                non_empty[0][0] if non_empty else self._heading_line("符号和缩略语"),
                "符号和缩略语章为空或只有导语。",
                "补充符号/缩略语说明；如没有必要，可删除该章。",
            )
            return

    def _check_reference_section(self):
        section = self._section_lines("参考文献")
        if not section:
            return
        for line_no, line in section:
            stripped = line.strip()
            if not stripped or _HEADING_RE.match(line):
                continue
            if _GBT_1_1_RE.search(stripped):
                self._issue(
                    "GBT_1_1_IN_REFERENCES",
                    "warning",
                    line_no,
                    "参考文献中列出了 GB/T 1.1。",
                    "GB/T 1.1 通常作为起草依据写入前言；仅在正文存在资料性引用时才宜保留在参考文献。",
                )
            match = _REFERENCE_ITEM_RE.match(stripped)
            if match:
                self._issue(
                    "MANUAL_REFERENCE_NUMBER",
                    "error",
                    line_no,
                    "参考文献条目不应在 Markdown 中手写方括号序号。",
                    "删除 `[1]`、`[2]` 等手写序号，只保留参考文献正文；编号由 md2std/Word 参考文献样式生成。",
                )

    def _check_index_section(self):
        section = self._section_lines("索引")
        if not section:
            return
        current_group = ""
        previous_group = ""
        for line_no, line in section:
            heading = _HEADING_RE.match(line)
            if heading:
                title = heading.group(2).strip().upper()
                if len(heading.group(1)) == 2 and _INDEX_GROUP_RE.match(title):
                    if previous_group and title < previous_group:
                        self._issue(
                            "INDEX_GROUP_ORDER",
                            "warning",
                            line_no,
                            "索引字母分组顺序疑似不符合字母顺序。",
                            "按关键词汉语拼音首字母顺序排列索引分组。",
                        )
                    current_group = title
                    previous_group = title
                continue
            if not current_group:
                continue
            item = _INDEX_ITEM_RE.match(line)
            if not item:
                continue
            keyword = item.group(1).strip()
            initial = self._keyword_initial(keyword)
            if initial and initial != current_group:
                self._issue(
                    "INDEX_ITEM_GROUP_MISMATCH",
                    "warning",
                    line_no,
                    "索引项 `%s` 归入 `%s` 组，按拼音首字母疑似应归入 `%s` 组。"
                    % (keyword, current_group, initial),
                    "按关键词汉语拼音字母顺序编排索引项，并将条目移入对应字母分组。",
                )

    def _check_informative_appendix_modal_verbs(self):
        in_informative_appendix = False
        for line_no, line in enumerate(self.lines, start=1):
            heading = _HEADING_RE.match(line)
            if heading and len(heading.group(1)) == 1:
                title = heading.group(2).strip()
                in_informative_appendix = self._is_appendix_heading(title) and "资料性" in title
                continue
            if not in_informative_appendix:
                continue
            if self._line_has_modal_verb(line):
                self._issue(
                    "INFORMATIVE_APPENDIX_MODAL_VERB",
                    "warning",
                    line_no,
                    "资料性附录中疑似出现要求、推荐或禁止类能愿动词。",
                    "资料性附录宜只给出有助于理解或使用文件的附加信息；改为陈述，或复核附录性质。",
                )

    def _check_md2std_block_markers(self):
        last_target = ""
        target_addons: set[str] = set()
        pending_table_caption = False
        in_html_table = False
        in_example_block = False
        subfigure_group_open = False
        subfigure_count = 0
        current_chapter = ""

        def reset_target():
            nonlocal last_target, target_addons, pending_table_caption, subfigure_group_open, subfigure_count
            last_target = ""
            target_addons = set()
            pending_table_caption = False
            subfigure_group_open = False
            subfigure_count = 0

        for line_no, line in enumerate(self.lines, start=1):
            stripped = line.strip()
            if not stripped:
                continue

            heading = _HEADING_RE.match(line)
            if heading and len(heading.group(1)) == 1:
                current_chapter = heading.group(2).strip()
                reset_target()
                in_html_table = False
                subfigure_group_open = False
                subfigure_count = 0
                continue

            for pattern, message, hint in _REMOVED_MARKERS:
                if pattern.match(line):
                    self._issue("REMOVED_MD2STD_MARKER", "error", line_no, message, hint)
                    reset_target()
                    break
            else:
                pass
            if any(pattern.match(line) for pattern, _, _ in _REMOVED_MARKERS):
                continue

            if _BRACED_NOTE_RE.match(line):
                self._issue(
                    "BRACED_NOTE",
                    "error",
                    line_no,
                    "正文注不应写进 `{注：...}`。",
                    "正文普通注写成 `注：...`；表格单元格内普通注写成 `段内容〔注：...〕`。",
                )
                reset_target()
                continue

            if _UNTITLED_MARKER_RE.match(line) and not _UNTITLED_CLAUSE_RE.match(line):
                self._issue(
                    "INVALID_UNTITLED_CLAUSE",
                    "error",
                    line_no,
                    "无标题条语法不符合 md2std 契约。",
                    "写成 `{无标题条:2} 正文`、`{无标题条:3} 正文` 或 `{无标题条:4} 正文`。",
                )
                reset_target()
                continue

            if _UNTITLED_CLAUSE_RE.match(line) and current_chapter in _FOUNDATIONAL_UNTITLED_CHAPTERS:
                self._issue(
                    "UNTITLED_CLAUSE_IN_FOUNDATIONAL_SECTION",
                    "error",
                    line_no,
                    "`# %s` 章内不应使用 `{无标题条:n}`。" % current_chapter,
                    "范围、规范性引用文件、术语和定义、符号和缩略语内直接写普通段落；"
                    "无标题条只用于术语和定义之后的技术章或附录。",
                )
                reset_target()
                continue

            if _EXAMPLE_END_RE.match(line):
                if not in_example_block:
                    self._issue(
                        "EXAMPLE_END_WITHOUT_START",
                        "error",
                        line_no,
                        "`{示例结束}` 没有对应的 `示例：`。",
                        "仅在多块示例中使用 `{示例结束}`，并确保前面存在 `示例：`。",
                    )
                in_example_block = False
                reset_target()
                continue
            if _EXAMPLE_RE.match(line):
                if in_example_block:
                    self._issue(
                        "NESTED_EXAMPLE_BLOCK",
                        "error",
                        line_no,
                        "示例块疑似嵌套。",
                        "先用 `{示例结束}` 结束当前多块示例，再开始新的示例。",
                    )
                in_example_block = True
                reset_target()
                continue

            if _TERM_MARKER_RE.match(line):
                reset_target()
                continue

            if _TABLE_CAPTION_RE.match(line):
                pending_table_caption = True
                last_target = ""
                target_addons = set()
                subfigure_group_open = False
                continue

            if self._is_table_start(line) and _OLD_TABLE_CELL_FOOTNOTE_RE.search(line):
                self._issue(
                    "OLD_TABLE_CELL_FOOTNOTE_REF",
                    "error",
                    line_no,
                    "表格单元格内脚注引用不应使用 `{脚注}` 或 `{脚注a}`。",
                    "表格单元格中的脚注引用点写成 `〔脚注〕`，脚注内容写成表后的 `{脚注} ...`。",
                )

            if pending_table_caption and self._is_table_start(line):
                last_target = "table"
                target_addons = set()
                pending_table_caption = False
                in_html_table = stripped.lower().startswith("<table") and "</table>" not in stripped.lower()
                continue
            if in_html_table:
                if "</table>" in stripped.lower():
                    in_html_table = False
                    last_target = "table"
                continue
            if last_target == "table" and self._is_table_start(line):
                continue

            if _FIGURE_CAPTION_RE.match(line) or _IMAGE_RE.search(line):
                if subfigure_group_open and _IMAGE_RE.search(line) and not _ANCHOR_RE.search(line):
                    self.subfigure_image_lines.add(line_no)
                    subfigure_count += 1
                    continue
                last_target = "figure"
                target_addons = set()
                subfigure_group_open = False
                subfigure_count = 0
                continue

            generic_addon = _GENERIC_ADDON_RE.match(line)
            if generic_addon:
                addon_name = generic_addon.group(1)
                if last_target not in {"table", "figure"}:
                    self._issue(
                        "ADDON_WITHOUT_TARGET",
                        "error",
                        line_no,
                        "`{%s}` 必须紧跟表格或图片。" % addon_name,
                        "将 `{%s} ...` 移到目标表或图之后，中间不要插入正文段落。" % addon_name,
                    )
                elif addon_name in {"单位", "来源"}:
                    if addon_name in target_addons:
                        self._issue(
                            "DUPLICATE_ADDON",
                            "error",
                            line_no,
                            "`{%s}` 在同一个图表目标后重复出现。" % addon_name,
                            "同一个表或图的 `{%s}` 只能写一次。" % addon_name,
                        )
                    target_addons.add(addon_name)
                subfigure_group_open = False
                continue

            if _FIGURE_KEY_ITEM_RE.match(line) or _FIGURE_BODY_PARAGRAPH_RE.match(line):
                marker = "图标引" if _FIGURE_KEY_ITEM_RE.match(line) else "图段"
                if last_target != "figure":
                    self._issue(
                        "FIGURE_ADDON_WITHOUT_FIGURE",
                        "error",
                        line_no,
                        "`{%s}` 必须紧跟图片。" % marker,
                        "仅图附加项可使用 `{%s} ...`；表格或正文后不要使用该标记。" % marker,
                    )
                subfigure_group_open = False
                continue

            subfigure_group = _SUBFIGURE_GROUP_RE.match(line)
            if subfigure_group:
                columns = int(subfigure_group.group(1))
                if last_target != "figure":
                    self._issue(
                        "FIGURE_ADDON_WITHOUT_FIGURE",
                        "error",
                        line_no,
                        "`{分图组:n}` 必须紧跟图片。",
                        "先写 `{图：#fig:id} 图题` 或普通图片，再写 `{分图组:2}`。",
                    )
                if not 1 <= columns <= 6:
                    self._issue(
                        "INVALID_SUBFIGURE_GROUP",
                        "error",
                        line_no,
                        "分图组并排数量应为 1 到 6。",
                        "写成 `{分图组:2}` 这类有效列数。",
                    )
                if subfigure_group_open:
                    self._issue(
                        "DUPLICATE_SUBFIGURE_GROUP",
                        "error",
                        line_no,
                        "`{分图组:n}` 在同一组合图后重复出现。",
                        "每个组合图只写一次 `{分图组:n}`。",
                    )
                subfigure_group_open = last_target == "figure"
                subfigure_count = 0
                continue

            if subfigure_group_open and subfigure_count == 0:
                self._issue(
                    "EMPTY_SUBFIGURE_GROUP",
                    "error",
                    line_no,
                    "`{分图组:n}` 后至少应紧跟一张 Markdown 图片。",
                    "在 `{分图组:n}` 后连续放置 `![分图题](图片路径)`。",
                )
            if not self._is_table_start(line):
                reset_target()

    def _scan_lines(self):
        for line_no, line in enumerate(self.lines, start=1):
            self._check_heading(line_no, line)
            self._check_table_caption(line_no, line)
            self._check_table_without_caption(line_no, line)
            self._check_figure_caption(line_no, line)
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
            self._check_standard_year_separator(line_no, line)
            self._check_drafting_basis_text(line_no, line)
            self._check_note_modal_verb(line_no, line)

    def _check_drafting_basis_text(self, line_no: int, line: str):
        if not _DRAFTING_BASIS_RE.match(line):
            return
        if self._compact_text(line.lstrip("- ")) == self._compact_text(_DRAFTING_BASIS_EXPECTED):
            return
        self._issue(
            "PREFACE_DRAFTING_BASIS_TEXT",
            "warning",
            line_no,
            "GB/T 1.1 起草依据语句疑似不是规范固定表述。",
            "md2std 会自动生成前言首句；如需手写，应使用“%s”。" % _DRAFTING_BASIS_EXPECTED,
        )

    def _check_standard_year_separator(self, line_no: int, line: str):
        for match in _STANDARD_YEAR_HYPHEN_RE.finditer(line):
            self._issue(
                "STANDARD_YEAR_SEPARATOR",
                "warning",
                line_no,
                "标准编号 `%s%s%s` 中年份连接号疑似使用了 `%s`。"
                % (match.group(1), match.group(2), match.group(3), match.group(2)),
                "顺序号与年份号之间应使用一字线连接号 `—`，例如 `GB/T 1.1—2020`。",
            )

    def _check_note_modal_verb(self, line_no: int, line: str):
        if not _NOTE_LEAD_RE.match(line):
            return
        if not self._line_has_modal_verb(line):
            return
        self._issue(
            "NOTE_MODAL_VERB",
            "warning",
            line_no,
            "注中疑似出现要求、推荐或禁止类能愿动词。",
            "除图表脚注外，注属于附加信息，宜改为事实陈述；如需规定要求，应移入条款或表中段。",
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

    def _check_figure_caption(self, line_no: int, line: str):
        match = _FIGURE_CAPTION_RE.match(line)
        if not match:
            if _FIGURE_CAPTION_MARKER_RE.match(line):
                self._issue(
                    "INVALID_FIGURE_CAPTION",
                    "error",
                    line_no,
                    "图题标记格式不符合 md2std 契约。",
                    "组合图题应写成 `{图：#fig:id} 标题`，标题中不要写图号。",
                )
            return
        local_id = self._parse_typed_anchor(match.group(1), "fig", "图题", line_no)
        if local_id:
            self._add_anchor("fig", local_id, line_no)
        title = match.group(2).strip()
        if _VISIBLE_FIGURE_LABEL_RE.match(title):
            self._issue(
                "MANUAL_FIGURE_NUMBER",
                "error",
                line_no,
                "图题中疑似手写了图号。",
                "图题只写纯标题，例如 `{图：#fig:flow} 流程图`。",
            )

    def _check_images(self, line_no: int, line: str):
        for match in _IMAGE_RE.finditer(line):
            alt = match.group(1).strip()
            anchors = list(_ANCHOR_RE.finditer(alt))
            if line_no in self.subfigure_image_lines:
                if anchors:
                    self._issue(
                        "SUBFIGURE_IMAGE_ANCHOR",
                        "warning",
                        line_no,
                        "分图图片通常不单独设置 `#fig:id` 锚点。",
                        "组合图的交叉引用锚点应写在父图题 `{图：#fig:id} 图题` 中。",
                    )
                continue
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
                "GB/T 1.1—2020 规定列项细分不宜超过两个层次。",
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
        if ":" in raw:
            first, rest = raw.split(":", 1)
            parts = [first.strip(), rest.strip()]
        else:
            parts = [raw.strip()]
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
            target = normalize_standard_id(parts[1])
            if target not in self.normative_refs:
                self._issue(
                    "UNKNOWN_STANDARD_REFERENCE",
                    "error",
                    line_no,
                    "规范性引用文件未在“规范性引用文件”章中列出：%s。" % target,
                    "补充对应清单条目，或修正 `{{std:...}}` 中的标准号文本。",
                )
            return
        parts = [part.strip() for part in raw.split(":")]
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

    def _has_top_section(self, title: str) -> bool:
        return any(level == 1 and heading_title == title for _, level, heading_title in self.heading_entries)

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

    def _starts_with_any(self, text: str, prefixes: Iterable[str]) -> bool:
        stripped = (text or "").strip()
        return any(stripped.startswith(prefix) for prefix in prefixes)

    def _is_term_entry_line(self, line: str) -> bool:
        stripped = (line or "").strip()
        heading = _HEADING_RE.match(stripped)
        return bool(_TERM_MARKER_RE.match(stripped) or (heading and len(heading.group(1)) == 2))

    def _compact_text(self, text: str) -> str:
        return re.sub(r"\s+", "", text or "")

    def _line_has_modal_verb(self, line: str) -> bool:
        stripped = line.strip()
        if not stripped or stripped.startswith("| ---") or stripped.startswith("```"):
            return False
        stripped = _REF_RE.sub("", stripped)
        stripped = _ANCHOR_RE.sub("", stripped)
        return bool(_MODAL_VERB_RE.search(stripped))

    def _keyword_initial(self, keyword: str) -> str:
        keyword = re.sub(r"[`*_《》“”\"'（）()]", "", keyword).strip()
        for char in keyword:
            if char.isascii() and char.isalpha():
                return char.upper()
            initial = self._hanzi_initial(char)
            if initial:
                return initial
        return ""

    def _hanzi_initial(self, char: str) -> str:
        try:
            encoded = char.encode("gb2312")
        except UnicodeEncodeError:
            return ""
        if len(encoded) < 2:
            return ""
        code = encoded[0] * 256 + encoded[1] - 65536
        for start, end, initial in _PINYIN_INITIAL_RANGES:
            if start <= code <= end:
                return initial
        return ""

    def _normative_ref_sort_key(self, code: str) -> tuple[object, ...]:
        code = code.replace("–", "—")
        code = re.sub(r"\s*[—-]\s*\d{4}(?:\.\d+)?$", "", code)
        match = _STANDARD_CODE_RE.match(code)
        if not match:
            return (99, code)
        prefix = match.group(1)
        sequence = self._number_tuple(match.group(2))
        category = self._standard_category(prefix)
        if category in (1, 5):
            return (category, sequence, prefix)
        return (category, prefix, sequence)

    def _standard_category(self, prefix: str) -> int:
        if prefix in {"GB", "GB/T", "GB/Z"}:
            return 1
        if prefix.startswith("DB"):
            return 3
        if prefix.startswith("T/"):
            return 4
        if prefix in {"ISO", "ISO/IEC", "IEC"}:
            return 5
        if "/" in prefix or prefix.isalpha():
            return 2
        return 6

    def _number_tuple(self, text: str) -> tuple[int, ...]:
        return tuple(int(part) for part in text.split(".") if part.isdigit())


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
