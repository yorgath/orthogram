"""Provides types for defining diagrams."""

from abc import (
    ABCMeta,
    abstractmethod,
)

from dataclasses import dataclass
from enum import Enum, auto

from typing import (
    Dict,
    Iterable,
    Iterator,
    List,
    Mapping,
    Optional,
    Sequence,
    Tuple,
    Union,
    cast,
)

from ..util import (
    class_str,
    log_warning,
    vector_repr,
)

from .attributes import (
    AttributeMap,
    Attributes,
)

######################################################################

class TagSet:
    """Collection of unique cell tags.

    It preserves the order of insertion.

    """

    def __init__(self, tags: Iterable[str] = ()):
        """Initialize optionally with some tags."""
        self._tags: List[str] = []
        self.update(tags)

    def __repr__(self) -> str:
        """Represent as string."""
        content = repr(self._tags)[1:-1]
        return class_str(self, content)

    def __iter__(self) -> Iterator[str]:
        """Iterate over the tags."""
        yield from self._tags

    def add(self, tag: str) -> None:
        """Add the tag to the set."""
        tags = self._tags
        if tag not in tags:
            tags.append(tag)

    def remove(self, tag: str) -> None:
        """Remove a tag from the set."""
        self._tags.remove(tag)

    def update(self, tags: Iterable[str]) -> None:
        """Add the tags to the set."""
        for tag in tags:
            self.add(tag)

######################################################################

class RowDef:
    """Definition of a diagram row.

    Holds the information necessary to create a row of diagram cells.

    """

    def __init__(self, index: int, tags: Iterable[Optional[str]]):
        """Initialize with the given sequence of tags."""
        self._index = index
        self._tags = list(tags)

    def __repr__(self) -> str:
        """Represent as string."""
        return class_str(self, self._index)

    def __iter__(self) -> Iterator[Optional[str]]:
        """Iterate over the tags for the cells."""
        yield from self._tags

######################################################################

class LabelDef:
    """Definition of a label.

    Holds the information necessary to create a label.

    """

    def __init__(self, **attrs: AttributeMap):
        """Initialize with the given attributes."""
        self._attributes = attrs

    def __repr__(self) -> str:
        """Represent as string."""
        text = self._attributes.get('label')
        return class_str(self, repr(text))

    @property
    def attributes(self) -> AttributeMap:
        """Attributes of the label."""
        return self._attributes

######################################################################

class BlockDef(metaclass=ABCMeta):
    """Interface of block definitions."""

    @property
    @abstractmethod
    def name(self) -> Optional[str]:
        """Implement this to return the name of the block."""

    @property
    @abstractmethod
    def tags(self) -> TagSet:
        """Implement this to return the tags used to look up cells."""

    @property
    @abstractmethod
    def attributes(self) -> AttributeMap:
        """Implement this to return the attributes to create the block with."""

######################################################################

class UserBlockDef(BlockDef):
    """Definition of a block created by the user.

    Holds the information necessary to create a block.

    """

    def __init__(
            self,
            index: int,
            name: Optional[str] = None,
            tags: Iterable[str] = (),
            **attrs: AttributeMap,
    ):
        """Initialize for a block with the given properties."""
        self._index = index
        self._name = name
        self._tags = TagSet(tags)
        self._attributes = attrs

    def __repr__(self) -> str:
        """Represent as string."""
        parts = [str(self._index)]
        name = self._name
        if name:
            parts.append(f"name={repr(name)}")
        tags = list(self._tags)
        if tags:
            parts.append(f"tags={tags}")
        content = ", ".join(parts)
        return class_str(self, content)

    @property
    def name(self) -> Optional[str]:
        """Name of the block."""
        return self._name

    @property
    def tags(self) -> TagSet:
        """Tags used to look up cells."""
        return TagSet(self._tags)

    @property
    def attributes(self) -> AttributeMap:
        """The attributes to create the block with."""
        return self._attributes

######################################################################

class AutoBlockDef(BlockDef):
    """Definition of a block created by the program itself."""

    def __init__(self, name: str, **attrs: AttributeMap):
        """Initialize for a block with the given properties."""
        self._name = name
        self._attributes = attrs

    def __repr__(self) -> str:
        """Represent as string."""
        content = repr(self._name)
        return class_str(self, content)

    @property
    def name(self) -> str:
        """Name of the block."""
        return self._name

    @property
    def tags(self) -> TagSet:
        """Tags used to look up cells.

        This is actually an empty set; the definition corresponds to a
        single (leftover) tag, which is the name of the block.

        """
        return TagSet()

    @property
    def attributes(self) -> AttributeMap:
        """The attributes to create the block with."""
        return self._attributes

######################################################################

# Connections can be made between whole blocks or nodes of blocks with
# a specifed tag.  A "sub-block" can be defined either by a block name
# (whole block) or a block name and a tag (partial block).
SubBlockDef = Union[str, Tuple[str, Optional[str]]]

