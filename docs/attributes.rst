Attributes
==========

The following table summarizes the attributes available to the diagram
and its components.  Where an attribute is applicable, it shows the
default value *in Python*.  In the YAML file, you just omit the
attribute or leave the value empty.  Also, in YAML you can have all
values in lowercase.  The *name* of the attribute *must be* lowercase
in both Python and YAML.

========================  ===============  ============  ==========
Attribute                 Diagram          Block         Connection
========================  ===============  ============  ==========
``arrow_aspect``                                         1.5
``arrow_back``                                           False
``arrow_base``                                           3.0
``arrow_forward``                                        True
``buffer_fill``                                          "none"
``buffer_width``                                         0.0
``collapse_connections``  False
``connection_distance``   4.0
``entrances``                                            [<all>]
``exits``                                                [<all>]
``fill``                  "none"           "none"
``font_family``           None             None
``font_size``             14.0             10.0
``font_style``            None             None
``font_weight``           None             None
``label``                 None             None
``label_distance``        6.0              2.0
``label_position``        TOP              CENTER
``margin_bottom``                          12.0
``margin_left``                            12.0
``margin_right``                           12.0
``margin_top``                             12.0
``min_height``            300.0            48.0
``min_width``             300.0            96.0
``padding_bottom``        0.0              8.0
``padding_left``          0.0              8.0
``padding_right``         0.0              8.0
``padding_top``           0.0              8.0
``pass_through``                           False
``stretch``               True
``stroke_dasharray``      None             None          None
``stroke_width``          0.0              2.0           2.0
``stroke``                "none"           "black"       "black"
``text_fill``             "black"          "black"
``text_line_height``      1.25             1.25
``text_orientation``      HORIZONTAL       HORIZONTAL
========================  ===============  ============  ==========

Basic styling
-------------

stroke
~~~~~~

* Applies to: Diagram, Blocks and Connections
* Type: String
* Default: "none" (D), "black" (B, C)

The ``stroke`` attribute defines the color of a line.  When used with
an area, it applies to the outline.  It is analogous to the SVG
attribute of the same name.  The value can be a color name
(e.g. "darkgreen") or a string of hexadecimal numbers
(e.g. "#FF0088").  Note that color names in SVG files must be
lowercase (i.e. "DarkGreen" is *not* a valid color name).

stroke_width
~~~~~~~~~~~~

* Applies to: Diagram, Blocks and Connections
* Type: Float
* Default: 0.0 (D), 2.0 (B, C)

The ``stroke_width`` attribute defines the width of a connection line
or box outline.  The value is in drawing units (one unit being equal
to 1.25 pt).  It is the equivalent of the ``stroke-width`` SVG
attribute.

stroke_dasharray
~~~~~~~~~~~~~~~~

* Applies to: Diagram, Blocks and Connections
* Type: String
* Default: None

The ``stroke_dasharray`` attribute defines a dash pattern for a line.
It is equivalent to the ``stroke-dasharray`` SVG attribute.  For
example, a value of "6 3" results in a pattern of dashes six units
long separated by gaps three units long.

fill
~~~~

* Applies to: Diagram and Blocks
* Type: String
* Default: "none"

The ``fill`` attribute defines the color to fill areas with.  It is
analogous to the SVG attribute of the same name.

Text
----

label
~~~~~

* Applies to: Diagram and Blocks
* Type: String
* Default: None

The ``label`` attribute defines the text to draw on blocks and the
title of the diagram.  It may consist of several lines separated by
newline characters.  If the label of a block is not defined, its name
is used instead.  To have a block without a label, an empty string
must be specified in the YAML file.

label_position
~~~~~~~~~~~~~~

* Applies to: Diagram and Blocks
* Type: ``LabelPosition``
* Default: TOP (D), CENTER (B)

The ``label_position`` attribute defines the position of the label
inside a box.  The positions available for labels are:

* BOTTOM
* BOTTOM_LEFT
* BOTTOM_RIGHT
* CENTER
* TOP
* TOP_LEFT
* TOP_RIGHT

