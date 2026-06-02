"""Local python-for-android recipe override: build pygame-ce, not stale pygame.

p4a's bundled `pygame` recipe pins pygame 2.1.0 (2021), whose C sources still
`#include "longintrepr.h"` — a header removed in Python 3.12 — so it cannot
compile against the Python 3.14 that this p4a builds. The game targets pygame-ce
anyway, so we point the same recipe at pygame-ce 2.5.7: it supports Python 3.14,
the offending `_sdl2/sdl2.c` is gone, and it still ships the legacy
`buildconfig/Setup.Android.SDL2.in` template the base recipe formats. We subclass
the built-in recipe so all the SDL2 / image / mixer / ttf / jpeg / png build
wiring is reused unchanged — only the source version/URL differs.

Wired in via `p4a.local_recipes = ./recipes` in buildozer.spec; the requirement
stays `pygame` (the recipe name), which now resolves to this override.
"""

from os.path import exists

from pythonforandroid.logger import info, shprint
from pythonforandroid.recipes.pygame import Pygame2Recipe
from pythonforandroid.toolchain import current_directory


class PygameCERecipe(Pygame2Recipe):
    # Build pygame-ce 2.5.7 (3.12-compatible, has Setup.Android.SDL2.in) instead of
    # p4a's stale pygame 2.1.0. See recipes/python3/__init__.py for why we target
    # Python 3.12.
    version = "2.5.7"
    url = "https://github.com/pygame-community/pygame-ce/archive/refs/tags/{version}.tar.gz"

    # pygame-ce 2.5.7's setup.py imports Cython to (re)generate its .pyx sources,
    # so Cython must be importable by the cross-compile hostpython. p4a installs
    # only setuptools there by default; add Cython 3.x (the version pygame-ce uses;
    # it emits PY_VERSION_HEX-guarded C that compiles fine against Python 3.12).
    # wheel is needed too: with the meson backend stripped (see prebuild_arch),
    # the install step builds a wheel via setuptools' legacy backend.
    hostpython_prerequisites = ["setuptools", "wheel", "cython<3.1"]

    def prebuild_arch(self, arch):
        super().prebuild_arch(arch)
        # pygame-ce's setup.py monkeypatches the compiler's spawn() to inject x86
        # AVX2 flags. That override (a) touches distutils/Compiler internals and
        # (b) is x86-only — it keys off the x86_64 BUILD host and would wrongly add
        # -mavx2 to our ARM target build. Disable it so the stock spawn is used.
        with current_directory(self.get_build_dir(arch.arch)):
            with open("setup.py") as handle:
                source = handle.read()
            patched = source.replace(
                "distutils.ccompiler.CCompiler.spawn = spawn",
                "pass  # AVX2 spawn override disabled for Android cross-compile",
            )
            if patched != source:
                with open("setup.py", "w") as handle:
                    handle.write(patched)

            # Strip the [build-system] table from pyproject.toml so p4a's install
            # step (`pip install .`) falls back to setuptools' legacy setup.py
            # backend — the same setup.py that build_ext already uses — instead of
            # the meson-python backend pygame-ce declares. meson does a *native*
            # build whose cross-compile sanity check fails ("binary or interpreter
            # not executable. Possibly wrong architecture"). The legacy setup.py
            # assembles the full package: the ARM .so files plus the src_py/*.py
            # modules and data files (fonts, icons), which a bare build_ext lacks.
            #
            # We strip only [build-system], NOT the whole file: setup.py imports
            # buildconfig.get_version, which reads [project].version from here.
            self._strip_build_system("pyproject.toml")

    @staticmethod
    def _strip_build_system(path):
        if not exists(path):
            return
        with open(path) as handle:
            lines = handle.readlines()
        out = []
        skipping = False
        for line in lines:
            stripped = line.lstrip()
            if stripped.startswith("["):
                # A table header ends any [build-system] block we were skipping.
                if stripped.startswith("[build-system]"):
                    skipping = True
                    continue
                skipping = False
                out.append(line)
            elif not skipping:
                out.append(line)
        with open(path, "w") as handle:
            handle.writelines(out)

    def install_python_package(self, arch, name=None, env=None, is_dir=True):
        # p4a's base install runs `pip install .` with build isolation, which
        # spins up a fresh venv lacking the setuptools/Cython we put in hostpython
        # (so pygame-ce's setup.py would again abort with "You need cython"). Pass
        # --no-build-isolation so pip builds the wheel in the hostpython env that
        # has those prerequisites, using the cross-compile CC/CFLAGS from
        # get_recipe_env. With pyproject.toml removed (see prebuild_arch) pip uses
        # the legacy setuptools backend and assembles the full pygame package.
        if env is None:
            env = self.get_recipe_env(arch)
        info(
            "Installing {} into site-packages (legacy setup.py, no meson)".format(
                self.name
            )
        )
        with current_directory(self.get_build_dir(arch.arch)):
            shprint(
                self._host_recipe.pip,
                "install",
                ".",
                "--compile",
                "--no-build-isolation",
                "--target",
                self.ctx.get_python_install_dir(arch.arch),
                _env=env,
            )


recipe = PygameCERecipe()
