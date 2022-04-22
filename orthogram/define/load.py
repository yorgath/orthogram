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
    Iterable,
    List,
    Optional,
    Set,
    cast,
)

import yaml

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
        self._real_path = os.path.realpath(abs_path)
        self._defs = self._load()

    def __repr__(self) -> str:
        """Represent as string."""
        return class_str(self, self._real_path)

    def __eq__(self, other: object) -> bool:
        """True if the other file is the same as the given one."""
        if not isinstance(other, self.__class__):
            return False
        return os.path.samefile(self.real_path, other.real_path)

    def __hash__(self) -> int:
        """Make the file object hashable."""
        return hash(self.real_path)

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
    # Start from the top file.  This *must* be a YAML file.
    abs_path = os.path.abspath(path)
    top_file = YamlFile(abs_path)
    files: List[File] = [top_file]
    expanded: Set[File] = set()
    while True:
        new_files: List[File] = []
        for file in files:
            if _is_file_included(file, new_files):
                continue
            if not file in expanded:
                current_dir = os.path.dirname(file.real_path)
                for idef in file.include_defs:
                    def_path = idef.path
                    if os.path.isabs(def_path):
                        abs_path = def_path
                    else:
                        abs_path = os.path.join(current_dir, def_path)
                    next_file = _make_file(abs_path, idef)
                    _maybe_add_file(next_file, new_files)
                expanded.add(file)
            _maybe_add_file(file, new_files)
        if new_files == files:
            break
        files = new_files
    return files

def _maybe_add_file(file: File, files: List[File]) -> None:
    """Add the file to the list if not already there."""
    if not _is_file_included(file, files):
        files.append(file)

def _is_file_included(file: File, files: Iterable[File]) -> bool:
    """Answer whether the file is already in the collection.

    It prints a warning if the file is already in.

    """
    if file in files:
        log_warning(f"File '{file.real_path}' already included")
        return True
    return False

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
    """Determine the type of the file from its name alone.

    If the name of the file does not have an extension or the
    extension is unrecognizable, the program supposes that it is a
    YAML file (i.e. YAML is the default file type).

    """
    _, ext = os.path.splitext(path)
    if not ext:
        return FileType.YAML
    ext = ext.lower()
    if ext in (".csv", ".txt"):
        return FileType.CSV
    return FileType.YAML
