"""Command line interface for agent-session-recorder."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path
from typing import Iterable, Optional

from .doctor import doctor_exit_code, render_doctor_json, render_doctor_markdown, run_doctor
from .exporters import export_bundle
from .importers import import_records
from .model import CommandRecord, SessionBundle
from .redaction import Redactor
from .summarizer import build_summary
from .timeline import build_timeline, render_timeline_json, render_timeline_markdown


def main(argv: Optional[Iterable[str]] = None) -> int:
    parser = build_parser()
    args = parser.parse_args(list(argv) if argv is not None else None)
    try:
        return args.func(args)
    except Exception as exc:
        print(f"agent-session-recorder: error: {exc}", file=sys.stderr)
        return 2


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="agent-session-recorder",
        description="Record offline, auditable AI coding agent session bundles.",
    )
    parser.add_argument("--redact-pattern", action="append", default=[], help="Additional regex pattern to redact.")
    subparsers = parser.add_subparsers(dest="command_name", required=True)

    init = subparsers.add_parser("init", help="Create a new session bundle directory.")
    init.add_argument("session_dir", type=Path)
    init.add_argument("--goal", required=True)
    init.add_argument("--title", default="")
    init.add_argument("--actor", default="ai-coding-agent")
    init.add_argument("--force", action="store_true")
    init.set_defaults(func=cmd_init)

    add_command = subparsers.add_parser("add-command", help="Record a command and optional evidence.")
    add_common_session_arg(add_command)
    add_command.add_argument("--cmd", required=True)
    add_command.add_argument("--cwd", default="")
    add_command.add_argument("--exit-code", type=int)
    add_command.add_argument("--stdout", default="")
    add_command.add_argument("--stderr", default="")
    add_command.add_argument("--stdout-file", type=Path)
    add_command.add_argument("--stderr-file", type=Path)
    add_command.add_argument("--started-at", default="")
    add_command.add_argument("--ended-at", default="")
    add_command.add_argument("--note", default="")
    add_command.set_defaults(func=cmd_add_command)

    add_file = subparsers.add_parser("add-file", help="Attach a context file or evidence artifact.")
    add_common_session_arg(add_file)
    add_file.add_argument("path", type=Path)
    add_file.add_argument("--role", default="context")
    add_file.add_argument("--note", default="")
    add_file.set_defaults(func=cmd_add_file)

    import_transcript = subparsers.add_parser("import-transcript", help="Import transcript, notes, history, diff, or test output.")
    add_common_session_arg(import_transcript)
    import_transcript.add_argument("path", type=Path)
    import_transcript.add_argument(
        "--type",
        choices=["auto", "transcript", "shell-history", "git-diff", "pytest", "junit", "notes"],
        default="auto",
    )
    import_transcript.set_defaults(func=cmd_import_transcript)

    summarize = subparsers.add_parser("summarize", help="Generate deterministic summary, risks, and follow-up items.")
    add_common_session_arg(summarize)
    summarize.set_defaults(func=cmd_summarize)

    export = subparsers.add_parser("export", help="Export a bundle as Markdown, JSON, or ZIP.")
    add_common_session_arg(export)
    export.add_argument("--format", choices=["markdown", "json", "zip"], required=True)
    export.add_argument("--output", type=Path, required=True)
    export.add_argument("--check", action="store_true", help="Validate hashes before exporting.")
    export.set_defaults(func=cmd_export)

    check = subparsers.add_parser("check", help="Validate bundle integrity without exporting.")
    add_common_session_arg(check)
    check.set_defaults(func=cmd_check)

    doctor = subparsers.add_parser("doctor", help="Check whether a bundle is ready for review or CI.")
    add_common_session_arg(doctor)
    doctor.add_argument("--format", choices=["markdown", "json"], default="markdown")
    doctor.add_argument("--output", type=Path)
    doctor.add_argument("--fail-on", choices=["error", "warning"], default="error")
    doctor.set_defaults(func=cmd_doctor)

    timeline = subparsers.add_parser("timeline", help="Render a chronological audit timeline for a session bundle.")
    add_common_session_arg(timeline)
    timeline.add_argument("--format", choices=["markdown", "json"], default="markdown")
    timeline.add_argument("--output", type=Path)
    timeline.set_defaults(func=cmd_timeline)

    return parser


def add_common_session_arg(parser: argparse.ArgumentParser) -> None:
    parser.add_argument("--session", type=Path, required=True, help="Session bundle directory.")


def get_redactor(args: argparse.Namespace) -> Redactor:
    return Redactor(args.redact_pattern)


def load_bundle(args: argparse.Namespace) -> SessionBundle:
    return SessionBundle.load(args.session)


def cmd_init(args: argparse.Namespace) -> int:
    bundle = SessionBundle.create(
        args.session_dir,
        goal=args.goal,
        title=args.title,
        actor=args.actor,
        force=args.force,
        redactor=get_redactor(args),
    )
    print(f"created session: {bundle.root}")
    return 0


def cmd_add_command(args: argparse.Namespace) -> int:
    stdout = args.stdout
    stderr = args.stderr
    if args.stdout_file:
        stdout = args.stdout_file.read_text(encoding="utf-8", errors="replace")
    if args.stderr_file:
        stderr = args.stderr_file.read_text(encoding="utf-8", errors="replace")
    bundle = load_bundle(args)
    bundle.add_command(
        CommandRecord(
            command=args.cmd,
            cwd=args.cwd,
            exit_code=args.exit_code,
            started_at=args.started_at,
            ended_at=args.ended_at,
            stdout=stdout,
            stderr=stderr,
            note=args.note,
        ),
        redactor=get_redactor(args),
    )
    print("recorded command")
    return 0


def cmd_add_file(args: argparse.Namespace) -> int:
    bundle = load_bundle(args)
    record = bundle.add_file(args.path, role=args.role, note=args.note, redactor=get_redactor(args))
    print(f"attached file: {record.bundle_path}")
    return 0


def cmd_import_transcript(args: argparse.Namespace) -> int:
    import_type, records = import_records(args.path, args.type)
    bundle = load_bundle(args)
    path = bundle.add_import(import_type, str(args.path), records, redactor=get_redactor(args))
    print(f"imported {len(records)} {import_type} record(s): {path}")
    return 0


def cmd_summarize(args: argparse.Namespace) -> int:
    bundle = load_bundle(args)
    summary, risks, followups = build_summary(bundle)
    bundle.set_summary(summary, risks, followups, redactor=get_redactor(args))
    print(summary)
    if risks:
        print("\nRisks:")
        for item in risks:
            print(f"- {item}")
    if followups:
        print("\nFollow-ups:")
        for item in followups:
            print(f"- {item}")
    return 0


def cmd_export(args: argparse.Namespace) -> int:
    bundle = load_bundle(args)
    if args.check:
        ok, errors = bundle.check()
        if not ok:
            for error in errors:
                print(error, file=sys.stderr)
            return 1
    export_bundle(bundle, args.output, args.format)
    print(f"exported {args.format}: {args.output}")
    return 0


def cmd_check(args: argparse.Namespace) -> int:
    bundle = load_bundle(args)
    ok, errors = bundle.check()
    if ok:
        print("bundle integrity ok")
        return 0
    for error in errors:
        print(error, file=sys.stderr)
    return 1


def cmd_doctor(args: argparse.Namespace) -> int:
    bundle = load_bundle(args)
    report = run_doctor(bundle)
    output = render_doctor_json(report) if args.format == "json" else render_doctor_markdown(report)
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(output, encoding="utf-8")
    else:
        print(output, end="")
    return doctor_exit_code(report, args.fail_on)


def cmd_timeline(args: argparse.Namespace) -> int:
    bundle = load_bundle(args)
    timeline = build_timeline(bundle)
    output = render_timeline_json(timeline) if args.format == "json" else render_timeline_markdown(timeline)
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(output, encoding="utf-8")
    else:
        print(output, end="")
    return 0
