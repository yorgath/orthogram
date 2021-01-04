Diagram definition file
=======================

Orthogram uses YAML for its input file format.  Of course, YAML being
a superset of JSON, you can use JSON if you prefer so.  The top-level
structure must be a YAML mapping; the program recognizes the following
keys, each one containing a different category of definitions:

* ``diagram``
* ``rows``
* ``terminals``
* ``links``
* ``styles``
* ``groups``

``diagram``
-----------

The ``diagram`` section contains the :ref:`Attributes` of the diagram
itself.  It is entirely optional; you do not need one if you do not
intend to customize your diagram.  Here is an example of a ``diagram``
section:

.. code-block:: yaml

   diagram:
     label: This is my diagram!
     label_position: bottom
     font_weight: bold

The optional label of the diagram is the title of the drawing.  If you
want a label with more than one line of text, use the newline
character in the string:

.. code-block:: yaml

   diagram:
     label: Two lines separated by\na newline character

For longer texts, the YAML literal style may be more convenient:

.. code-block:: yaml

   diagram:
     label: |-
       You can also use
       YAML literal style

Consult the :ref:`Attributes` section for a list of attributes
available for diagrams.  Out of all those attributes, however, the
following are of particular significance to the program:

``collapse_links``
  If you set this to ``true``, collinear segments of links belonging
  to the same ``group`` will collapse into a single segment.  This may
  help reduce the clutter, though it depends on the application.  Try
  it out and see.

``stretch``
  By default, the diagram resizes itself to fill the element that
  contains it.  Set this attribute to ``false`` to make the browser
  render the diagram in its original dimensions.

``rows``
--------

The ``rows`` section of the diagram definition file defines the layout
of the diagram.  It is essential; without one the program cannot
determine the position of any element to draw!

The program lays out the elements of the diagram in a rectangular
grid.  The grid consists of *cells*, which are arranged in rows and
columns.  You define the grid one row at a time.

The ``rows`` structure is a sequence of row definitions.  Each row
definition is a sequence of strings.  Each string corresponds to one
cell in the row.  If the string is *not* empty the cell is *tagged*
with the string; otherwise it is an anonymous cell.  Here is an
example:

.. code-block:: yaml

   rows:
     - [a, "", c, c]
     - [b, "", c, c]

The grid above contains a cell tagged with "a", another one tagged
with "b", two anonymous cells, and four cells tagged with "c".

You use the tags to refer to a cell or group of cells.  More
precisely, you use the tags to define the positions of the
*terminals*, which is the subject of the section that follows.

Note that, since the grid is rectangular, all the rows must contain
the same number of cells, which is the length of the longest row in
the definition.  You do not have to worry about it, though; the
program will pad shorter rows with anonymous cells, until all rows
have the same length.

``terminals``
-------------

The terminals are the elements of the diagram where links terminate.
Each terminal occupies a rectangular area of the diagram grid.  You
must have at least a couple of terminals to produce a meaningful
diagram.

The ``terminals`` section contains mappings between terminal names and
terminal definitions.  Here is an example:

.. code-block:: yaml

   terminals:
     a:
       label: A terminal
     b:
       label: Another terminal
       stroke: blue

Note that if you do not define a label for a terminal, the program
will use its name as a label instead.

A terminal occupies the minimal rectangular area of the grid that
contains all the cells tagged with the name of the terminal.  In the
example that follows, terminal "b" is just one cell, whereas terminal
"b" covers six cells, including the cell on which "a" stands:

.. code-block:: yaml

   rows:
     - ["b", "a"     ]
     - ["" , "" , "b"]
   terminals:
     a:
       label: A single-cell terminal
       drawing_priority: 1
     b:
       label: A terminal of 6 cells

Terminals can overlap each other.  In the example above, terminal "b"
contains terminal "a" in its entirety.  The ``drawing_priority``
attribute ensures that the program draws "a" *over* "b"; otherwise it
will be completely hidden by it.  The program draws terminals with
higher priority over terminals with lower priority.  The default
priority is zero.

If you want to expand a terminal beyond the cells tagged with its own
name, you can add more tags to it using the ``cover``
pseudo-attribute:

.. code-block:: yaml

   rows:
     - ["a", "", "b"]
     - ["a", "", "c"]
     - ["a", "", "" ]
   terminals:
     a:
       label: Covers 9 cells!
       cover: ["b", "c"]

