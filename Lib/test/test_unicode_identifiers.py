import unittest


class PEP3131Test(unittest.TestCase):
    def test_valid(self):
        class T:
            ä = 1
            μ = 2
            蟒 = 3
            x󠄀 = 4

        self.assertEqual(getattr(T, "ä"), 1)
        self.assertEqual(getattr(T, "μ"), 2)
        self.assertEqual(getattr(T, "蟒"), 3)
        self.assertEqual(getattr(T, "x󠄀"), 4)

    def test_non_bmp_normalized(self):
        Unicode = 1
        self.assertIn("Unicode", dir())

    def test_invalid(self):
        try:
            from test import badsyntax_3131
        except SyntaxError as err:
            self.assertEqual(
                str(err), "invalid character '€' (U+20AC) (badsyntax_3131.py, line 2)"
            )
            self.assertEqual(err.lineno, 2)
            self.assertEqual(err.offset, 1)
        else:
            self.fail("expected exception didn't occur")


if __name__ == "__main__":
    unittest.main()
