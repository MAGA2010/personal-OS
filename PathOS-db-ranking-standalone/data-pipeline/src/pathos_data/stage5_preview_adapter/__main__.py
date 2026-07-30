"""Generate a complete deterministic Stage 5 Preview checkpoint."""

from __future__ import annotations

import argparse
from pathlib import Path

from .generator import build_validated_preview_bundle, write_preview_bundle
from .reports import write_reports


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--repo-root", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--report-output", type=Path, required=True)
    args = parser.parse_args()
    bundle = build_validated_preview_bundle(args.repo_root)
    write_preview_bundle(bundle, args.output)
    write_reports(bundle, args.report_output)
    print("Stage 5 deterministic Preview Adapter generation passed")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
