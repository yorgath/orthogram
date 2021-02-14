Installation
============

You must have Python 3.7 or newer installed in your system.  Run the
following command to install package ``orthogram`` from PyPI:

.. code-block:: console

   $ python -m pip install orthogram

Note that Orthogram depends on ``pycairo``, which provides Python
bindings to the Cairo graphics library.  On Windows systems you should
have no trouble with the installation, since PyPI offers a binary
package for this OS.  On Unix systems, however, you must have the
Cairo package installed in your system, including headers, as well as
the compiler tools necessary for the build.  See the `Getting
Started`_ guide in the ``pycairo`` documentation for further
instructions.

.. _Getting Started:
   https://pycairo.readthedocs.io/en/latest/getting_started.html
