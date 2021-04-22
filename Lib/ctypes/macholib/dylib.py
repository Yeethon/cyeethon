"\nGeneric dylib path manipulation\n"
import re

__all__ = ["dylib_info"]
DYLIB_RE = re.compile(
    "(?x)\n(?P<location>^.*)(?:^|/)\n(?P<name>\n    (?P<shortname>\\w+?)\n    (?:\\.(?P<version>[^._]+))?\n    (?:_(?P<suffix>[^._]+))?\n    \\.dylib$\n)\n"
)


def dylib_info(filename):
    "\n    A dylib name can take one of the following four forms:\n        Location/Name.SomeVersion_Suffix.dylib\n        Location/Name.SomeVersion.dylib\n        Location/Name_Suffix.dylib\n        Location/Name.dylib\n\n    returns None if not found or a mapping equivalent to:\n        dict(\n            location='Location',\n            name='Name.SomeVersion_Suffix.dylib',\n            shortname='Name',\n            version='SomeVersion',\n            suffix='Suffix',\n        )\n\n    Note that SomeVersion and Suffix are optional and may be None\n    if not present.\n    "
    is_dylib = DYLIB_RE.match(filename)
    if not is_dylib:
        return None
    return is_dylib.groupdict()


def test_dylib_info():
    def d(location=None, name=None, shortname=None, version=None, suffix=None):
        return dict(
            location=location,
            name=name,
            shortname=shortname,
            version=version,
            suffix=suffix,
        )

    assert dylib_info("completely/invalid") is None
    assert dylib_info("completely/invalide_debug") is None
    assert dylib_info("P/Foo.dylib") == d("P", "Foo.dylib", "Foo")
    assert dylib_info("P/Foo_debug.dylib") == d(
        "P", "Foo_debug.dylib", "Foo", suffix="debug"
    )
    assert dylib_info("P/Foo.A.dylib") == d("P", "Foo.A.dylib", "Foo", "A")
    assert dylib_info("P/Foo_debug.A.dylib") == d(
        "P", "Foo_debug.A.dylib", "Foo_debug", "A"
    )
    assert dylib_info("P/Foo.A_debug.dylib") == d(
        "P", "Foo.A_debug.dylib", "Foo", "A", "debug"
    )


if __name__ == "__main__":
    test_dylib_info()
