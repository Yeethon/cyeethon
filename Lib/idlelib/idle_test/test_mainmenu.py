"Test mainmenu, coverage 100%."
from idlelib import mainmenu
import re
import unittest


class MainMenuTest(unittest.TestCase):
    def test_menudefs(self):
        actual = [item[0] for item in mainmenu.menudefs]
        expect = [
            "file",
            "edit",
            "format",
            "run",
            "shell",
            "debug",
            "options",
            "window",
            "help",
        ]
        self.assertEqual(actual, expect)

    def test_default_keydefs(self):
        self.assertGreaterEqual(len(mainmenu.default_keydefs), 50)

    def test_tcl_indexes(self):
        for (menu, pattern) in (
            ("debug", ".*tack.*iewer"),
            ("options", ".*ode.*ontext"),
            ("options", ".*ine.*umbers"),
        ):
            with self.subTest(menu=menu, pattern=pattern):
                for menutup in mainmenu.menudefs:
                    if menutup[0] == menu:
                        break
                else:
                    self.assertTrue(0, f"{menu} not in menudefs")
                self.assertTrue(
                    any(
                        (
                            re.search(pattern, menuitem[0])
                            for menuitem in menutup[1]
                            if (menuitem is not None)
                        )
                    ),
                    f"{pattern} not in {menu}",
                )


if __name__ == "__main__":
    unittest.main(verbosity=2)
