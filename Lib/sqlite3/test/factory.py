import unittest
import sqlite3 as sqlite
from collections.abc import Sequence


class MyConnection(sqlite.Connection):
    def __init__(self, *args, **kwargs):
        sqlite.Connection.__init__(self, *args, **kwargs)


def dict_factory(cursor, row):
    d = {}
    for (idx, col) in enumerate(cursor.description):
        d[col[0]] = row[idx]
    return d


class MyCursor(sqlite.Cursor):
    def __init__(self, *args, **kwargs):
        sqlite.Cursor.__init__(self, *args, **kwargs)
        self.row_factory = dict_factory


class ConnectionFactoryTests(unittest.TestCase):
    def setUp(self):
        self.con = sqlite.connect(":memory:", factory=MyConnection)

    def tearDown(self):
        self.con.close()

    def test_is_instance(self):
        self.assertIsInstance(self.con, MyConnection)


class CursorFactoryTests(unittest.TestCase):
    def setUp(self):
        self.con = sqlite.connect(":memory:")

    def tearDown(self):
        self.con.close()

    def test_is_instance(self):
        cur = self.con.cursor()
        self.assertIsInstance(cur, sqlite.Cursor)
        cur = self.con.cursor(MyCursor)
        self.assertIsInstance(cur, MyCursor)
        cur = self.con.cursor(factory=(lambda con: MyCursor(con)))
        self.assertIsInstance(cur, MyCursor)

    def test_invalid_factory(self):
        self.assertRaises(TypeError, self.con.cursor, None)
        self.assertRaises(TypeError, self.con.cursor, (lambda: None))
        self.assertRaises(TypeError, self.con.cursor, (lambda con: None))


class RowFactoryTestsBackwardsCompat(unittest.TestCase):
    def setUp(self):
        self.con = sqlite.connect(":memory:")

    def test_is_produced_by_factory(self):
        cur = self.con.cursor(factory=MyCursor)
        cur.execute("select 4+5 as foo")
        row = cur.fetchone()
        self.assertIsInstance(row, dict)
        cur.close()

    def tearDown(self):
        self.con.close()


class RowFactoryTests(unittest.TestCase):
    def setUp(self):
        self.con = sqlite.connect(":memory:")

    def test_custom_factory(self):
        self.con.row_factory = lambda cur, row: list(row)
        row = self.con.execute("select 1, 2").fetchone()
        self.assertIsInstance(row, list)

    def test_sqlite_row_index(self):
        self.con.row_factory = sqlite.Row
        row = self.con.execute("select 1 as a_1, 2 as b").fetchone()
        self.assertIsInstance(row, sqlite.Row)
        self.assertEqual(row["a_1"], 1, "by name: wrong result for column 'a_1'")
        self.assertEqual(row["b"], 2, "by name: wrong result for column 'b'")
        self.assertEqual(row["A_1"], 1, "by name: wrong result for column 'A_1'")
        self.assertEqual(row["B"], 2, "by name: wrong result for column 'B'")
        self.assertEqual(row[0], 1, "by index: wrong result for column 0")
        self.assertEqual(row[1], 2, "by index: wrong result for column 1")
        self.assertEqual(row[(-1)], 2, "by index: wrong result for column -1")
        self.assertEqual(row[(-2)], 1, "by index: wrong result for column -2")
        with self.assertRaises(IndexError):
            row["c"]
        with self.assertRaises(IndexError):
            row["a_\x11"]
        with self.assertRaises(IndexError):
            row["a\x7f1"]
        with self.assertRaises(IndexError):
            row[2]
        with self.assertRaises(IndexError):
            row[(-3)]
        with self.assertRaises(IndexError):
            row[(2 ** 1000)]

    def test_sqlite_row_index_unicode(self):
        self.con.row_factory = sqlite.Row
        row = self.con.execute("select 1 as ÿ").fetchone()
        self.assertEqual(row["ÿ"], 1)
        with self.assertRaises(IndexError):
            row["Ÿ"]
        with self.assertRaises(IndexError):
            row["ß"]

    def test_sqlite_row_slice(self):
        self.con.row_factory = sqlite.Row
        row = self.con.execute("select 1, 2, 3, 4").fetchone()
        self.assertEqual(row[0:0], ())
        self.assertEqual(row[0:1], (1,))
        self.assertEqual(row[1:3], (2, 3))
        self.assertEqual(row[3:1], ())
        self.assertEqual(row[1:], (2, 3, 4))
        self.assertEqual(row[:3], (1, 2, 3))
        self.assertEqual(row[(-2):(-1)], (3,))
        self.assertEqual(row[(-2):], (3, 4))
        self.assertEqual(row[0:4:2], (1, 3))
        self.assertEqual(row[3:0:(-2)], (4, 2))

    def test_sqlite_row_iter(self):
        "Checks if the row object is iterable"
        self.con.row_factory = sqlite.Row
        row = self.con.execute("select 1 as a, 2 as b").fetchone()
        for col in row:
            pass

    def test_sqlite_row_as_tuple(self):
        "Checks if the row object can be converted to a tuple"
        self.con.row_factory = sqlite.Row
        row = self.con.execute("select 1 as a, 2 as b").fetchone()
        t = tuple(row)
        self.assertEqual(t, (row["a"], row["b"]))

    def test_sqlite_row_as_dict(self):
        "Checks if the row object can be correctly converted to a dictionary"
        self.con.row_factory = sqlite.Row
        row = self.con.execute("select 1 as a, 2 as b").fetchone()
        d = dict(row)
        self.assertEqual(d["a"], row["a"])
        self.assertEqual(d["b"], row["b"])

    def test_sqlite_row_hash_cmp(self):
        "Checks if the row object compares and hashes correctly"
        self.con.row_factory = sqlite.Row
        row_1 = self.con.execute("select 1 as a, 2 as b").fetchone()
        row_2 = self.con.execute("select 1 as a, 2 as b").fetchone()
        row_3 = self.con.execute("select 1 as a, 3 as b").fetchone()
        row_4 = self.con.execute("select 1 as b, 2 as a").fetchone()
        row_5 = self.con.execute("select 2 as b, 1 as a").fetchone()
        self.assertTrue((row_1 == row_1))
        self.assertTrue((row_1 == row_2))
        self.assertFalse((row_1 == row_3))
        self.assertFalse((row_1 == row_4))
        self.assertFalse((row_1 == row_5))
        self.assertFalse((row_1 == object()))
        self.assertFalse((row_1 != row_1))
        self.assertFalse((row_1 != row_2))
        self.assertTrue((row_1 != row_3))
        self.assertTrue((row_1 != row_4))
        self.assertTrue((row_1 != row_5))
        self.assertTrue((row_1 != object()))
        with self.assertRaises(TypeError):
            (row_1 > row_2)
        with self.assertRaises(TypeError):
            (row_1 < row_2)
        with self.assertRaises(TypeError):
            (row_1 >= row_2)
        with self.assertRaises(TypeError):
            (row_1 <= row_2)
        self.assertEqual(hash(row_1), hash(row_2))

    def test_sqlite_row_as_sequence(self):
        " Checks if the row object can act like a sequence "
        self.con.row_factory = sqlite.Row
        row = self.con.execute("select 1 as a, 2 as b").fetchone()
        as_tuple = tuple(row)
        self.assertEqual(list(reversed(row)), list(reversed(as_tuple)))
        self.assertIsInstance(row, Sequence)

    def test_fake_cursor_class(self):
        class FakeCursor(str):
            __class__ = sqlite.Cursor

        self.con.row_factory = sqlite.Row
        self.assertRaises(TypeError, self.con.cursor, FakeCursor)
        self.assertRaises(TypeError, sqlite.Row, FakeCursor(), ())

    def tearDown(self):
        self.con.close()


