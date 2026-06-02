"""Local override: build CPython 3.12 instead of p4a's default 3.14.2.

This is the NEWEST Python that builds here: p4a pins Cython 0.29.x, whose
generated C for pygame-ce calls `_PyLong_AsByteArray` with 5 args. Python 3.13
changed that function to 6 args (added `with_exceptions`), so 3.13 AND 3.14 fail
to compile pygame; 3.12 still has the 5-arg signature. p4a's recipe supports 3.12
(its apply_patches adds the >=11 ctypes patch, not the 3.14-only patches).

hostpython3 must match this exact version (p4a enforces it) — see
recipes/hostpython3/__init__.py.
"""

import glob
import subprocess
from os.path import join

from pythonforandroid.recipes.python3 import Python3Recipe


class Python312Recipe(Python3Recipe):
    version = "3.12.7"

    def create_python_bundle(self, dirn, arch):
        # NB: the base method returns the site-packages dir, which the bootstrap
        # passes to fry_eggs() — so we must return it too, not None.
        site_packages_dir = super().create_python_bundle(dirn, arch)
        # CPython's Android build does NOT link the stdlib extension modules
        # (math.so, zlib.so, _socket.so, ...) against libpython, so each carries
        # undefined symbols (PyExc_ValueError, ...). On desktop Linux those resolve
        # from the globally-loaded interpreter; Android's linker is strict and
        # refuses — `dlopen failed: cannot locate symbol "PyExc_ValueError"
        # referenced by .../math.cpython-312.so` — which aborts the app on the
        # first `import math`. It also breaks zlib, so a DEFLATE-compressed
        # stdlib.zip can't even bootstrap ("failed to get the Python codec of the
        # filesystem encoding"). p4a links these correctly for its default Python
        # 3.14; the gap is a side effect of pinning 3.12. Add libpython to each
        # module's DT_NEEDED so the linker binds them to the loaded interpreter.
        # (pygame and the other pip-built .so already link libpython via the
        # recipe build env, so only the bundled stdlib modules need this.)
        soname = "libpython{}.so".format(self.link_version)
        for so in glob.glob(join(dirn, "modules", "*.so")):
            subprocess.check_call(["patchelf", "--add-needed", soname, so])
        return site_packages_dir


recipe = Python312Recipe()
