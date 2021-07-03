Acknowledgements
================

This program depends on the following excellent pieces of software:

* `Python`_: The author's preferred programming language.  Flexible,
  convenient and nice to look at.  Has a library for everything.

* `NetworkX`_: Very comprehensive network analysis library.
  Implemented in pure Python, so easy to install and convenient to
  use.

* `Cassowary`_: Linear constraint solver implemented in pure Python.
  Many of the calculations Orthogram does turn eventually into
  constraint satisfaction problems.

* `Shapely`_: Python interface to the powerful `GEOS`_ geometry
  library.  A bit overkill for the simple geometry manipulations
  Orthogram does, but why reinvent the wheel?

* `pycairo`_: Python interface to the popular `cairo`_ graphics
  library.

* `PyYAML`_: Simple to use, efficient YAML parser.

* `Sphinx`_: The Python documentation generator.

The following programs improved the development experience of the
author a lot:

* `mypy`_: Python static analyzer.  Makes refactoring so much easier.

* `Poetry`_: Great Python package manager.  Also makes publishing to
  PyPI a breeze.

.. _Python: https://python.org
.. _NetworkX: https://networkx.org/
.. _Shapely: https://github.com/Toblerity/Shapely
.. _GEOS: https://trac.osgeo.org/geos
.. _Cassowary: https://github.com/brodderickrodriguez/cassowary
.. _pycairo: https://github.com/pygobject/pycairo
.. _cairo: https://cairographics.org
.. _PyYAML: https://github.com/yaml/pyyaml
.. _Sphinx: https://www.sphinx-doc.org/
.. _Poetry: https://python-poetry.org/
.. _mypy: http://mypy-lang.org/
