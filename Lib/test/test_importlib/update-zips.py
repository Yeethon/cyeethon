"\nGenerate the zip test data files.\n\nRun to build the tests/zipdataNN/ziptestdata.zip files from\nfiles in tests/dataNN.\n\nReplaces the file with the working copy, but does commit anything\nto the source repo.\n"
import contextlib
import os
import pathlib
import zipfile


def main():
    "\n    >>> from unittest import mock\n    >>> monkeypatch = getfixture('monkeypatch')\n    >>> monkeypatch.setattr(zipfile, 'ZipFile', mock.MagicMock())\n    >>> print(); main()  # print workaround for bpo-32509\n    <BLANKLINE>\n    ...data01... -> ziptestdata/...\n    ...\n    ...data02... -> ziptestdata/...\n    ...\n    "
    suffixes = ("01", "02")
    tuple(map(generate, suffixes))


def generate(suffix):
    root = pathlib.Path(__file__).parent.relative_to(os.getcwd())
    zfpath = root / f"zipdata{suffix}/ziptestdata.zip"
    with zipfile.ZipFile(zfpath, "w") as zf:
        for (src, rel) in walk((root / f"data{suffix}")):
            dst = "ziptestdata" / pathlib.PurePosixPath(rel.as_posix())
            print(src, "->", dst)
            zf.write(src, dst)


def walk(datapath):
    for (dirpath, dirnames, filenames) in os.walk(datapath):
        with contextlib.suppress(KeyError):
            dirnames.remove("__pycache__")
        for filename in filenames:
            res = pathlib.Path(dirpath) / filename
            rel = res.relative_to(datapath)
            (yield (res, rel))


((__name__ == "__main__") and main())
