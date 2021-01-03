Diagram definition file
=======================

Orthogram uses YAML for its input file format.  Of course, YAML being
a superset of JSON, you can use JSON if you prefer so.  The top-level
structure must be a YAML mapping; the following keys are recognized,
each one containing a different category of definitions:

* ``diagram``
* ``terminals``
* ``rows``
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
     font_weight: bold

The following diagram attributes are of particular significance:

``collapse_links``
  If you set this to ``true``, collinear segments of links belonging
  to the same ``group`` will collapse into a single segment.  This may
  help reduce the clutter, though it depends on the application.  Try
  it out and see.

``stretch``
  By default, the diagram resizes itself to fill the element that
  contains it.  Set this attribute to ``false`` to make the browser
  render the diagram in its original dimensions.

``terminals``
-------------

The ``terminals`` section contains mappings between terminal names and
terminal definitions.  You must have at least a couple of terminals to
produce a meaningful diagram.  Here is an example:

.. code-block:: yaml

   terminals:
     a:
       label: A terminal
     b:
       label: Another terminal
       stroke: blue

If you want a label with more than one line of text, use the newline
character in the string.  Even better, you can use the YAML literal
style:

.. code-block:: yaml

   terminals:

     single-line:
       label: A single line label

     multi-with-newlines:
       label: Two lines separated by\na newline character

     multi-with-newlines-again:
       label: |-
         You can also use
         YAML literal style

Note that if the label of a terminal is not defined, the name of the
terminal is used as a label instead.

``rows``
--------

The ``rows`` section of the diagram definition file is used to arrange
the terminals in the layout grid.  It is essential; terminals that
have not been placed in the grid are not drawn at all.

The ``rows`` structure is a sequence of row definitions.  Each row
definition contains a sequence of terminal names.  You can use an
empty string between the terminal names to leave an empty spot in the
row.  Here is an example:

.. code-block:: yaml

   terminals:
     a:
     b:
     c:
   rows:
     - pins: [a]
     - pins: [b, "", c]

Note that the ``pins`` key is necessary.  Row definitions do not have
any attributes, though this may change in the future.

A terminal can have many pins in multiple rows as long as the area
they occupy in the grid is rectangular.  This way you can draw
terminals that span multiple diagram rows or columns.  The following
example contains valid arrangements:

.. code-block:: yaml

   rows:
     - pins: [a, b , b , c, c]
     - pins: [a, "", "", c, c]

However, the program will reject the following invalid arrangements:

.. code-block:: yaml

   # These are wrong!  Terminal 'a' has a gap; terminal 'b' is
   # L-shaped.
   rows:
     - pins: [a , "", a , b, ""]
     - pins: ["", "", "", b, b ]

``links``
---------

The ``links`` section defines the connections between the terminals.
It is a sequence of link definitions. Each link must declare the names
of the ``start`` and ``end`` terminals, as well as any
:ref:`Attributes` appropriate for links.  Note that the terminals must
have at least one pin placed before making a connection. Here is an
example:

.. code-block:: yaml

   terminals:
     a: {label: First terminal}
     b: {label: Second terminal}
     c: {label: Third terminal}
   rows:
     - pins: [a,  b]
     - pins: ["", c]
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

Of particular interest is the ``drawing_priority`` attribute.  Links
with a higher priority number are drawn over links with a lower
priority.  Since the intersection of links cannot typically be avoided
in complex diagrams, it is advised that you draw intersecting links
with a different ``stroke`` color to make obvious that the links are
not connected at the intersection points.  The ``drawing_priority``
lets you draw sets of links as layers on top of each other, giving a
more consistent look to your diagram.

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
named styles that can be referred to by the terminals, links and
groups.  Each style definition consists of attribute key-value pairs.
For example, the following two terminals are drawn in the same color:

.. code-block:: yaml

   terminals:
     a:
       style: reddish
     b:
       style: reddish
   rows:
     - pins: [a, b]
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
