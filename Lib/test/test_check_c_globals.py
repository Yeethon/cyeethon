import unittest
import test.test_tools

test.test_tools.skip_if_missing("c-analyzer")
with test.test_tools.imports_under_tool("c-analyzer"):
    from cpython.__main__ import main


class ActualChecks(unittest.TestCase):
    @unittest.skip("activate this once all the globals have been resolved")
    def test_check_c_globals(self):
        try:
            main("check", {})
        except NotImplementedError:
            raise unittest.SkipTest("not supported on this host")


if __name__ == "__main__":
    unittest.main()