label_distance
~~~~~~~~~~~~~~

* Applies to: Diagram and Blocks
* Type: Float
* Default: 6.0 (D), 2.0 (B)

The ``label_position`` attribute defines the distance of a label from
the border of the box in which it is drawn.

text_fill
~~~~~~~~~

* Applies to: Diagram and Blocks
* Type: String
* Default: "black"

The ``text_fill`` attribute defines the color in which text is drawn.

text_orientation
~~~~~~~~~~~~~~~~

* Applies to: Diagram and Blocks
* Type: ``Orientation``
* Default: HORIZONTAL

The ``text_orientation`` attribute defines the orientation in which
text is drawn.  If the value is ``VERTICAL``, the text is rotated 90
degrees anticlockwise.

text_line_height
~~~~~~~~~~~~~~~~

* Applies to: Diagram and Blocks
* Type: Float
* Default: 1.25

The ``text_line_height`` attribute is used to provide an estimation of
the height of a single line of text.  The program depends on this
attribute to calculate the height of a label, since it has no way of
knowing the actual dimensions itself (the size of the text depends on
the details of the font that the browser will use for rendering).  The
height of a line of text in drawing units is ``font_size * 1.25 *
text_line_height`` (the extra 1.25 factor is used to convert the font
size from points to drawing units).

font_family
~~~~~~~~~~~

* Applies to: Diagram and Blocks
* Type: String
* Default: None

The ``font_family`` attribute is used to select a font for the label.
It is equivalent to the ``font-family`` attribute in SVG.  If it is
left undefined, the browser renders text using its default font.
Example values are: "sans serif" and "Arial".

font_size
~~~~~~~~~

* Applies to: Diagram and Blocks
* Type: Float
* Default: 14.0 (D), 10.0 (B)

The ``font_size`` attribute defines the size of the font in points.
It is equivalent to the ``font-size`` attribute in SVG.

font_style
~~~~~~~~~~

* Applies to: Diagram and Blocks
* Type: String
* Default: None

The ``font_style`` attribute defines the style of the font used to
render text.  It is equivalent to the ``font-style`` attribute in SVG.
Example: "italic".

font_weight
~~~~~~~~~~~

* Applies to: Diagram and Blocks
* Type: String
* Default: None

The ``font_weight`` attribute defines the weight of the font used to
render text.  It is equivalent to the ``font-weight`` attribute in
SVG.  Example: "bold".

Arrows
------

arrow_forward
~~~~~~~~~~~~~

* Applies to: Connections
* Type: Boolean
* Default: True

If ``arrow_forward`` is true for a connection, the program draws an
arrow head at the end of the connection line.  This is the default.
This attribute is similar to the ``arrowforward`` attribute in
Graphviz.

arrow_back
~~~~~~~~~~

* Applies to: Connections
* Type: Boolean
* Default: False

If ``arrow_back`` is true for a connection, the program draws an arrow
head at the start of the connection line.  By default, the program
does *not* draw a back arrow.  This attribute is similar to the
``arrowback`` attribute in Graphviz.

arrow_base
~~~~~~~~~~

* Applies to: Connections
* Type: Float
* Default: 3.0

Attribute ``arrow_base`` controls the width of the arrow relative to
the width of the line.  The width of the base of the arrow is equal to
``arrow_base * stroke_width``.

arrow_aspect
~~~~~~~~~~~~

* Applies to: Connections
* Type: Float
* Default: 1.5

Attribute ``arrow_aspect`` controls the length of the arrow, which is
equal to ``arrow_aspect * arrow_base * stroke_width``.

Buffering
---------

buffer_width
~~~~~~~~~~~~

* Applies to: Connections
* Type: Float
* Default: 0.0

The ``buffer_width`` attribute defines the width of the buffer around
a connection line.  By default it is zero, i.e. no buffer is drawn.

buffer_fill
~~~~~~~~~~~~

* Applies to: Connections
* Type: String
* Default: "none"

The ``buffer_fill`` attribute defines the color of the buffer around a
connection line.  By default, the color is "none", i.e. no buffer is
visible.

