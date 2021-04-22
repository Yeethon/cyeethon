import unittest
import sqlite3 as sqlite
from test.support.os_helper import TESTFN, unlink


class CollationTests(unittest.TestCase):
    def test_create_collation_not_string(self):
        con = sqlite.connect(":memory:")
        with self.assertRaises(TypeError):
            con.create_collation(None, (lambda x, y: ((x > y) - (x < y))))

    def test_create_collation_not_callable(self):
        con = sqlite.connect(":memory:")
        with self.assertRaises(TypeError) as cm:
            con.create_collation("X", 42)
        self.assertEqual(str(cm.exception), "parameter must be callable")

    def test_create_collation_not_ascii(self):
        con = sqlite.connect(":memory:")
        with self.assertRaises(sqlite.ProgrammingError):
            con.create_collation("collä", (lambda x, y: ((x > y) - (x < y))))

    def test_create_collation_bad_upper(self):
        class BadUpperStr(str):
            def upper(self):
                return None

        con = sqlite.connect(":memory:")
        mycoll = lambda x, y: (-((x > y) - (x < y)))
        con.create_collation(BadUpperStr("mycoll"), mycoll)
        result = con.execute(
            "\n            select x from (\n            select 'a' as x\n            union\n            select 'b' as x\n            ) order by x collate mycoll\n            "
        ).fetchall()
        self.assertEqual(result[0][0], "b")
        self.assertEqual(result[1][0], "a")

    def test_collation_is_used(self):
        def mycoll(x, y):
            return -((x > y) - (x < y))

        con = sqlite.connect(":memory:")
        con.create_collation("mycoll", mycoll)
        sql = "\n            select x from (\n            select 'a' as x\n            union\n            select 'b' as x\n            union\n            select 'c' as x\n            ) order by x collate mycoll\n            "
        result = con.execute(sql).fetchall()
        self.assertEqual(
            result, [("c",), ("b",), ("a",)], msg="the expected order was not returned"
        )
        con.create_collation("mycoll", None)
        with self.assertRaises(sqlite.OperationalError) as cm:
            result = con.execute(sql).fetchall()
        self.assertEqual(str(cm.exception), "no such collation sequence: mycoll")

    def test_collation_returns_large_integer(self):
        def mycoll(x, y):
            return (-((x > y) - (x < y))) * (2 ** 32)

        con = sqlite.connect(":memory:")
        con.create_collation("mycoll", mycoll)
        sql = "\n            select x from (\n            select 'a' as x\n            union\n            select 'b' as x\n            union\n            select 'c' as x\n            ) order by x collate mycoll\n            "
        result = con.execute(sql).fetchall()
        self.assertEqual(
            result, [("c",), ("b",), ("a",)], msg="the expected order was not returned"
        )

    def test_collation_register_twice(self):
        "\n        Register two different collation functions under the same name.\n        Verify that the last one is actually used.\n        "
        con = sqlite.connect(":memory:")
        con.create_collation("mycoll", (lambda x, y: ((x > y) - (x < y))))
        con.create_collation("mycoll", (lambda x, y: (-((x > y) - (x < y)))))
        result = con.execute(
            "\n            select x from (select 'a' as x union select 'b' as x) order by x collate mycoll\n            "
        ).fetchall()
        self.assertEqual(result[0][0], "b")
        self.assertEqual(result[1][0], "a")

    def test_deregister_collation(self):
        "\n        Register a collation, then deregister it. Make sure an error is raised if we try\n        to use it.\n        "
        con = sqlite.connect(":memory:")
        con.create_collation("mycoll", (lambda x, y: ((x > y) - (x < y))))
        con.create_collation("mycoll", None)
        with self.assertRaises(sqlite.OperationalError) as cm:
            con.execute(
                "select 'a' as x union select 'b' as x order by x collate mycoll"
            )
        self.assertEqual(str(cm.exception), "no such collation sequence: mycoll")


