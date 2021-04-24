"""Functions for loading DDFs and writing image files."""

import argparse
import os

from typing import Any, Optional

import yaml

from .arrange import Layout
from .debug import Debug
from .define import Builder, DiagramDef
from .draw import Drawing

######################################################################

def translate_from_command_line() -> int:
    """Create a diagram from command line arguments."""
    desc = "Create diagrams with fixed nodes and orthogonal connectors."
    parser = argparse.ArgumentParser(description=desc)
    parser.add_argument(
        'in_file',
        metavar='INFILE',
        help="path of diagram definition file"
    )
    parser.add_argument(
        "-d", "--debug",
        action='store_true',
        help="print debug information while running",
        dest='debug',
    )
    parser.add_argument(
        "-o", "--out",
        metavar='OUTFILE',
        help="write diagram to this file",
        dest='out_file',
    )
    args = parser.parse_args()
    Debug.set_debug(args.debug)
    translate(args.in_file, args.out_file)
    return 0

def translate_dir(in_dir: str, out_dir: Optional[str] = None) -> None:
    """Translate all the files in a directory.

    The diagram definition files in the input directory must end in
    ".yaml" or ".yml".

    """
    if not out_dir:
        out_dir = in_dir
    in_files = sorted(os.listdir(in_dir))
    for in_file in in_files:
        if in_file.endswith(".yaml") or in_file.endswith(".yml"):
            in_path = os.path.join(in_dir, in_file)
            base, _ = os.path.splitext(in_file)
            out_file = base + ".png"
            out_path = os.path.join(out_dir, out_file)
            print(in_path, "=>", out_path)
            translate(in_path, out_path)

def translate(in_file: str, out_file: Optional[str] = None) -> None:
    """Create a PNG file from a diagram definition file."""
    diagram = load_ddf(in_file)
    if not out_file:
        pre, _ = os.path.splitext(in_file)
        out_file = pre + ".png"
    write_png(diagram, out_file)

def load_ddf(file: str) -> DiagramDef:
    """Load a diagram definition from a file."""
    definitions = _load_yaml(file)
    builder = Builder()
    builder.add(definitions)
    return builder.diagram_def

def _load_yaml(file: str) -> Any:
    """Read diagram definitions from a YAML file."""
    with open(file, encoding='utf-8') as stream:
        return yaml.safe_load(stream)

def write_png(diagram_def: DiagramDef, file: str) -> None:
    """Produce a PNG file of the diagram."""
    layout = Layout(diagram_def)
    drawing = Drawing(layout)
    drawing.write_png(file)
