"""Functions for loading DDFs and writing SVGs."""

import argparse, os

from typing import Any

import yaml

from .build import Builder
from .diagram import Diagram
from .draw import Drawing
from .layout import Layout

######################################################################

def convert_ddf_from_command_line() -> int:
    """Create a diagram from command line arguments."""
    desc = "Create diagrams with fixed nodes and orthogonal connectors."
    parser = argparse.ArgumentParser(description=desc)
    parser.add_argument(
        'in_file',
        metavar='INFILE',
        help="path of diagram definition file"
    )
    parser.add_argument(
        "-o", "--out",
        metavar='OUTFILE',
        help="write diagram to this file",
        dest='out_file',
    )
    args = parser.parse_args()
    in_file = args.in_file
    out_file = args.out_file
    if not out_file:
        pre, ext = os.path.splitext(in_file)
        out_file = pre + ".svg"
    convert_ddf(in_file, out_file)
    return 0

def convert_ddf(in_file: str, out_file: str) -> None:
    """Create a SVG file from a diagram definition file."""
    diagram = load_ddf(in_file)
    write_svg(diagram, out_file)

def load_ddf(file: str) -> Diagram:
    """Load a diagram definition from a file."""
    definitions = _load_yaml(file)
    builder = Builder()
    builder.add(definitions)
    return builder.diagram

def _load_yaml(file: str) -> Any:
    """Read diagram definitions from a YAML file."""
    with open(file) as s:
        return yaml.safe_load(s)

def write_svg(diagram: Diagram, file: str) -> None:
    """Produce a SVG file of the diagram."""
    layout = Layout(diagram)
    drawing = Drawing(layout)
    drawing.write_svg(file)