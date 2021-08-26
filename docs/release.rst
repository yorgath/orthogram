Release history
===============

0.7.0 (2021-08-27)
------------------

* Introduced labels at the start and end of connections.
* Fixed bug: connection label distance was previously applied in half,
  which is now fixed.  Had to halve the default value.  This change
  may affect the appearance of diagrams created with previous versions
  in mind.
* Fixed bug: null connection labels in DDFs are now properly
  recognized.  They were previously rendered as "None".
* Reorganized cases directory.  Added more cases.

0.6.0 (2021-08-04)
------------------

* Made changes that may affect the output of some diagrams, so bumped
  version number appropriately.
* Put connection arrows inside block margins to avoid overlaps.
* Spacing between connections is now increased when necessary to avoid
  overlaps of wide arrow heads.
* Drawing of connection labels now takes into account arrow size to
  avoid label - arrow overlap.
* Added cases to visually check the above.

0.5.5 (2021-07-25)
------------------

* Fixed regression: diagram box and label are now drawn properly.
* Minor updates to loading mechanism and depedencies.
* Reorganized cases and examples; added a couple more cases.

0.5.4 (2021-07-03)
------------------

* Added the ability to include files in DDFs.  Useful for sharing
  styles between diagrams.
* Added the ability to define the diagram layout grid using a CSV
  file.  It is now possible to manipulate the layout using a
  spreadsheet.
* Internal change: using the constraint solver for refinement instead
  of graphs.  Made code much clearer at the cost of a slight
  performance degradation.
* Internal change: refactored code; replaced a few convoluted
  inheritance patterns with composition; added representation strings
  to most objects.

0.5.3 (2021-06-19)
------------------

* Fixed vertex-to-vertex interaction regression.

0.5.2 (2021-05-23)
------------------

* Improved drawing of connections.

0.5.1 (2021-04-30)
------------------

* Added optional constraints to prevent block boxes from growing
  unnecessarily large.

0.5.0 (2021-04-24)
------------------

* Major new feature: connections can now have labels.

* Switched from SVG to PNG output using the cairo graphics library.
  Needed to be able to calculate the dimensions of labels.  Breaking
  DDF and API changes.

* Colors are now sequences of numbers instead of strings.

* Removed the now irrelevant ``stretch`` attribute.

* Added the ``scale`` attribute.

0.4.4 (2021-02-14)
------------------

* Some enumerators needed for attributes were not exposed -- fixed.

* Removed Poetry lock file from version control.

0.4.3 (2021-02-12)
------------------

* Stopped depending on ``dominant-baseline`` SVG attribute; Firefox
  now centers text correctly.

* Minor aesthetic change: replaced empty string with tilde character
  in examples.

* Corrected some errors in the documentation.  Reversed the order of
  releases in the history section.

0.4.2 (2021-01-23)
------------------

* No code changes.
* Corrected command line usage documentation.

0.4.1 (2021-01-23)
------------------

* No code changes.
* Updated depedencies.
* Documentation fixes.

0.4.0 (2021-01-14)
------------------

* Significant breaking changes all around.

* Adopted more mainstream terminology of block diagrams.  "Blocks"
  instead of "terminals", "connections" instead of "links".

* Introduced the ability to define overlapping blocks.

* Eliminated the ``drawing_priority`` attribute.  Drawing order is now
  definition order.

* Content of the ``blocks`` section in the definition file is now a
  sequence instead of a mapping.  Program relies on definition order.

* Replaced ``start_bias`` and ``end_bias`` attributes with
  ``entrances`` and ``exits`` attributes.

* Removed ``column_margin`` and ``row_margin`` diagram attributes.
  Added ``margin_*`` block attributes.

* Replaced ``padding`` diagram attribute with ``padding_*``
  attributes.

* Got rid of the ``pins`` key in row definitions.

* Added autogeneration of blocks.

* Made diagram center in the drawing area.

* Improved the refinement engine.

* Updated the documentation.  Added the Gallery section.

* Added a few more examples.

0.3.0 (2021-01-03)
------------------

* Made compatible with Python 3.7.
* Replaced igraph with NetworkX to ease installation.
* Moved documentation to Read the Docs.

0.2.2 (2020-12-16)
------------------

* Enabled multiple style references in definition files.
* Made debug switch compatible with Python 3.8.

0.2.1 (2020-12-15)
------------------

* Enforced the UTF-8 character encoding for the definition file.

0.2.0 (2020-12-14)
------------------

* Introduced the ability to create shapes spanning multiple rows and
  columns.

* Major API breaking changes: Replaced ``nodes`` with ``terminals``
  and ``pins`` in order to facilitate the expansion of connected
  objects.  Both API and diagram definition files affected.

* Added the ``text_orientation`` attribute.

* Updated the documentation to reflect the changes.  Added the
  acknowledgments and release history sections.

0.1.1 (2020-12-10)
------------------

* API breaking change: renamed :py:func:`convert_ddf()` public
  function to the arguably more user friendly :py:func:`translate()`.

* Added the ``arrow_aspect`` and ``arrow_base`` attributes.

* Fixed bug when ``buffer_width`` is not set.

* Updated the documentation to reflect the changes and correct a few
  errors; made the stability warning a bit less scary.

* Added the scripts.

0.1.0 (2020-12-09)
------------------

* First release.
* Important functionality already in place.
