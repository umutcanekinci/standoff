"""Local override: build CPython 3.12 instead of p4a's default 3.14.2.

This is the NEWEST Python that builds here: p4a pins Cython 0.29.x, whose
generated C for pygame-ce calls `_PyLong_AsByteArray` with 5 args. Python 3.13
changed that function to 6 args (added `with_exceptions`), so 3.13 AND 3.14 fail
to compile pygame; 3.12 still has the 5-arg signature. p4a's recipe supports 3.12
(its apply_patches adds the >=11 ctypes patch, not the 3.14-only patches).

hostpython3 must match this exact version (p4a enforces it) — see
recipes/hostpython3/__init__.py.
"""

from pythonforandroid.recipes.python3 import Python3Recipe


class Python312Recipe(Python3Recipe):
    version = "3.12.7"


recipe = Python312Recipe()