class TextFactoryTests(unittest.TestCase):
    def setUp(self):
        self.con = sqlite.connect(":memory:")

    def test_unicode(self):
        austria = "Österreich"
        row = self.con.execute("select ?", (austria,)).fetchone()
        self.assertEqual(type(row[0]), str, "type of row[0] must be unicode")

    def test_string(self):
        self.con.text_factory = bytes
        austria = "Österreich"
        row = self.con.execute("select ?", (austria,)).fetchone()
        self.assertEqual(type(row[0]), bytes, "type of row[0] must be bytes")
        self.assertEqual(
            row[0], austria.encode("utf-8"), "column must equal original data in UTF-8"
        )

    def test_custom(self):
        self.con.text_factory = lambda x: str(x, "utf-8", "ignore")
        austria = "Österreich"
        row = self.con.execute("select ?", (austria,)).fetchone()
        self.assertEqual(type(row[0]), str, "type of row[0] must be unicode")
        self.assertTrue(row[0].endswith("reich"), "column must contain original data")

    def test_optimized_unicode(self):
        with self.assertWarns(DeprecationWarning) as cm:
            self.con.text_factory = sqlite.OptimizedUnicode
        self.assertIn("factory.py", cm.filename)
        austria = "Österreich"
        germany = "Deutchland"
        a_row = self.con.execute("select ?", (austria,)).fetchone()
        d_row = self.con.execute("select ?", (germany,)).fetchone()
        self.assertEqual(type(a_row[0]), str, "type of non-ASCII row must be str")
        self.assertEqual(type(d_row[0]), str, "type of ASCII-only row must be str")

    def tearDown(self):
        self.con.close()


class TextFactoryTestsWithEmbeddedZeroBytes(unittest.TestCase):
    def setUp(self):
        self.con = sqlite.connect(":memory:")
        self.con.execute("create table test (value text)")
        self.con.execute("insert into test (value) values (?)", ("a\x00b",))

    def test_string(self):
        row = self.con.execute("select value from test").fetchone()
        self.assertIs(type(row[0]), str)
        self.assertEqual(row[0], "a\x00b")

    def test_bytes(self):
        self.con.text_factory = bytes
        row = self.con.execute("select value from test").fetchone()
        self.assertIs(type(row[0]), bytes)
        self.assertEqual(row[0], b"a\x00b")

    def test_bytearray(self):
        self.con.text_factory = bytearray
        row = self.con.execute("select value from test").fetchone()
        self.assertIs(type(row[0]), bytearray)
        self.assertEqual(row[0], b"a\x00b")

    def test_custom(self):
        self.con.text_factory = lambda x: x
        row = self.con.execute("select value from test").fetchone()
        self.assertIs(type(row[0]), bytes)
        self.assertEqual(row[0], b"a\x00b")

    def tearDown(self):
        self.con.close()


def suite():
    tests = [
        ConnectionFactoryTests,
        CursorFactoryTests,
        RowFactoryTests,
        RowFactoryTestsBackwardsCompat,
        TextFactoryTests,
        TextFactoryTestsWithEmbeddedZeroBytes,
    ]
    return unittest.TestSuite(
        [unittest.TestLoader().loadTestsFromTestCase(t) for t in tests]
    )


def test():
    runner = unittest.TextTestRunner()
    runner.run(suite())


if __name__ == "__main__":
    test()
