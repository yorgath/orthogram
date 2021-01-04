Release history
===============

0.1.0 (2020-12-09)
------------------

* First release.
* Important functionality already in place.

0.1.1 (2020-12-10)
------------------

* API breaking change: renamed :py:func:`convert_ddf()` public
  function to the arguably more user friendly :py:func:`translate()`.

* Added the ``arrow_aspect`` and ``arrow_base`` attributes.

* Fixed bug when ``buffer_width`` is not set.

* Updated the documentation to reflect the changes and correct a few
  errors; made the stability warning a bit less scary.

* Added the scripts.

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

0.2.1 (2020-12-15)
------------------

* Enforced the UTF-8 character encoding for the definition file.

0.2.2 (2020-12-16)
------------------

* Enabled multiple style references in definition files.
* Made debug switch compatible with Python 3.8.

0.3.0 (2021-01-03)
------------------

* Made compatible with Python 3.7.
* Replaced igraph with NetworkX to ease installation.
* Moved documentation to Read the Docs.

0.4.0 (????-??-??)
------------------

* Breaking change: Removed ``column_margin`` and ``row_margin``
  diagram attributes.  Added ``margin_*`` terminal attributes.

* Breaking change: Replaced ``padding`` diagram attribute with
  ``padding_*`` attributes.

* Breaking change: Renamed ``start_bias`` to ``bias_start`` and
  ``end_bias`` to ``bias_end``.

* Breaking change: Got rid of the ``pins`` key in row definitions.

* Added autogeneration of terminals.

* Made diagram center on the drawing area.
