Hello, world
============

Start the text editor of your choice and type in the following lines
of YAML:

.. code-block:: yaml

   rows:
     - [a]
     - ["", b]
   blocks:
     a:
       label: Hello
     b:
       label: world
   connections:
     - start: a
       end: b

Save it as ``hello.yaml`` and run:

.. code-block:: console

   $ python -m orthogram hello.yaml

This should create a ``hello.svg`` file in the same directory.
