"""Command line application entry point."""

import sys

from .functions import translate_from_command_line

def _main() -> None:
    """Entry point of program."""
    result = translate_from_command_line()
    sys.exit(result)

if __name__ == '__main__':
    _main()