Maintaining distances
---------------------

connection_distance
~~~~~~~~~~~~~~~~~~~

* Applies to: Diagram
* Type: Float
* Default: 4.0

The ``connection_distance`` attribute is used to define the minimum
distance between connection lines.

margin_top
~~~~~~~~~~

* Applies to: Blocks
* Type: Float
* Default: 12.0

margin_bottom
~~~~~~~~~~~~~

* Applies to: Blocks
* Type: Float
* Default: 12.0

margin_left
~~~~~~~~~~~

* Applies to: Blocks
* Type: Float
* Default: 12.0

margin_right
~~~~~~~~~~~~

* Applies to: Blocks
* Type: Float
* Default: 12.0

The ``margin_*`` attributes are used to define the space around
blocks.  They are similar to the ``margin-*`` properties of CSS,
though they are used in a slightly different way.  In Orthogram they
are *additive*, i.e. if one block has a 12 unit right margin and the
block next to it has a 10 unit left margin, the distance between them
will be equal to 22 units.

padding_top
~~~~~~~~~~~

* Applies to: Diagram and Blocks
* Type: Float
* Default: 0.0 (D), 8.0 (B)

padding_bottom
~~~~~~~~~~~~~~

* Applies to: Diagram and Blocks
* Type: Float
* Default: 0.0 (D), 8.0 (B)

padding_left
~~~~~~~~~~~~

* Applies to: Diagram and Blocks
* Type: Float
* Default: 0.0 (D), 8.0 (B)

padding_right
~~~~~~~~~~~~~

* Applies to: Diagram and Blocks
* Type: Float
* Default: 0.0 (D), 8.0 (B)

The ``padding_*`` attributes define the distance between the border of
a box and its contents.  They are similar to the ``padding-*``
properties in CSS.  Note that padding does not affect labels at all.

Sizing
------

min_width
~~~~~~~~~

* Applies to: Diagram and Blocks
* Type: Float
* Default: 300.0 (D), 96.0 (B)

min_height
~~~~~~~~~~

* Applies to: Diagram and Blocks
* Type: Float
* Default: 300.0 (D), 48.0 (B)

The ``min_width`` and ``min_height`` attributes define lower limits
for the dimensions of boxes.  Note that Orthogram will make the size
of the diagram large enough to fit all the elements inside it, and
will also enlarge blocks as needed for the connections attached to
them.  However, since the program cannot calculate the size of a
*label* inside a block, setting the minimum width or height is
sometimes necessary for the block to be large enough to fit the label
in it.  These attributes are analogous to the ``minwidth`` and
``minheight`` attributes in Graphviz.

stretch
~~~~~~~

* Applies to: Diagram
* Type: Boolean
* Default: True

If the value of the ``stretch`` diagram attribute is true, the diagram
expands or shrinks to fit the element that contains it.  If the value
is false, the diagram is rendered in its actual dimensions.

Routing
-------

exits
~~~~~

* Applies to: Connections
* Type: Set of ``Side``
* Default: All possible values

entrances
~~~~~~~~~

* Applies to: Connections
* Type: Set of ``Side``
* Default: All possible values

The ``exits`` and ``entrances`` attributes control the routing of a
connection at the start and end points, respectively.  By default, the
program is free to start routing a connection from any side of the
source block, as well as end at any side of the destination block.
Using the aforementioned attributes, one can restrict the exit and
entrance sides.  The value is a set that can contain any of the
following values:

* BOTTOM
* LEFT
* RIGHT
* TOP

pass_through
~~~~~~~~~~~~

* Applies to: Blocks
* Type: Boolean
* Default: False

By default, a block does not permit connections to pass through it
unless they start or end within the block itself.  Setting
``pass_through`` to false makes a block permeable to all connections.

Grouping
--------

collapse_connections
~~~~~~~~~~~~~~~~~~~~

* Applies to: Diagram
* Type: Boolean
* Default: False

If the value of the ``collapse_connections`` diagram attribute is
true, parallel segments of connections in the same group are drawn on
top of each other.
