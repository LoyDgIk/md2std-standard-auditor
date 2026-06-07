# -*- coding: utf-8 -*-
"""Command line interface for md2std-standard-auditor."""

from __future__ import annotations

import argparse
import json
import sys

from .auditor import SEVERITY_ORDER, audit_file, issue_dicts


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        prog="md2std-audit",
        description="审校 md2std 中文标准 Markdown，不生成 DOCX。",
    )
    parser.add_argument("input", help="输入 Markdown 文件")
    parser.add_argument(
        "--format",
        choices=("text", "json"),
        default="text",
        help="输出格式，默认 text。",
    )
    parser.add_argument(
        "--fail-level",
        choices=tuple(SEVERITY_ORDER.keys()),
        default="error",
        help="达到该级别即返回非零退出码，默认 error。",
    )
    args = parser.parse_args(argv)

    try:
        result = audit_file(args.input)
    except OSError as exc:
        sys.stderr.write("读取文件失败：%s\n" % exc)
        return 2
    except UnicodeDecodeError as exc:
        sys.stderr.write("文件不是有效 UTF-8：%s\n" % exc)
        return 2

    if args.format == "json":
        payload = {
            "source": result.source,
            "ok": result.ok,
            "issues": issue_dicts(result.issues),
        }
        sys.stdout.write(json.dumps(payload, ensure_ascii=False, indent=2) + "\n")
    else:
        if not result.issues:
            sys.stdout.write("OK: no audit issues\n")
        else:
            for issue in result.issues:
                sys.stdout.write(
                    "%s:%d: %s %s: %s\n"
                    % (result.source, issue.line, issue.severity, issue.code, issue.message)
                )
                if issue.hint:
                    sys.stdout.write("  hint: %s\n" % issue.hint)

    return 1 if result.has_issues_at_or_above(args.fail_level) else 0

