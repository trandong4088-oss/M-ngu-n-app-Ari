"""
ARO Studio Worker CLI Entrypoint
"""

from __future__ import annotations

import argparse
import sys
from aro_worker import __version__
from aro_worker.core.doctor import run_doctor


def create_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="aro",
        description="ARO Studio Worker CLI — Video Subtitling, Translation, and Audio Dubbing Engine.",
    )
    parser.add_argument(
        "--version",
        action="version",
        version=f"aro-worker {__version__}",
        help="Show ARO worker version and exit.",
    )

    subparsers = parser.add_subparsers(dest="subcommand", help="Available subcommands")

    # doctor subcommand
    doctor_parser = subparsers.add_parser(
        "doctor",
        help="Diagnose system environment, disk space, FFmpeg filters, and hardware acceleration.",
    )
    doctor_parser.add_argument(
        "--json",
        action="store_true",
        help="Output diagnosis report as structured JSON.",
    )
    doctor_parser.add_argument(
        "--check",
        action="store_true",
        help="Return exit code 1 if critical host requirements fail.",
    )

    # worker subcommand (placeholder with explicit task notification)
    worker_parser = subparsers.add_parser(
        "worker",
        help="Start worker daemon to poll and execute jobs from Google Drive.",
    )
    worker_parser.add_argument(
        "--config",
        default="configs/worker.example.yaml",
        help="Path to worker configuration YAML.",
    )

    return parser


def main(argv: list[str] | None = None) -> int:
    parser = create_parser()
    args = parser.parse_args(argv)

    if args.subcommand == "doctor":
        return run_doctor(output_json=args.json, check_mode=args.check)
    elif args.subcommand == "worker":
        print("ARO Studio Worker Daemon")
        print(f"Config path: {args.config}")
        print("STATUS: NOT_IMPLEMENTED in Task A01.")
        print("Job polling, lifecycle and fencing will be introduced in Task A04 (Controller, jobs & fencing).")
        return 1
    else:
        parser.print_help()
        return 0


if __name__ == "__main__":
    sys.exit(main())