class ProgressTests(unittest.TestCase):
    def test_progress_handler_used(self):
        "\n        Test that the progress handler is invoked once it is set.\n        "
        con = sqlite.connect(":memory:")
        progress_calls = []

        def progress():
            progress_calls.append(None)
            return 0

        con.set_progress_handler(progress, 1)
        con.execute("\n            create table foo(a, b)\n            ")
        self.assertTrue(progress_calls)

    def test_opcode_count(self):
        "\n        Test that the opcode argument is respected.\n        "
        con = sqlite.connect(":memory:")
        progress_calls = []

        def progress():
            progress_calls.append(None)
            return 0

        con.set_progress_handler(progress, 1)
        curs = con.cursor()
        curs.execute("\n            create table foo (a, b)\n            ")
        first_count = len(progress_calls)
        progress_calls = []
        con.set_progress_handler(progress, 2)
        curs.execute("\n            create table bar (a, b)\n            ")
        second_count = len(progress_calls)
        self.assertGreaterEqual(first_count, second_count)

    def test_cancel_operation(self):
        "\n        Test that returning a non-zero value stops the operation in progress.\n        "
        con = sqlite.connect(":memory:")

        def progress():
            return 1

        con.set_progress_handler(progress, 1)
        curs = con.cursor()
        self.assertRaises(
            sqlite.OperationalError, curs.execute, "create table bar (a, b)"
        )

    def test_clear_handler(self):
        "\n        Test that setting the progress handler to None clears the previously set handler.\n        "
        con = sqlite.connect(":memory:")
        action = 0

        def progress():
            nonlocal action
            action = 1
            return 0

        con.set_progress_handler(progress, 1)
        con.set_progress_handler(None, 1)
        con.execute("select 1 union select 2 union select 3").fetchall()
        self.assertEqual(action, 0, "progress handler was not cleared")


class TraceCallbackTests(unittest.TestCase):
    def test_trace_callback_used(self):
        "\n        Test that the trace callback is invoked once it is set.\n        "
        con = sqlite.connect(":memory:")
        traced_statements = []

        def trace(statement):
            traced_statements.append(statement)

        con.set_trace_callback(trace)
        con.execute("create table foo(a, b)")
        self.assertTrue(traced_statements)
        self.assertTrue(
            any((("create table foo" in stmt) for stmt in traced_statements))
        )

    def test_clear_trace_callback(self):
        "\n        Test that setting the trace callback to None clears the previously set callback.\n        "
        con = sqlite.connect(":memory:")
        traced_statements = []

        def trace(statement):
            traced_statements.append(statement)

        con.set_trace_callback(trace)
        con.set_trace_callback(None)
        con.execute("create table foo(a, b)")
        self.assertFalse(traced_statements, "trace callback was not cleared")

    def test_unicode_content(self):
        "\n        Test that the statement can contain unicode literals.\n        "
        unicode_value = "öäüÖÄÜß€"
        con = sqlite.connect(":memory:")
        traced_statements = []

        def trace(statement):
            traced_statements.append(statement)

        con.set_trace_callback(trace)
        con.execute("create table foo(x)")
        con.execute(('insert into foo(x) values ("%s")' % unicode_value))
        con.commit()
        self.assertTrue(
            any(((unicode_value in stmt) for stmt in traced_statements)),
            (
                "Unicode data %s garbled in trace callback: %s"
                % (ascii(unicode_value), ", ".join(map(ascii, traced_statements)))
            ),
        )

    def test_trace_callback_content(self):
        traced_statements = []

        def trace(statement):
            traced_statements.append(statement)

        queries = ["create table foo(x)", "insert into foo(x) values(1)"]
        self.addCleanup(unlink, TESTFN)
        con1 = sqlite.connect(TESTFN, isolation_level=None)
        con2 = sqlite.connect(TESTFN)
        con1.set_trace_callback(trace)
        cur = con1.cursor()
        cur.execute(queries[0])
        con2.execute("create table bar(x)")
        cur.execute(queries[1])
        self.assertEqual(traced_statements, queries)


def suite():
    tests = [CollationTests, ProgressTests, TraceCallbackTests]
    return unittest.TestSuite(
        [unittest.TestLoader().loadTestsFromTestCase(t) for t in tests]
    )


def test():
    runner = unittest.TextTestRunner()
    runner.run(suite())


if __name__ == "__main__":
    test()