def _sub_block_str(sub_block: SubBlockDef) -> str:
    """Return a string that represents the sub-block definition."""
    strings = []
    if isinstance(sub_block, str):
        strings.append(sub_block)
    else:
        strings.append(sub_block[0])
        tag = sub_block[1]
        if tag:
            strings.append(tag)
    return ":".join(strings)

######################################################################

class ConnectionDef:
    """Definition of a connection between two blocks.

    Holds the information necessary to create a connection.

    """

    def __init__(
            self,
            index: int,
            start: SubBlockDef,
            end: SubBlockDef,
            group: Optional[str] = None,
            **attrs: AttributeMap
    ):
        """Initialize given the names of two blocks."""
        self._index = index
        self._start = start
        self._end = end
        self._group = group
        self._attributes = attrs
        self._start_label: Optional[LabelDef] = None
        self._middle_label: Optional[LabelDef] = None
        self._end_label: Optional[LabelDef] = None
        self._init_labels()

    def __repr__(self) -> str:
        """Represent as string."""
        index = self._index
        start = _sub_block_str(self._start)
        end = _sub_block_str(self._end)
        ends = vector_repr(start, end)
        content = f"{index}, ends={ends}"
        return class_str(self, content)

    @property
    def start(self) -> SubBlockDef:
        """Definition of source node."""
        return self._start

    @property
    def end(self) -> SubBlockDef:
        """Definition of destination node."""
        return self._end

    @property
    def group(self) -> Optional[str]:
        """Group to which the connection belongs."""
        return self._group

    @property
    def attributes(self) -> AttributeMap:
        """Attributes to create the connection with."""
        return self._attributes

    @property
    def start_label(self) -> Optional[LabelDef]:
        """Definition of the label at the start of the connection."""
        return self._start_label

    @property
    def middle_label(self) -> Optional[LabelDef]:
        """Definition of the label near the middle of the connection."""
        return self._middle_label

    @property
    def end_label(self) -> Optional[LabelDef]:
        """Definition of the label at the end of the connection."""
        return self._end_label

    def set_start_label(
            self,
            text: Optional[str],
            **attrs: AttributeMap,
    ) -> Optional[LabelDef]:
        """Set the label at the start of the connection."""
        label_def = self._make_label(text, **attrs)
        self._start_label = label_def
        return label_def

    def set_middle_label(
            self,
            text: Optional[str],
            **attrs: AttributeMap,
    ) -> Optional[LabelDef]:
        """Set the label near the middle of the connection."""
        label_def = self._make_label(text, **attrs)
        self._middle_label = label_def
        return label_def

    def set_end_label(
            self,
            text: Optional[str],
            **attrs: AttributeMap,
    ) -> Optional[LabelDef]:
        """Set the label at the end of the connection."""
        label_def = self._make_label(text, **attrs)
        self._end_label = label_def
        return label_def

    def _init_labels(self) -> None:
        """Create the label definitions from the attributes."""
        attrs = self._attributes
        if 'start_label' in attrs:
            label_attrs = attrs['start_label']
            self.set_start_label(None, **label_attrs)
        if 'end_label' in attrs:
            label_attrs = attrs['end_label']
            self.set_end_label(None, **label_attrs)
        if 'middle_label' in attrs:
            label_attrs = attrs['middle_label']
            self.set_middle_label(None, **label_attrs)
        else:
            # If there is label text in the attributes, assume that
            # the user wants to create a middle label with it.
            text = attrs.get('label')
            if text:
                self.set_middle_label(cast(str, text), **attrs)

    def _make_label(
            self,
            text: Optional[str],
            **attrs: AttributeMap,
    ) -> Optional[LabelDef]:
        """Create a label for the connection."""
        if not text:
            if 'label' in attrs:
                own_text = attrs.get('label')
                if own_text:
                    text = cast(str, own_text)
            else:
                parent_text = self._attributes.get('label')
                if parent_text:
                    text = cast(str, parent_text)
        if not text:
            return None
        attributes = Attributes(**attrs)
        attributes['label'] = text
        return LabelDef(**attrs)

######################################################################

# Multiple connection points can be specified as:
# - a single block name (string)
# - a list of block names (sequence of strings)
# - a list of block names and associated tag cells (mapping from
#   string to string)
MultipleNodes = Union[str, Sequence[str], Mapping[str, str]]

def _to_sub_block_defs(multi_nodes: MultipleNodes) -> Sequence[SubBlockDef]:
    """Produce the object necessary for a connection."""
    if isinstance(multi_nodes, str):
        return [multi_nodes]
    if isinstance(multi_nodes, Sequence):
        return multi_nodes
    if isinstance(multi_nodes, Mapping):
        seq = []
        for block_name, tag in multi_nodes.items():
            seq.append((block_name, tag))
        return seq
    raise RuntimeError("Bad connection point definition")

######################################################################

