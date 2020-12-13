"""Build diagrams out of definitions in a dictionary."""

from typing import (
    Any,
    Dict,
    List,
    Mapping,
    Optional,
    Sequence,
)

from .diagram import (
    AttributeDict,
    AttributeMap,
    Diagram,
    LabelPosition,
)

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
        self._named_styles: Dict[str, AttributeMap] = {}
        self._group_styles: Dict[str, AttributeMap] = {}
        self._diagram = Diagram()

    @property
    def diagram(self) -> Diagram:
        """The diagram being built."""
        return self._diagram

    def add(self, defs: _Definitions) -> None:
        """Add the definitions to the diagram.

        Valid keys are:

        - diagram
        - terminals
        - rows
        - links
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
        terminal_defs = defs.get('terminals')
        if terminal_defs:
            self.add_terminals(terminal_defs)
        row_defs = defs.get('rows')
        if row_defs:
            self.add_rows(row_defs)
        link_defs = defs.get('links')
        if link_defs:
            self.add_links(link_defs)

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
        styles[name] = self._collect_attributes(style_def)

    def add_groups(self, defs: _Definitions) -> None:
        """Define groups of links in the diagram.

        The input is a mapping between group names and group
        definitions.  See add_group() for the structure of a group
        definition.

        """
        for name, group_def in defs.items():
            self.add_group(name, group_def)

    def add_group(self, name: str, group_def: _Definition) -> None:
        """Define a group of links in the diagram.

        The group definition may contain any attributes plus a 'style'
        reference to a named style.

        If a group with the same name already exists, the old
        definition is replaced with a warning.

        """
        attrs: AttributeDict = {}
        # Merge attributes inherited from style reference.
        style_name = group_def.get('style')
        style_attrs = self._get_style(style_name, True)
        self._merge_attributes(attrs, style_attrs)
        # Merge attributes defined here.
        own_attrs = self._collect_attributes(group_def)
        self._merge_attributes(attrs, own_attrs)
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
        self._diagram.attributes.set_attributes(**attrs)

    def add_terminals(self, defs: _Definitions) -> None:
        """Add terminals to the diagram.

        The input is a mapping between terminal names and terminal
        definitions.  See add_terminal() for the structure of a
        terminal definition.

        """
        for name, terminal_def in defs.items():
            self.add_terminal(name, terminal_def)

    def add_terminal(
            self,
            name: str, terminal_def: Optional[_Definition]
    ) -> None:
        """Add a terminal to the diagram.

        The terminal definition may contain any attributes plus a
        'style' reference to a named style.

        """
        attrs: AttributeDict = {}
        # Merge default terminal attributes.
        def_attrs = self._get_style('default_terminal')
        self._merge_attributes(attrs, def_attrs)
        # The terminal definition may be None: an empty definition.
        if terminal_def:
            # Merge attributes inherited from style reference.
            style_name = terminal_def.get('style')
            style_attrs = self._get_style(style_name, True)
            self._merge_attributes(attrs, style_attrs)
            # Merge attributes defined here.
            own_attrs = self._collect_attributes(terminal_def)
            self._merge_attributes(attrs, own_attrs)
        # Create the object.
        self._diagram.add_terminal(name, **attrs)

    def add_rows(self, row_defs: Sequence[_Definition]) -> None:
        """Add rows of terminal pins to the diagram.

        The input is a sequence of row definitions.  See add_row() for
        the structure of a rwo definition.

        """
        for row_def in row_defs:
            self.add_row(row_def)

    def add_row(self, row_def: _Definition) -> None:
        """Add a row of terminal pins to the diagram.

        The names of the terminals go under the following key:

        - pins: list of terminal names (optional)

        An empty string as a terminal name inserts an empty space into
        the row.

        """
        terminal_names = row_def.get('pins', list())
        self._diagram.add_row(terminal_names)

    def add_links(self, defs: Sequence[_Definition]) -> None:
        """Add links to the diagram.

        The input is a sequence of link definitions.  See add_link()
        for the structure of an link definition.

        """
        for link_def in defs:
            self.add_link(link_def)

    def add_link(self, link_def: _Definition) -> None:
        """Add a link to the diagram.

        The link definition may include any attributes plus the
        following:

        - start: string or list of strings (required)
        - end: string or list of strings (required)
        - style: string (optional)

        """
        start = self._str_or_list(link_def['start'])
        end = self._str_or_list(link_def['end'])
        # Calculate the styles.
        attrs: AttributeDict = {}
        # Merge default link attributes.
        def_attrs = self._get_style('default_link')
        self._merge_attributes(attrs, def_attrs)
        # Merge attributes inherited from group.
        group = link_def.get('group')
        if group and group in self._group_styles:
            group_attrs = self._group_styles[group]
            self._merge_attributes(attrs, group_attrs)
        # Merge attributes inherited from style reference.
        style_name = link_def.get('style')
        style_attrs = self._get_style(style_name, True)
        self._merge_attributes(attrs, style_attrs)
        # Merge attributes defined here.
        own_attrs = self._collect_attributes(link_def)
        self._merge_attributes(attrs, own_attrs)
        # Create the object(s).
        self._diagram.add_links(start, end, **attrs)

    def _collect_attributes(self, any_def: _Definition) -> AttributeMap:
        """Collect the attributes from a definition."""
        attrs: AttributeDict = {}
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
        if 'collapse_links' in any_def:
            attrs['collapse_links'] = bool(any_def['collapse_links'])
        if 'column_margin' in any_def:
            attrs['column_margin'] = float(any_def['column_margin'])
        if 'drawing_priority' in any_def:
            attrs['drawing_priority'] = int(any_def['drawing_priority'])
        if 'end_bias' in any_def:
            end_bias = self._parse_orientation(any_def['end_bias'])
            if end_bias:
                attrs['end_bias'] = end_bias
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
        if 'group' in any_def:
            attrs['group'] = str(any_def['group'])
        if 'label' in any_def:
            attrs['label'] = str(any_def['label'])
        if 'label_distance' in any_def:
            attrs['label_distance'] = float(any_def['label_distance'])
        if 'label_position' in any_def:
            lpos = self._parse_label_position(any_def['label_position'])
            if lpos:
                attrs['label_position'] = lpos
        if 'link_distance' in any_def:
            attrs['link_distance'] = float(any_def['link_distance'])
        if 'min_height' in any_def:
            attrs['min_height'] = float(any_def['min_height'])
        if 'min_width' in any_def:
            attrs['min_width'] = float(any_def['min_width'])
        if 'padding' in any_def:
            attrs['padding'] = float(any_def['padding'])
        if 'row_margin' in any_def:
            attrs['row_margin'] = float(any_def['row_margin'])
        if 'start_bias' in any_def:
            start_bias = self._parse_orientation(any_def['start_bias'])
            if start_bias:
                attrs['start_bias'] = start_bias
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

    def _merge_attributes(self, dest: AttributeDict, src: AttributeMap) -> None:
        """Merge attributes from a definition."""
        if 'arrow_aspect' in src:
            dest['arrow_aspect'] = src['arrow_aspect']
        if 'arrow_back' in src:
            dest['arrow_back'] = src['arrow_back']
        if 'arrow_base' in src:
            dest['arrow_base'] = src['arrow_base']
        if 'arrow_forward' in src:
            dest['arrow_forward'] = src['arrow_forward']
        if 'buffer_fill' in src:
            dest['buffer_fill'] = src['buffer_fill']
        if 'buffer_width' in src:
            dest['buffer_width'] = src['buffer_width']
        if 'collapse_links' in src:
            dest['collapse_links'] = src['collapse_links']
        if 'column_margin' in src:
            dest['column_margin'] = src['column_margin']
        if 'drawing_priority' in src:
            dest['drawing_priority'] = src['drawing_priority']
        if 'end_bias' in src:
            dest['end_bias'] = src['end_bias']
        if 'fill' in src:
            dest['fill'] = src['fill']
        if 'font_family' in src:
            dest['font_family'] = src['font_family']
        if 'font_size' in src:
            dest['font_size'] = src['font_size']
        if 'font_style' in src:
            dest['font_style'] = src['font_style']
        if 'font_weight' in src:
            dest['font_weight'] = src['font_weight']
        if 'group' in src:
            dest['group'] = src['group']
        if 'label' in src:
            dest['label'] = src['label']
        if 'label_distance' in src:
            dest['label_distance'] = src['label_distance']
        if 'label_position' in src:
            dest['label_position'] = src['label_position']
        if 'link_distance' in src:
            dest['link_distance'] = src['link_distance']
        if 'min_height' in src:
            dest['min_height'] = src['min_height']
        if 'min_width' in src:
            dest['min_width'] = src['min_width']
        if 'padding' in src:
            dest['padding'] = src['padding']
        if 'row_margin' in src:
            dest['row_margin'] = src['row_margin']
        if 'stretch' in src:
            dest['stretch'] = src['stretch']
        if 'stroke' in src:
            dest['stroke'] = src['stroke']
        if 'stroke_dasharray' in src:
            dest['stroke_dasharray'] = src['stroke_dasharray']
        if 'start_bias' in src:
            dest['start_bias'] = src['start_bias']
        if 'stroke_width' in src:
            dest['stroke_width'] = src['stroke_width']
        if 'text_fill' in src:
            dest['text_fill'] = src['text_fill']
        if 'text_line_height' in src:
            dest['text_line_height'] = src['text_line_height']
        if 'text_orientation' in src:
            dest['text_orientation'] = src['text_orientation']

    def _get_style(
            self,
            name: Optional[str],
            warn: bool = False
    ) -> AttributeMap:
        """Retrieve the attributes of the style with the given name.

        If the name is empty or the style does not exist, it returns
        an empty attribute set.

        """
        if not name:
            return {}
        attrs = self._named_styles.get(name, {})
        if not attrs and warn:
            log_warning("Style '{}' not found".format(name))
        return attrs

    @staticmethod
    def _str_or_list(text: Any) -> List[str]:
        """Take a string or list of strings and return a list of strings."""
        result = []
        if isinstance(text, list):
            result.extend(text)
        else:
            result.append(str(text))
        return result

    @staticmethod
    def _parse_label_position(s: str) -> Optional[LabelPosition]:
        """Parse the value of a label position attribute."""
        a = s.lower()
        if a == 'bottom':
            return LabelPosition.BOTTOM
        elif a == 'top':
            return LabelPosition.TOP
        else:
            return None

    @staticmethod
    def _parse_orientation(s: str) -> Optional[Orientation]:
        """Parse the value of an orientation attribute."""
        a = s.lower()
        if a == 'horizontal':
            return Orientation.HORIZONTAL
        elif a == 'vertical':
            return Orientation.VERTICAL
        else:
            return None
