"Tests for scripts in the Tools directory.\n\nThis file contains extremely basic regression tests for the scripts found in\nthe Tools directory of a Python checkout or tarball which don't have separate\ntests of their own.\n"
import os
import sys
import unittest
from test.support import import_helper
from test.test_tools import scriptsdir, import_tool, skip_if_missing

skip_if_missing()


class TestSundryScripts(unittest.TestCase):
    allowlist = ["reindent", "pdeps", "gprof2html", "md5sum"]
    denylist = ["make_ctype"]
    windows_only = ["win_add2path"]
    other = ["analyze_dxp", "2to3"]
    skiplist = ((denylist + allowlist) + windows_only) + other

    def test_sundry(self):
        old_modules = import_helper.modules_setup()
        try:
            for fn in os.listdir(scriptsdir):
                if not fn.endswith(".py"):
                    continue
                name = fn[:(-3)]
                if name in self.skiplist:
                    continue
                import_tool(name)
        finally:
            import_helper.modules_cleanup(*old_modules)

    @unittest.skipIf((sys.platform != "win32"), "Windows-only test")
    def test_sundry_windows(self):
        for name in self.windows_only:
            import_tool(name)

    def test_analyze_dxp_import(self):
        if hasattr(sys, "getdxp"):
            import_tool("analyze_dxp")
        else:
            with self.assertRaises(RuntimeError):
                import_tool("analyze_dxp")


if __name__ == "__main__":
    unittest.main()
