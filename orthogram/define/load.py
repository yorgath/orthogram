"""Provides facilities for loading data definition files."""

import csv
import os

from abc import (
    ABCMeta,
    abstractmethod,
)

from typing import (
    Any,
    Dict,
    List,
    Optional,
    cast,
)

import yaml

from cassowary import (  # type: ignore
    SimplexSolver,
    Variable,
)

from ..debug import Debug

from ..util import (
    class_str,
    log_info,
    log_warning,
)

from .build import Builder

from .defs import (
    FileType,
    IncludeDef,
)

######################################################################

class File(metaclass=ABCMeta):
    """Encapsulates the information for a file to load."""

    # Encoding of the file.
    ENCODING = "utf-8"

    def __init__(self, abs_path: str):
        """Initialize for the given *absolute* path."""
        self._real_path = path = os.path.realpath(abs_path)
        self._defs = self._load()
        self._index = Variable(path)

    def __repr__(self) -> str:
        """Represent as string."""
        return class_str(self, self._real_path)

    def __eq__(self, other: object) -> bool:
        """True if the other file is the same as the given one."""
        if not isinstance(other, self.__class__):
            return False
        return os.path.samefile(self.real_path, other.real_path)

    @property
    def real_path(self) -> str:
        """Real path of the file."""
        return self._real_path

    @property
    def defs(self) -> Dict[str, Any]:
        """Loaded definitions."""
        return self._defs

    @property
    def include_defs(self) -> List[IncludeDef]:
        """Include definitions loaded from the file."""
        result = []
        defs = self._defs.get('include')
        if defs:
            for mapping in defs:
                path = mapping['path']
                file_type = _parse_file_type(mapping.get('type'))
                if not file_type:
                    file_type = _file_type_from_extension(path)
                delim = mapping.get('delimiter')
                idef = IncludeDef(path, file_type, delim)
                result.append(idef)
        return result

    @property
    def index(self) -> Variable:
        """Index number in the loading sequence."""
        return self._index

    @abstractmethod
    def _load(self) -> Dict[str, Any]:
        """Implement this to return the definitions from the file."""

######################################################################

class YamlFile(File):
    """Represents a YAML diagram definition file."""

    def _load(self) -> Dict[str, Any]:
        """Read the diagram definitions from the YAML file."""
        with open(self._real_path, encoding=self.ENCODING) as stream:
            data = yaml.safe_load(stream)
            if not data:
                return {}
            defs = cast(Dict[str, Any], data)
            return defs

######################################################################

class CsvFile(File):
    """Represents a CSV row definitions file."""

    def __init__(self, abs_path: str, delimiter: Optional[str] = ","):
        """Initialize for the given path."""
        if not delimiter:
            delimiter = ","
        self._delimiter = delimiter
        super().__init__(abs_path)

    def _load(self) -> Dict[str, Any]:
        """Read row definitions from the CSV file."""
        defs = []
        with open(self._real_path, encoding=self.ENCODING) as stream:
            reader = csv.reader(stream, delimiter=self._delimiter)
            for row_def in reader:
                defs.append(row_def)
        return {'rows': defs}

######################################################################

class Loader:
    """Loads a diagram definition from definition files."""

    def __init__(self) -> None:
        """Initialize with an empty definition."""
        self._builder = Builder()

    def load_file(self, path: str) -> None:
        """Load definitions from the file at the given path."""
        files = _collect_files(path)
        for file in files:
            if Debug.is_enabled():
                log_info(f"Adding file '{file.real_path}'")
            self._builder.add(file.defs)

    @property
    def builder(self) -> Builder:
        """The diagram builder into which the definitions are loaded."""
        return self._builder

######################################################################

def _collect_files(path: str) -> List[File]:
    """Return the sequence of all files to be loaded."""
    # Start from the top file.
    abs_path = os.path.abspath(path)
    file = YamlFile(abs_path)
    result: List[File] = [file]
    solver = SimplexSolver()
    # Apply recursion to collect all included files.
    _recur_collect_files(file, solver, result)
    # Sort the files according to the calculated index number.
    key = lambda file: file.index.value
    result.sort(key=key)
    return result

def _recur_collect_files(
        file: File,
        solver: SimplexSolver,
        result: List[File],
) -> None:
    """Recursively collect the included files in the list.

    It uses the solver to calculate the loading index number of each
    file.

    """
    current_dir = os.path.dirname(file.real_path)
    previous_file: Optional[File] = None
    for idef in file.include_defs:
        def_path = idef.path
        if os.path.isabs(def_path):
            abs_path = def_path
        else:
            abs_path = os.path.join(current_dir, def_path)
        next_file = _make_file(abs_path, idef)
        if next_file in result:
            # Avoid double loading and cycles.
            log_warning(f"File '{next_file.real_path}' already included")
        else:
            # Includes must be used in the order they appear.
            if previous_file:
                constraint = next_file.index >= previous_file.index + 1
                solver.add_constraint(constraint)
            result.append(next_file)
            _recur_collect_files(next_file, solver, result)
            previous_file = next_file
    # File must be used after the last include.
    if previous_file:
        constraint = file.index >= previous_file.index + 1
        solver.add_constraint(constraint)

def _make_file(abs_path: str, idef: IncludeDef) -> File:
    """Creates a file object for the given absolute path.

    Additional parameters are derived from the definition.  The
    (possibly relative) path in the definition is ignored.

    """
    if idef.file_type is FileType.CSV:
        return CsvFile(abs_path, idef.delimiter)
    return YamlFile(abs_path)

def _parse_file_type(text: Optional[str]) -> Optional[FileType]:
    """Parse the string into a file type."""
    if not text:
        return None
    if text.lower() == "yaml":
        return FileType.YAML
    if text.lower() == "csv":
        return FileType.CSV
    return None

def _file_type_from_extension(path: str) -> FileType:
    """Determine the type of the file from its name alone."""
    _, ext = os.path.splitext(path)
    if not ext:
        return FileType.YAML
    ext = ext.lower()
    if ext in (".csv", ".txt"):
        return FileType.CSV
    return FileType.YAML
