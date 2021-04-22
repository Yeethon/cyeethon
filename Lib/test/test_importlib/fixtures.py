import os
import sys
import shutil
import pathlib
import tempfile
import textwrap
import contextlib
from test.support.os_helper import FS_NONASCII
from typing import Dict, Union


@contextlib.contextmanager
def tempdir():
    tmpdir = tempfile.mkdtemp()
    try:
        (yield pathlib.Path(tmpdir))
    finally:
        shutil.rmtree(tmpdir)


@contextlib.contextmanager
def save_cwd():
    orig = os.getcwd()
    try:
        (yield)
    finally:
        os.chdir(orig)


@contextlib.contextmanager
def tempdir_as_cwd():
    with tempdir() as tmp:
        with save_cwd():
            os.chdir(str(tmp))
            (yield tmp)


@contextlib.contextmanager
def install_finder(finder):
    sys.meta_path.append(finder)
    try:
        (yield)
    finally:
        sys.meta_path.remove(finder)


class Fixtures:
    def setUp(self):
        self.fixtures = contextlib.ExitStack()
        self.addCleanup(self.fixtures.close)


class SiteDir(Fixtures):
    def setUp(self):
        super(SiteDir, self).setUp()
        self.site_dir = self.fixtures.enter_context(tempdir())


class OnSysPath(Fixtures):
    @staticmethod
    @contextlib.contextmanager
    def add_sys_path(dir):
        sys.path[:0] = [str(dir)]
        try:
            (yield)
        finally:
            sys.path.remove(str(dir))

    def setUp(self):
        super(OnSysPath, self).setUp()
        self.fixtures.enter_context(self.add_sys_path(self.site_dir))


FilesDef = Dict[(str, Union[(Dict[(str, Union[(Dict[(str, str)], str)])], str)])]


class DistInfoPkg(OnSysPath, SiteDir):
    files: FilesDef = {
        "distinfo_pkg-1.0.0.dist-info": {
            "METADATA": "\n                Name: distinfo-pkg\n                Author: Steven Ma\n                Version: 1.0.0\n                Requires-Dist: wheel >= 1.0\n                Requires-Dist: pytest; extra == 'test'\n                ",
            "RECORD": "mod.py,sha256=abc,20\n",
            "entry_points.txt": "\n                [entries]\n                main = mod:main\n                ns:sub = mod:main\n            ",
        },
        "mod.py": '\n            def main():\n                print("hello world")\n            ',
    }

    def setUp(self):
        super(DistInfoPkg, self).setUp()
        build_files(DistInfoPkg.files, self.site_dir)


class DistInfoPkgWithDot(OnSysPath, SiteDir):
    files: FilesDef = {
        "pkg_dot-1.0.0.dist-info": {
            "METADATA": "\n                Name: pkg.dot\n                Version: 1.0.0\n                "
        }
    }

    def setUp(self):
        super(DistInfoPkgWithDot, self).setUp()
        build_files(DistInfoPkgWithDot.files, self.site_dir)


class DistInfoPkgWithDotLegacy(OnSysPath, SiteDir):
    files: FilesDef = {
        "pkg.dot-1.0.0.dist-info": {
            "METADATA": "\n                Name: pkg.dot\n                Version: 1.0.0\n                "
        },
        "pkg.lot.egg-info": {
            "METADATA": "\n                Name: pkg.lot\n                Version: 1.0.0\n                "
        },
    }

    def setUp(self):
        super(DistInfoPkgWithDotLegacy, self).setUp()
        build_files(DistInfoPkgWithDotLegacy.files, self.site_dir)


class DistInfoPkgOffPath(SiteDir):
    def setUp(self):
        super(DistInfoPkgOffPath, self).setUp()
        build_files(DistInfoPkg.files, self.site_dir)


class EggInfoPkg(OnSysPath, SiteDir):
    files: FilesDef = {
        "egginfo_pkg.egg-info": {
            "PKG-INFO": "\n                Name: egginfo-pkg\n                Author: Steven Ma\n                License: Unknown\n                Version: 1.0.0\n                Classifier: Intended Audience :: Developers\n                Classifier: Topic :: Software Development :: Libraries\n                ",
            "SOURCES.txt": "\n                mod.py\n                egginfo_pkg.egg-info/top_level.txt\n            ",
            "entry_points.txt": "\n                [entries]\n                main = mod:main\n            ",
            "requires.txt": '\n                wheel >= 1.0; python_version >= "2.7"\n                [test]\n                pytest\n            ',
            "top_level.txt": "mod\n",
        },
        "mod.py": '\n            def main():\n                print("hello world")\n            ',
    }

    def setUp(self):
        super(EggInfoPkg, self).setUp()
        build_files(EggInfoPkg.files, prefix=self.site_dir)


class EggInfoFile(OnSysPath, SiteDir):
    files: FilesDef = {
        "egginfo_file.egg-info": "\n            Metadata-Version: 1.0\n            Name: egginfo_file\n            Version: 0.1\n            Summary: An example package\n            Home-page: www.example.com\n            Author: Eric Haffa-Vee\n            Author-email: eric@example.coms\n            License: UNKNOWN\n            Description: UNKNOWN\n            Platform: UNKNOWN\n            "
    }

    def setUp(self):
        super(EggInfoFile, self).setUp()
        build_files(EggInfoFile.files, prefix=self.site_dir)


class LocalPackage:
    files: FilesDef = {
        "setup.py": '\n            import setuptools\n            setuptools.setup(name="local-pkg", version="2.0.1")\n            '
    }

    def setUp(self):
        self.fixtures = contextlib.ExitStack()
        self.addCleanup(self.fixtures.close)
        self.fixtures.enter_context(tempdir_as_cwd())
        build_files(self.files)


def build_files(file_defs, prefix=pathlib.Path()):
    'Build a set of files/directories, as described by the\n\n    file_defs dictionary.  Each key/value pair in the dictionary is\n    interpreted as a filename/contents pair.  If the contents value is a\n    dictionary, a directory is created, and the dictionary interpreted\n    as the files within it, recursively.\n\n    For example:\n\n    {"README.txt": "A README file",\n     "foo": {\n        "__init__.py": "",\n        "bar": {\n            "__init__.py": "",\n        },\n        "baz.py": "# Some code",\n     }\n    }\n    '
    for (name, contents) in file_defs.items():
        full_name = prefix / name
        if isinstance(contents, dict):
            full_name.mkdir()
            build_files(contents, prefix=full_name)
        elif isinstance(contents, bytes):
            with full_name.open("wb") as f:
                f.write(contents)
        else:
            with full_name.open("w", encoding="utf-8") as f:
                f.write(DALS(contents))


class FileBuilder:
    def unicode_filename(self):
        return FS_NONASCII or self.skip("File system does not support non-ascii.")


def DALS(str):
    "Dedent and left-strip"
    return textwrap.dedent(str).lstrip()


class NullFinder:
    def find_module(self, name):
        pass