The ``cover`` pseudo-attribute has an additional function.  Terminal
"a" in the example above has eight *nodes* on which links can be
attached, one for each outer cell that it occupies (the cell in the
middle cannot be used for connections.)  The program creates links
using a shortest path algorithm; however when it has to chose among
paths with the same length, it gives precedence to the nodes according
to the sequnce in the ``cover`` attribute.  The name of the terminal
comes last, unless you explicitly include it in the ``cover``
sequence.

The ability to have overlapping terminals is most useful when you want
to draw a frame around a bunch of terminals.  In the example that
follows, a terminal named "frame" functions as a frame around
terminals "a" and "b":

.. code-block:: yaml

   rows:
     - ["a", "b"]
   terminals:
     frame:
       cover: ["a", "b"]
       label: Frame around a and b
       label_position: top
       drawing_priority: -1

Tags that are neither names of terminals nor mentioned in a ``cover``
sequence are "leftover" tags.  The program does not throw them away.
Instead, it uses them to *autogenerate* terminals, one terminal for
each unique tag.  These automatically generated terminals come with
default attributes and are labelled with their name.  This is a
convenience for simple quick-and-dirty diagrams.  The example below is
a complete, self-contained diagram definition, without a ``terminals``
section in it:

.. code-block:: yaml

   rows:
     - ["a", "b"]
   links:
     - start: a
       end: b

``links``
---------

The ``links`` section defines the connections between the terminals.
It is a sequence of link definitions. Each link must declare the names
of the ``start`` and ``end`` terminals, as well as any
:ref:`Attributes` appropriate for links.  Here is an example:

.. code-block:: yaml

   terminals:
     a: {label: First terminal}
     b: {label: Second terminal}
     c: {label: Third terminal}
   rows:
     - [a,  b]
     - ["", c]
   links:
     - start: a
       end: b
       stroke: blue
     - start: b
       end: c
       stroke: "#FF8844"

Note that the ``start`` and ``end`` values of a link definition can be
*sequences* of terminal names as well.  This lets you make multiple
connections in a single definition, all links sharing the same
attributes.  For example, the following definition creates six links:

.. code-block:: yaml

   links:
     - start: [a, b]
       end: [c, d, e]

Of particular interest is the ``drawing_priority`` attribute.  The
program draws links with a higher priority number *over* links with a
lower priority.  Since it is not easy to avoid the intersection of
links in complex diagrams, it is better that you draw intersecting
links with a different ``stroke`` color to make obvious that the links
are not connected at the intersection points.  The
``drawing_priority`` lets you draw sets of links as layers on top of
each other, giving a more consistent look to your diagram.

Another way to avoid intersecting links appearing as if they were
connected at the intersections is to draw a *buffer* around the links.
Attributes ``buffer_fill`` and ``buffer_width`` control the appearance
of the buffer.  By default, the program draws the links without a
buffer.

Links may have an additional ``group`` attribute, which works together
with the ``collapse_links`` diagram attribute.  If ``collapse_links``
is set to true, links of the same group that run along the same axis
can be drawn on top of each other, thus reducing the clutter and size
of the diagram.  The ``group`` value is just a string.  Note that
setting this attribute affects the drawing priority of the links.  All
links in the same group must share the same priority, which is the
highest priority among all links in the group.

``styles``
----------

You can add style definitions to the ``styles`` section to create
named styles that the elements of the diagram (terminals, links and
groups) can refer to.  Each style definition consists of attribute
key-value pairs.  For example, the following two terminals are drawn
in the same color:

.. code-block:: yaml

   terminals:
     a:
       style: reddish
     b:
       style: reddish
   rows:
     - [a, b]
   styles:
     reddish:
       stroke: "#880000"
       stroke_width: 3.0
       fill: "#FFDDDD"

You add style references to an element using the ``style`` attribute.
The value of this attribute can be either a single style name or a
list of style names.  When in a list, later styles override the ones
coming before them.  Attributes you define in the element itself
override the attributes it inherits from the referenced named styles.

There are two special style names, ``default_terminal`` and
``default_link``, which you can use to set default values for all the
terminals and links in the diagram respectively.

Styles themselves *cannot* reference other styles, i.e. the program
ignores the ``style`` attribute in style definitions.

``groups``
----------

The ``groups`` section may be used to attach attributes to link
groups.  Since links in the same group may collapse on one another, it
is usually desirable for all the links in one group to share the same
attributes.  In the example that follows, all links are drawn in blue:

.. code-block:: yaml

   groups:
     water:
       stroke: blue
       stroke_width: 4.0
   links:
     - start: a
       end: b
       group: water
     - start: c
       end: d
       group: water

A group definition may contain references to named styles.  Note that
creating an entry in the ``groups`` section is not necessary for the
grouping of the links; a common ``group`` name in each link definition
is sufficient.
