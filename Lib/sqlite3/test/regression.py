import datetime
import unittest
import sqlite3 as sqlite
import weakref
import functools
from test import support


class RegressionTests(unittest.TestCase):
    def setUp(self):
        self.con = sqlite.connect(":memory:")

    def tearDown(self):
        self.con.close()

    def test_pragma_user_version(self):
        cur = self.con.cursor()
        cur.execute("pragma user_version")

    def test_pragma_schema_version(self):
        con = sqlite.connect(":memory:", detect_types=sqlite.PARSE_COLNAMES)
        try:
            cur = self.con.cursor()
            cur.execute("pragma schema_version")
        finally:
            cur.close()
            con.close()

    def test_statement_reset(self):
        con = sqlite.connect(":memory:", cached_statements=5)
        cursors = [con.cursor() for x in range(5)]
        cursors[0].execute("create table test(x)")
        for i in range(10):
            cursors[0].executemany(
                "insert into test(x) values (?)", [(x,) for x in range(10)]
            )
        for i in range(5):
            cursors[i].execute(((" " * i) + "select x from test"))
        con.rollback()

    def test_column_name_with_spaces(self):
        cur = self.con.cursor()
        cur.execute('select 1 as "foo bar [datetime]"')
        self.assertEqual(cur.description[0][0], "foo bar [datetime]")
        cur.execute('select 1 as "foo baz"')
        self.assertEqual(cur.description[0][0], "foo baz")

    def test_statement_finalization_on_close_db(self):
        con = sqlite.connect(":memory:")
        cursors = []
        for i in range(105):
            cur = con.cursor()
            cursors.append(cur)
            cur.execute(("select 1 x union select " + str(i)))
        con.close()

    def test_on_conflict_rollback(self):
        con = sqlite.connect(":memory:")
        con.execute("create table foo(x, unique(x) on conflict rollback)")
        con.execute("insert into foo(x) values (1)")
        try:
            con.execute("insert into foo(x) values (1)")
        except sqlite.DatabaseError:
            pass
        con.execute("insert into foo(x) values (2)")
        try:
            con.commit()
        except sqlite.OperationalError:
            self.fail("pysqlite knew nothing about the implicit ROLLBACK")

    def test_workaround_for_buggy_sqlite_transfer_bindings(self):
        "\n        pysqlite would crash with older SQLite versions unless\n        a workaround is implemented.\n        "
        self.con.execute("create table foo(bar)")
        self.con.execute("drop table foo")
        self.con.execute("create table foo(bar)")

    def test_empty_statement(self):
        '\n        pysqlite used to segfault with SQLite versions 3.5.x. These return NULL\n        for "no-operation" statements\n        '
        self.con.execute("")

    def test_type_map_usage(self):
        "\n        pysqlite until 2.4.1 did not rebuild the row_cast_map when recompiling\n        a statement. This test exhibits the problem.\n        "
        SELECT = "select * from foo"
        con = sqlite.connect(":memory:", detect_types=sqlite.PARSE_DECLTYPES)
        con.execute("create table foo(bar timestamp)")
        con.execute("insert into foo(bar) values (?)", (datetime.datetime.now(),))
        con.execute(SELECT)
        con.execute("drop table foo")
        con.execute("create table foo(bar integer)")
        con.execute("insert into foo(bar) values (5)")
        con.execute(SELECT)

    def test_bind_mutating_list(self):
        class X:
            def __conform__(self, protocol):
                parameters.clear()
                return "..."

        parameters = [X(), 0]
        con = sqlite.connect(":memory:", detect_types=sqlite.PARSE_DECLTYPES)
        con.execute("create table foo(bar X, baz integer)")
        with self.assertRaises(IndexError):
            con.execute("insert into foo(bar, baz) values (?, ?)", parameters)

    def test_error_msg_decode_error(self):
        with self.assertRaises(sqlite.OperationalError) as cm:
            self.con.execute(
                "select 'xxx' || ? || 'yyy' colname", (bytes(bytearray([250])),)
            ).fetchone()
        msg = "Could not decode to UTF-8 column 'colname' with text 'xxx"
        self.assertIn(msg, str(cm.exception))

    def test_register_adapter(self):
        "\n        See issue 3312.\n        "
        self.assertRaises(TypeError, sqlite.register_adapter, {}, None)

    def test_set_isolation_level(self):
        class CustomStr(str):
            def upper(self):
                return None

            def __del__(self):
                con.isolation_level = ""

        con = sqlite.connect(":memory:")
        con.isolation_level = None
        for level in ("", "DEFERRED", "IMMEDIATE", "EXCLUSIVE"):
            with self.subTest(level=level):
                con.isolation_level = level
                con.isolation_level = level.lower()
                con.isolation_level = level.capitalize()
                con.isolation_level = CustomStr(level)
        con.isolation_level = None
        con.isolation_level = "DEFERRED"
        pairs = [
            (1, TypeError),
            (b"", TypeError),
            ("abc", ValueError),
            ("IMMEDIATE\x00EXCLUSIVE", ValueError),
            ("é", ValueError),
        ]
        for (value, exc) in pairs:
            with self.subTest(level=value):
                with self.assertRaises(exc):
                    con.isolation_level = value
                self.assertEqual(con.isolation_level, "DEFERRED")

    def test_cursor_constructor_call_check(self):
        "\n        Verifies that cursor methods check whether base class __init__ was\n        called.\n        "

        class Cursor(sqlite.Cursor):
            def __init__(self, con):
                pass

        con = sqlite.connect(":memory:")
        cur = Cursor(con)
        with self.assertRaises(sqlite.ProgrammingError):
            cur.execute("select 4+5").fetchall()
        with self.assertRaisesRegex(
            sqlite.ProgrammingError, "^Base Cursor\\.__init__ not called\\.$"
        ):
            cur.close()

    def test_str_subclass(self):
        "\n        The Python 3.0 port of the module didn't cope with values of subclasses of str.\n        "

        class MyStr(str):
            pass

        self.con.execute("select ?", (MyStr("abc"),))

    def test_connection_constructor_call_check(self):
        "\n        Verifies that connection methods check whether base class __init__ was\n        called.\n        "

        class Connection(sqlite.Connection):
            def __init__(self, name):
                pass

        con = Connection(":memory:")
        with self.assertRaises(sqlite.ProgrammingError):
            cur = con.cursor()

    def test_cursor_registration(self):
        "\n        Verifies that subclassed cursor classes are correctly registered with\n        the connection object, too.  (fetch-across-rollback problem)\n        "

        class Connection(sqlite.Connection):
            def cursor(self):
                return Cursor(self)

        class Cursor(sqlite.Cursor):
            def __init__(self, con):
                sqlite.Cursor.__init__(self, con)

        con = Connection(":memory:")
        cur = con.cursor()
        cur.execute("create table foo(x)")
        cur.executemany("insert into foo(x) values (?)", [(3,), (4,), (5,)])
        cur.execute("select x from foo")
        con.rollback()
        with self.assertRaises(sqlite.InterfaceError):
            cur.fetchall()

    def test_auto_commit(self):
        "\n        Verifies that creating a connection in autocommit mode works.\n        2.5.3 introduced a regression so that these could no longer\n        be created.\n        "
        con = sqlite.connect(":memory:", isolation_level=None)

    def test_pragma_autocommit(self):
        "\n        Verifies that running a PRAGMA statement that does an autocommit does\n        work. This did not work in 2.5.3/2.5.4.\n        "
        cur = self.con.cursor()
        cur.execute("create table foo(bar)")
        cur.execute("insert into foo(bar) values (5)")
        cur.execute("pragma page_size")
        row = cur.fetchone()

    def test_connection_call(self):
        "\n        Call a connection with a non-string SQL request: check error handling\n        of the statement constructor.\n        "
        self.assertRaises(TypeError, self.con, 1)

    def test_collation(self):
        def collation_cb(a, b):
            return 1

        self.assertRaises(
            sqlite.ProgrammingError, self.con.create_collation, "\udc80", collation_cb
        )

    def test_recursive_cursor_use(self):
        "\n        http://bugs.python.org/issue10811\n\n        Recursively using a cursor, such as when reusing it from a generator led to segfaults.\n        Now we catch recursive cursor usage and raise a ProgrammingError.\n        "
        con = sqlite.connect(":memory:")
        cur = con.cursor()
        cur.execute("create table a (bar)")
        cur.execute("create table b (baz)")

        def foo():
            cur.execute("insert into a (bar) values (?)", (1,))
            (yield 1)

        with self.assertRaises(sqlite.ProgrammingError):
            cur.executemany("insert into b (baz) values (?)", ((i,) for i in foo()))

    def test_convert_timestamp_microsecond_padding(self):
        '\n        http://bugs.python.org/issue14720\n\n        The microsecond parsing of convert_timestamp() should pad with zeros,\n        since the microsecond string "456" actually represents "456000".\n        '
        con = sqlite.connect(":memory:", detect_types=sqlite.PARSE_DECLTYPES)
        cur = con.cursor()
        cur.execute("CREATE TABLE t (x TIMESTAMP)")
        cur.execute("INSERT INTO t (x) VALUES ('2012-04-04 15:06:00.456')")
        cur.execute("INSERT INTO t (x) VALUES ('2012-04-04 15:06:00.123456789')")
        cur.execute("SELECT * FROM t")
        values = [x[0] for x in cur.fetchall()]
        self.assertEqual(
            values,
            [
                datetime.datetime(2012, 4, 4, 15, 6, 0, 456000),
                datetime.datetime(2012, 4, 4, 15, 6, 0, 123456),
            ],
        )

    def test_invalid_isolation_level_type(self):
        self.assertRaises(TypeError, sqlite.connect, ":memory:", isolation_level=123)

    def test_null_character(self):
        con = sqlite.connect(":memory:")
        self.assertRaises(ValueError, con, "\x00select 1")
        self.assertRaises(ValueError, con, "select 1\x00")
        cur = con.cursor()
        self.assertRaises(ValueError, cur.execute, " \x00select 2")
        self.assertRaises(ValueError, cur.execute, "select 2\x00")

    def test_commit_cursor_reset(self):
        "\n        Connection.commit() did reset cursors, which made sqlite3\n        to return rows multiple times when fetched from cursors\n        after commit. See issues 10513 and 23129 for details.\n        "
        con = sqlite.connect(":memory:")
        con.executescript(
            "\n        create table t(c);\n        create table t2(c);\n        insert into t values(0);\n        insert into t values(1);\n        insert into t values(2);\n        "
        )
        self.assertEqual(con.isolation_level, "")
        counter = 0
        for (i, row) in enumerate(con.execute("select c from t")):
            with self.subTest(i=i, row=row):
                con.execute("insert into t2(c) values (?)", (i,))
                con.commit()
                if counter == 0:
                    self.assertEqual(row[0], 0)
                elif counter == 1:
                    self.assertEqual(row[0], 1)
                elif counter == 2:
                    self.assertEqual(row[0], 2)
                counter += 1
        self.assertEqual(counter, 3, "should have returned exactly three rows")

    def test_bpo31770(self):
        "\n        The interpreter shouldn't crash in case Cursor.__init__() is called\n        more than once.\n        "

        def callback(*args):
            pass

        con = sqlite.connect(":memory:")
        cur = sqlite.Cursor(con)
        ref = weakref.ref(cur, callback)
        cur.__init__(con)
        del cur
        del ref
        support.gc_collect()

    def test_del_isolation_level_segfault(self):
        with self.assertRaises(AttributeError):
            del self.con.isolation_level

    def test_bpo37347(self):
        class Printer:
            def log(self, *args):
                return sqlite.SQLITE_OK

        for method in [
            self.con.set_trace_callback,
            functools.partial(self.con.set_progress_handler, n=1),
            self.con.set_authorizer,
        ]:
            printer_instance = Printer()
            method(printer_instance.log)
            method(printer_instance.log)
            self.con.execute("select 1")
            method(None)

    def test_return_empty_bytestring(self):
        cur = self.con.execute("select X''")
        val = cur.fetchone()[0]
        self.assertEqual(val, b"")


def suite():
    tests = [RegressionTests]
    return unittest.TestSuite(
        [unittest.TestLoader().loadTestsFromTestCase(t) for t in tests]
    )


def test():
    runner = unittest.TextTestRunner()
    runner.run(suite())


if __name__ == "__main__":
    test()
