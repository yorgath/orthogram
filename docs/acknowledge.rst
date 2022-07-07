Acknowledgements
================

This program depends on the following excellent pieces of software:

* `Python`_: Orthogram is implemented in the Python programming
  language.  This project would probably not exist without Python
  helping along the way with its ease of use and availability of high
  quality libraries.

* `NetworkX`_: Very comprehensive network analysis library.
  Implemented in pure Python, so easy to install and convenient to
  use.  Orthogram utilizes graphs to route the connections around the
  blocks and minimize their overlapping with each other.

* `Cassowary`_: Linear constraint solver implemented in pure Python.
  Orthogram uses this to arrange the elements in the drawing.

* `Shapely`_: Powerful geometry manipulation library based on `GEOS`_.
  A bit overkill for the simple geometry manipulations Orthogram does,
  but why reinvent the wheel?

* `pycairo`_: Python interface to the popular `cairo`_ graphics
  library.  Orthogram uses this to generate image files.

* `PyYAML`_: Simple to use, efficient YAML parser.  Orthogram uses
  this to read the diagram definition files.

* `Sphinx`_: The Python documentation generator.  This documentation
  is built with Sphinx.

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
