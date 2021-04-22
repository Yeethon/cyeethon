"\nProvides .props file.\n"
import os
import sys
from .constants import *

__all__ = ["get_nuspec_layout"]
PYTHON_NUSPEC_NAME = "python.nuspec"
NUSPEC_DATA = {
    "PYTHON_TAG": VER_DOT,
    "PYTHON_VERSION": os.getenv("PYTHON_NUSPEC_VERSION"),
    "FILELIST": '    <file src="**\\*" exclude="python.png" target="tools" />',
    "GIT": sys._git,
}
NUSPEC_PLATFORM_DATA = dict(
    _keys=("PYTHON_BITNESS", "PACKAGENAME", "PACKAGETITLE"),
    win32=("32-bit", "pythonx86", "Python (32-bit)"),
    amd64=("64-bit", "python", "Python"),
    arm32=("ARM", "pythonarm", "Python (ARM)"),
    arm64=("ARM64", "pythonarm64", "Python (ARM64)"),
)
if not NUSPEC_DATA["PYTHON_VERSION"]:
    NUSPEC_DATA["PYTHON_VERSION"] = "{}.{}{}{}".format(
        VER_DOT, VER_MICRO, ("-" if VER_SUFFIX else ""), VER_SUFFIX
    )
FILELIST_WITH_PROPS = '    <file src="**\\*" exclude="python.png;python.props" target="tools" />\n    <file src="python.props" target="build\\native" />'
NUSPEC_TEMPLATE = '<?xml version="1.0"?>\n<package>\n  <metadata>\n    <id>{PACKAGENAME}</id>\n    <title>{PACKAGETITLE}</title>\n    <version>{PYTHON_VERSION}</version>\n    <authors>Python Software Foundation</authors>\n    <license type="file">tools\\LICENSE.txt</license>\n    <projectUrl>https://www.python.org/</projectUrl>\n    <description>Installs {PYTHON_BITNESS} Python for use in build scenarios.</description>\n    <icon>images\\python.png</icon>\n    <iconUrl>https://www.python.org/static/favicon.ico</iconUrl>\n    <tags>python</tags>\n    <repository type="git" url="https://github.com/Python/CPython.git" commit="{GIT[2]}" />\n  </metadata>\n  <files>\n    <file src="python.png" target="images" />\n{FILELIST}\n  </files>\n</package>\n'


def _get_nuspec_data_overrides(ns):
    for (k, v) in zip(NUSPEC_PLATFORM_DATA["_keys"], NUSPEC_PLATFORM_DATA[ns.arch]):
        ev = os.getenv(("PYTHON_NUSPEC_" + k))
        if ev:
            (yield (k, ev))
        (yield (k, v))


def get_nuspec_layout(ns):
    if ns.include_all or ns.include_nuspec:
        data = dict(NUSPEC_DATA)
        for (k, v) in _get_nuspec_data_overrides(ns):
            if not data.get(k):
                data[k] = v
        if ns.include_all or ns.include_props:
            data["FILELIST"] = FILELIST_WITH_PROPS
        nuspec = NUSPEC_TEMPLATE.format_map(data)
        (yield ("python.nuspec", ("python.nuspec", nuspec.encode("utf-8"))))
        (yield ("python.png", (((ns.source / "PC") / "icons") / "logox128.png")))
