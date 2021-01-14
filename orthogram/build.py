"""Build diagrams out of definitions in a dictionary."""

from typing import (
    Any,
    Dict,
    List,
    Mapping,
    Optional,
    Sequence,
    Set,
    Tuple,
)

from .attributes import Attributes, LabelPosition, Side
from .diagram import DiagramDef
from .geometry import Orientation
from .util import log_warning

######################################################################

# Generic definition.
_Definition = Mapping[str, Any]

# Collection of definitions.
_Definitions = Mapping[str, Any]

######################################################################

class Builder:
    """Create a diagram from definitions in a dictionary."""

    def __init__(self) -> None:
        """Initialize the builder."""
        self._named_styles: Dict[str, Attributes] = {}
        self._group_styles: Dict[str, Attributes] = {}
        self._diagram_def = DiagramDef()

    @property
    def diagram_def(self) -> DiagramDef:
        """The definition of the diagram being built."""
        return self._diagram_def

    def add(self, defs: _Definitions) -> None:
        """Add the definitions to the diagram.

        Valid keys are:

        - diagram
        - rows
        - blocks
        - connections
        - styles
        - groups

        See add_* methods for details.

        """
        style_defs = defs.get('styles')
        if style_defs:
            self.add_styles(style_defs)
        group_defs = defs.get('groups')
        if group_defs:
            self.add_groups(group_defs)
        dia_def = defs.get('diagram')
        if dia_def:
            self.configure_diagram(dia_def)
        row_defs = defs.get('rows')
        if row_defs:
            self.add_rows(row_defs)
        block_defs = defs.get('blocks')
        if block_defs:
            self.add_blocks(block_defs)
        connection_defs = defs.get('connections')
        if connection_defs:
            self.add_connections(connection_defs)

    def add_styles(self, defs: _Definitions) -> None:
        """Store named styles in the builder.

        The input is a mapping between style names and style
        definitions.  See add_style() for the structure of a style
        definition.

        """
        for name, style_def in defs.items():
            self.add_style(name, style_def)

    def add_style(self, name: str, style_def: _Definition) -> None:
        """Store a named style in the builder.

        A style is just a collection of attribute key-value pairs.

        If a style with the same name already exists, it replaces the
        older definition with a warning.

        """
        styles = self._named_styles
        if name in styles:
            log_warning("Replacing style '{}'".format(name))
        attrs = self._collect_attributes(style_def)
        if name == 'default_block':
            self._diagram_def.set_auto_block_attributes(**attrs)
        styles[name] = attrs

    def add_groups(self, defs: _Definitions) -> None:
        """Define groups of connections in the diagram.

        The input is a mapping between group names and group
        definitions.  See add_group() for the structure of a group
        definition.

        """
        for name, group_def in defs.items():
            self.add_group(name, group_def)

    def add_group(self, name: str, group_def: _Definition) -> None:
        """Define a group of connections in the diagram.

        The group definition may contain any attributes plus a 'style'
        reference to a named style.

        If a group with the same name already exists, the old
        definition is replaced with a warning.

        """
        attrs = Attributes()
        # Merge attributes inherited from style references.
        style_attrs = self._collect_style_attributes(group_def)
        attrs.merge(style_attrs)
        # Merge attributes defined here.
        own_attrs = self._collect_attributes(group_def)
        attrs.merge(own_attrs)
        # Store the group attributes for later use.
        styles = self._group_styles
        if name in styles:
            log_warning("Replacing attributes of group '{}'".format(name))
        styles[name] = attrs

    def configure_diagram(self, dia_def: _Definition) -> None:
        """Set the attributes of the diagram.

        The definition of the diagram consists of attributes names and
        their values.

        """
        attrs = self._collect_attributes(dia_def)
        self._diagram_def.attributes.merge(attrs)

    def add_rows(self, row_defs: Sequence[Sequence[str]]) -> None:
        """Add rows of cells to the diagram.

        The input is a sequence of row definitions.  See add_row() for
        the structure of a row definition.

        """
        for row_def in row_defs:
            self.add_row(row_def)

    def add_row(self, row_def: Sequence[str]) -> None:
        """Add a row of cells to the diagram.

        The input is a sequence of cell tags.  An empty string results
        in an untagged cell.

        """
        self._diagram_def.add_row(row_def)

    def add_blocks(self, defs: List[_Definition]) -> None:
        """Add blocks to the diagram.

        The input is a sequence of block definitions.  See add_block()
        for the structure of a block definition.

        """
        for block_def in defs:
            self.add_block(block_def)

    def add_block(self, block_def: Optional[_Definition]) -> None:
        """Add a block to the diagram.

        The block definition may contain any attributes plus the
        following:

        - tags: sequence of strings (optional)
        - style: string (optional)

        """
        name: Optional[str] = None
        attrs = Attributes()
        # Merge default attributes.
        def_attrs = self._get_style('default_block')
        attrs.merge(def_attrs)
        tags = []
        # The block definition may be None: an empty definition.
        if block_def:
            name = block_def.get('name')
            # Merge attributes inherited from style references.
            style_attrs = self._collect_style_attributes(block_def)
            attrs.merge(style_attrs)
            # Merge attributes defined here.
            own_attrs = self._collect_attributes(block_def)
            attrs.merge(own_attrs)
            # Additional cells to cover.
            tags = block_def.get('tags', ())
        # Create the object.
        self._diagram_def.add_block(name, tags, **attrs)

    def add_connections(self, defs: Sequence[_Definition]) -> None:
        """Add connections to the diagram.

        The input is a sequence of connection definitions.  See
        add_connection() for the structure of a connection definition.

        """
        for connection_def in defs:
            self.add_connection(connection_def)

    def add_connection(self, connection_def: _Definition) -> None:
        """Add a connection to the diagram.

        The connection definition may include any attributes plus the
        following:

        - start: see below (required)
        - end: see below (required)
        - style: string (optional)

        The start and end of the connection can be given as:

        - a block name (string)
        - many block names (sequence of strings)
        - block names and cell tags (mapping from string to string)

        """
        start = connection_def['start']
        end = connection_def['end']
        group = connection_def.get('group')
        # Calculate the styles.
        attrs = Attributes()
        # Merge default attributes.
        def_attrs = self._get_style('default_connection')
        attrs.merge(def_attrs)
        # Merge attributes inherited from group.
        if group and group in self._group_styles:
            group_attrs = self._group_styles[group]
            attrs.merge(group_attrs)
        # Merge attributes inherited from style references.
        style_attrs = self._collect_style_attributes(connection_def)
        attrs.merge(style_attrs)
        # Merge attributes defined here.
        own_attrs = self._collect_attributes(connection_def)
        attrs.merge(own_attrs)
        # Create the object(s).
        self._diagram_def.add_connections(start, end, group=group, **attrs)

    def _collect_style_attributes(self, any_def: _Definition) -> Attributes:
        """Collect the attributes of the named styles in the definition."""
        style_value = any_def.get('style')
        style_names = self._str_or_list(style_value)
        attrs = Attributes()
        for style_name in style_names:
            style_attrs = self._get_style(style_name, True)
            attrs.merge(style_attrs)
        return attrs

    def _collect_attributes(self, any_def: _Definition) -> Attributes:
        """Collect the attributes from a definition."""
        attrs = Attributes()
        if 'arrow_aspect' in any_def:
            attrs['arrow_aspect'] = float(any_def['arrow_aspect'])
        if 'arrow_back' in any_def:
            attrs['arrow_back'] = bool(any_def['arrow_back'])
        if 'arrow_base' in any_def:
            attrs['arrow_base'] = float(any_def['arrow_base'])
        if 'arrow_forward' in any_def:
            attrs['arrow_forward'] = bool(any_def['arrow_forward'])
        if 'buffer_fill' in any_def:
            attrs['buffer_fill'] = str(any_def['buffer_fill'])
        if 'buffer_width' in any_def:
            attrs['buffer_width'] = float(any_def['buffer_width'])
        if 'collapse_connections' in any_def:
            attrs['collapse_connections'] = bool(
                any_def['collapse_connections'])
        if 'entrances' in any_def:
            entrances = self._parse_sides(any_def['entrances'])
            if entrances:
                attrs['entrances'] = entrances
        if 'exits' in any_def:
            exits = self._parse_sides(any_def['exits'])
            if exits:
                attrs['exits'] = exits
        if 'fill' in any_def:
            attrs['fill'] = str(any_def['fill'])
        if 'font_family' in any_def:
            attrs['font_family'] = str(any_def['font_family'])
        if 'font_size' in any_def:
            attrs['font_size'] = float(any_def['font_size'])
        if 'font_style' in any_def:
            attrs['font_style'] = str(any_def['font_style'])
        if 'font_weight' in any_def:
            attrs['font_weight'] = str(any_def['font_weight'])
        if 'label' in any_def:
            attrs['label'] = str(any_def['label'])
        if 'label_distance' in any_def:
            attrs['label_distance'] = float(any_def['label_distance'])
        if 'label_position' in any_def:
            lpos = self._parse_label_position(any_def['label_position'])
            if lpos:
                attrs['label_position'] = lpos
        if 'connection_distance' in any_def:
            attrs['connection_distance'] = float(any_def['connection_distance'])
        if 'margin_bottom' in any_def:
            attrs['margin_bottom'] = float(any_def['margin_bottom'])
        if 'margin_left' in any_def:
            attrs['margin_left'] = float(any_def['margin_left'])
        if 'margin_right' in any_def:
            attrs['margin_right'] = float(any_def['margin_right'])
        if 'margin_top' in any_def:
            attrs['margin_top'] = float(any_def['margin_top'])
        if 'min_height' in any_def:
            attrs['min_height'] = float(any_def['min_height'])
        if 'min_width' in any_def:
            attrs['min_width'] = float(any_def['min_width'])
        if 'padding_bottom' in any_def:
            attrs['padding_bottom'] = float(any_def['padding_bottom'])
        if 'padding_left' in any_def:
            attrs['padding_left'] = float(any_def['padding_left'])
        if 'padding_right' in any_def:
            attrs['padding_right'] = float(any_def['padding_right'])
        if 'padding_top' in any_def:
            attrs['padding_top'] = float(any_def['padding_top'])
        if 'pass_through' in any_def:
            attrs['pass_through'] = bool(any_def['pass_through'])
        if 'stretch' in any_def:
            attrs['stretch'] = bool(any_def['stretch'])
        if 'stroke' in any_def:
            attrs['stroke'] = str(any_def['stroke'])
        if 'stroke_dasharray' in any_def:
            attrs['stroke_dasharray'] = str(any_def['stroke_dasharray'])
        if 'stroke_width' in any_def:
            attrs['stroke_width'] = float(any_def['stroke_width'])
        if 'text_fill' in any_def:
            attrs['text_fill'] = str(any_def['text_fill'])
        if 'text_line_height' in any_def:
            attrs['text_line_height'] = float(any_def['text_line_height'])
        if 'text_orientation' in any_def:
            text_orientation = self._parse_orientation(
                any_def['text_orientation'])
            if text_orientation:
                attrs['text_orientation'] = text_orientation
        return attrs

    def _get_style(
            self,
            name: Optional[str],
            warn: bool = False
    ) -> Attributes:
        """Retrieve the attributes of the style with the given name.

        If the name is empty or the style does not exist, it returns
        an empty attribute set.

        """
        empty = Attributes()
        if not name:
            return empty
        attrs = self._named_styles.get(name)
        if attrs:
            return attrs
        else:
            if warn:
                log_warning("Style '{}' not found".format(name))
            return empty

    @staticmethod
    def _str_or_list(text: Any) -> List[str]:
        """Take a string or list of strings and return a list of strings."""
        result: List[str] = []
        if not text:
            return result
        if isinstance(text, list):
            result.extend(text)
        else:
            result.append(str(text))
        return result

    @staticmethod
    def _parse_label_position(s: str) -> Optional[LabelPosition]:
        """Parse the value of a label position attribute."""
        result = None
        a = s.strip().upper()
        for member in LabelPosition:
            if member.name == a:
                result = member
                break
        return result

    @staticmethod
    def _parse_orientation(s: str) -> Optional[Orientation]:
        """Parse the value of an orientation attribute."""
        result = None
        a = s.strip().upper()
        for member in Orientation:
            if member.name == a:
                result = member
                break
        return result

    @staticmethod
    def _parse_sides(ss: List[str]) -> Set[Side]:
        """Parse the value of a sides attribute."""
        result = set()
        for s in ss:
            a = s.strip().upper()
            for member in Side:
                if member.name == a:
                    result.add(member)
                    break
        return result
