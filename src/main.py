#!/usr/bin/env python3
"""
Entry point for the frozen EXE.
"""

import sys
from pathlib import Path

if getattr(sys, "frozen", False):
    base_path = Path(sys.executable).parent
else:
    base_path = Path(__file__).resolve().parent.parent

sys.path.insert(0, str(base_path))

from src.cli import CLI
from src.main_orchestrator import MainOrchestrator


def main() -> int:
    try:
        context = CLI.resolve()
    except SystemExit as e:
        return e.code if isinstance(e.code, int) else 1

    orchestrator = MainOrchestrator(
        context=context,
        output_base=context.output_dir,
    )
    return orchestrator.run()


if __name__ == "__main__":
    sys.exit(main())