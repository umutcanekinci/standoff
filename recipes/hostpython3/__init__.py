"""Local override: host CPython 3.12, to match the target python3 override.

p4a hard-requires hostpython3.version == python3.version, so keep this in lockstep
with recipes/python3/__init__.py.
"""

from pythonforandroid.recipes.hostpython3 import HostPython3Recipe


class HostPython312Recipe(HostPython3Recipe):
    version = "3.12.7"


recipe = HostPython312Recipe()
