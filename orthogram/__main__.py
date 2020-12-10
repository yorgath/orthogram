"""Command line application entry point."""

import sys

from .functions import translate_from_command_line

if __name__ == '__main__':
    result = translate_from_command_line()
    sys.exit(result)