class DiagramDef:
    """Definition of a diagram.

    Holds the information necessary to create a diagram.

    """

    def __init__(self, **attrs: AttributeMap):
        """Initialize with the given diagram attributes.

        See DiagramAttributes for a list of available attributes.

        """
        self._attributes = Attributes(**attrs)
        self._auto_block_attributes = Attributes()
        self._row_defs: List[RowDef] = []
        self._block_defs: List[UserBlockDef] = []
        self._block_defs_by_name: Dict[str, UserBlockDef] = {}
        self._connection_defs: List[ConnectionDef] = []

    @property
    def attributes(self) -> Attributes:
        """The attributes to create the diagram with."""
        return self._attributes

    @property
    def auto_block_attributes(self) -> Attributes:
        """Attributes for blocks generated automatically from tags."""
        return self._auto_block_attributes

    def row_defs(self) -> Iterator[RowDef]:
        """Iterate over the row definitions."""
        yield from self._row_defs

    def block_defs(self) -> Iterator[UserBlockDef]:
        """Iterate over the block definitions."""
        yield from self._block_defs

    def auto_block_defs(self) -> Iterator[AutoBlockDef]:
        """Generate additional block definitions from the leftover tags."""
        attrs = self.auto_block_attributes
        for name in self._leftover_tags():
            yield AutoBlockDef(name, **attrs)

    def connection_defs(self) -> Iterator[ConnectionDef]:
        """Iterate over the connection definitions."""
        yield from self._connection_defs

    def set_auto_block_attributes(self, **attrs: AttributeMap) -> None:
        """Set the attributes of the autogenerated blocks."""
        self._auto_block_attributes = Attributes(**attrs)

    def add_row(self, tags: Iterable[Optional[str]]) -> RowDef:
        """Add a row at the end of the diagram.

        The input is a sequence of strings used to tag the cells with.
        An empty string or None results in an untagged cell.  The
        length of the new row is equal to the number of tags (empty or
        not).

        Returns the definition of the new row.

        """
        rdefs = self._row_defs
        index = len(rdefs)
        rdef = RowDef(index, tags)
        rdefs.append(rdef)
        return rdef

    def add_block(
            self,
            name: Optional[str],
            tags: Iterable[str] = (),
            **attrs: AttributeMap,
    ) -> Optional[UserBlockDef]:
        """Add a new block to the diagram.

        The 'tags' argument is a set of cell tags.  The block will
        cover the cells matching the tags in addition to the cells
        tagged with the name of the block itself.

        See BlockAttributes for a list of available attributes.

        Rejects the block with a warning if there is already a block
        registered with the same name.

        Returns the definition of the new block or None if the block
        was rejected.

        """
        by_name = self._block_defs_by_name
        if name and name in by_name:
            log_warning(f"Block '{name}' already exists")
            return None
        bdefs = self._block_defs
        index = len(bdefs)
        bdef = UserBlockDef(index, name, tags, **attrs)
        bdefs.append(bdef)
        if name:
            by_name[name] = bdef
        return bdef

    def add_connections(
            self,
            starts: MultipleNodes,
            ends: MultipleNodes,
            group: Optional[str] = None,
            **attrs: AttributeMap,
    ) -> List[ConnectionDef]:
        """Create many connections in one go.

        If the number of start blocks is n and the number of end
        blocks in m, then the number of connections created will be
        n*m (assuming all blocks exist).  See add_connection() for
        further information.

        Returns a list of connection definitions.

        """
        cdefs = []
        for start in _to_sub_block_defs(starts):
            for end in _to_sub_block_defs(ends):
                cdef = self.add_connection(start, end, group, **attrs)
                cdefs.append(cdef)
        return cdefs

    def add_connection(
            self,
            start: SubBlockDef, end: SubBlockDef,
            group: Optional[str] = None,
            **attrs: AttributeMap
    ) -> ConnectionDef:
        """Create a connection between two blocks.

        You must supply the start and the end of the connection either
        as block names or pairs of block name and cell tag.

        Provide the name of a group if you want the connection to
        belong to a group.

        See ConnectionAttributes for a list of available attributes.

        Returns the definition of the new connection.

        """
        cdefs = self._connection_defs
        index = len(cdefs)
        cdef = ConnectionDef(index, start, end, group, **attrs)
        cdefs.append(cdef)
        return cdef

    def _leftover_tags(self) -> TagSet:
        """Cell tags that do not appear in block definitions."""
        tags = TagSet(self._placed_tags())
        for bdef in self.block_defs():
            block_tags = TagSet(bdef.tags)
            name = bdef.name
            if name:
                block_tags.add(name)
            for tag in block_tags:
                if tag in tags:
                    tags.remove(tag)
        return tags

    def _placed_tags(self) -> TagSet:
        """Return all the tags from the row definitions.

        It returns each tag only once.  The order of the tags follows
        the order of the row definitions.

        """
        tag_set = TagSet()
        for row in self._row_defs:
            for tag in row:
                if tag:
                    tag_set.add(tag)
        return tag_set

######################################################################

class FileType(Enum):
    """Recognized types of input files."""
    YAML = auto()
    CSV = auto()

######################################################################

@dataclass
class IncludeDef:
    """Include definition."""
    path: str
    file_type: FileType
    delimiter: Optional[str] = None
