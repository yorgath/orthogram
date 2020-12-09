"""Command line application entry point."""

import sys

from .functions import convert_ddf_from_command_line

if __name__ == '__main__':
    result = convert_ddf_from_command_line()
    sys.exit(result)
