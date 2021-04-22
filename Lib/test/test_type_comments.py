import ast
import sys
import unittest
from test import support

funcdef = "def foo():\n    # type: () -> int\n    pass\n\ndef bar():  # type: () -> None\n    pass\n"
asyncdef = "async def foo():\n    # type: () -> int\n    return await bar()\n\nasync def bar():  # type: () -> int\n    return await bar()\n"
asyncvar = "async = 12\nawait = 13\n"
asynccomp = "async def foo(xs):\n    [x async for x in xs]\n"
matmul = "a = b @ c\n"
fstring = 'a = 42\nf"{a}"\n'
underscorednumber = "a = 42_42_42\n"
redundantdef = "def foo():  # type: () -> int\n    # type: () -> str\n    return ''\n"
nonasciidef = "def foo():\n    # type: () -> àçčéñt\n    pass\n"
forstmt = "for a in []:  # type: int\n    pass\n"
withstmt = "with context() as a:  # type: int\n    pass\n"
vardecl = "a = 0  # type: int\n"
ignores = "def foo():\n    pass  # type: ignore\n\ndef bar():\n    x = 1  # type: ignore\n\ndef baz():\n    pass  # type: ignore[excuse]\n    pass  # type: ignore=excuse\n    pass  # type: ignore [excuse]\n    x = 1  # type: ignore whatever\n"
longargs = "def fa(\n    a = 1,  # type: A\n):\n    pass\n\ndef fa(\n    a = 1  # type: A\n):\n    pass\n\ndef fa(\n    a = 1,  # type: A\n    /\n):\n    pass\n\ndef fab(\n    a,  # type: A\n    b,  # type: B\n):\n    pass\n\ndef fab(\n    a,  # type: A\n    /,\n    b,  # type: B\n):\n    pass\n\ndef fab(\n    a,  # type: A\n    b   # type: B\n):\n    pass\n\ndef fv(\n    *v,  # type: V\n):\n    pass\n\ndef fv(\n    *v  # type: V\n):\n    pass\n\ndef fk(\n    **k,  # type: K\n):\n    pass\n\ndef fk(\n    **k  # type: K\n):\n    pass\n\ndef fvk(\n    *v,  # type: V\n    **k,  # type: K\n):\n    pass\n\ndef fvk(\n    *v,  # type: V\n    **k  # type: K\n):\n    pass\n\ndef fav(\n    a,  # type: A\n    *v,  # type: V\n):\n    pass\n\ndef fav(\n    a,  # type: A\n    /,\n    *v,  # type: V\n):\n    pass\n\ndef fav(\n    a,  # type: A\n    *v  # type: V\n):\n    pass\n\ndef fak(\n    a,  # type: A\n    **k,  # type: K\n):\n    pass\n\ndef fak(\n    a,  # type: A\n    /,\n    **k,  # type: K\n):\n    pass\n\ndef fak(\n    a,  # type: A\n    **k  # type: K\n):\n    pass\n\ndef favk(\n    a,  # type: A\n    *v,  # type: V\n    **k,  # type: K\n):\n    pass\n\ndef favk(\n    a,  # type: A\n    /,\n    *v,  # type: V\n    **k,  # type: K\n):\n    pass\n\ndef favk(\n    a,  # type: A\n    *v,  # type: V\n    **k  # type: K\n):\n    pass\n"


class TypeCommentTests(unittest.TestCase):
    lowest = 4
    highest = sys.version_info[1]

    def parse(self, source, feature_version=highest):
        return ast.parse(source, type_comments=True, feature_version=feature_version)

    def parse_all(self, source, minver=lowest, maxver=highest, expected_regex=""):
        for version in range(self.lowest, (self.highest + 1)):
            feature_version = (3, version)
            if minver <= version <= maxver:
                try:
                    (yield self.parse(source, feature_version))
                except SyntaxError as err:
                    raise SyntaxError(
                        (str(err) + f" feature_version={feature_version}")
                    )
            else:
                with self.assertRaisesRegex(
                    SyntaxError,
                    expected_regex,
                    msg=f"feature_version={feature_version}",
                ):
                    self.parse(source, feature_version)

    def classic_parse(self, source):
        return ast.parse(source)

    def test_funcdef(self):
        for tree in self.parse_all(funcdef):
            self.assertEqual(tree.body[0].type_comment, "() -> int")
            self.assertEqual(tree.body[1].type_comment, "() -> None")
        tree = self.classic_parse(funcdef)
        self.assertEqual(tree.body[0].type_comment, None)
        self.assertEqual(tree.body[1].type_comment, None)

    def test_asyncdef(self):
        for tree in self.parse_all(asyncdef, minver=5):
            self.assertEqual(tree.body[0].type_comment, "() -> int")
            self.assertEqual(tree.body[1].type_comment, "() -> int")
        tree = self.classic_parse(asyncdef)
        self.assertEqual(tree.body[0].type_comment, None)
        self.assertEqual(tree.body[1].type_comment, None)

    def test_asyncvar(self):
        for tree in self.parse_all(asyncvar, maxver=6):
            pass

    def test_asynccomp(self):
        for tree in self.parse_all(asynccomp, minver=6):
            pass

    def test_matmul(self):
        for tree in self.parse_all(matmul, minver=5):
            pass

    def test_fstring(self):
        for tree in self.parse_all(fstring, minver=6):
            pass

    def test_underscorednumber(self):
        for tree in self.parse_all(underscorednumber, minver=6):
            pass

    def test_redundantdef(self):
        for tree in self.parse_all(
            redundantdef,
            maxver=0,
            expected_regex="^Cannot have two type comments on def",
        ):
            pass

    def test_nonasciidef(self):
        for tree in self.parse_all(nonasciidef):
            self.assertEqual(tree.body[0].type_comment, "() -> àçčéñt")

    def test_forstmt(self):
        for tree in self.parse_all(forstmt):
            self.assertEqual(tree.body[0].type_comment, "int")
        tree = self.classic_parse(forstmt)
        self.assertEqual(tree.body[0].type_comment, None)

    def test_withstmt(self):
        for tree in self.parse_all(withstmt):
            self.assertEqual(tree.body[0].type_comment, "int")
        tree = self.classic_parse(withstmt)
        self.assertEqual(tree.body[0].type_comment, None)

    def test_vardecl(self):
        for tree in self.parse_all(vardecl):
            self.assertEqual(tree.body[0].type_comment, "int")
        tree = self.classic_parse(vardecl)
        self.assertEqual(tree.body[0].type_comment, None)

    def test_ignores(self):
        for tree in self.parse_all(ignores):
            self.assertEqual(
                [(ti.lineno, ti.tag) for ti in tree.type_ignores],
                [
                    (2, ""),
                    (5, ""),
                    (8, "[excuse]"),
                    (9, "=excuse"),
                    (10, " [excuse]"),
                    (11, " whatever"),
                ],
            )
        tree = self.classic_parse(ignores)
        self.assertEqual(tree.type_ignores, [])

    def test_longargs(self):
        for tree in self.parse_all(longargs):
            for t in tree.body:
                todo = set(t.name[1:])
                self.assertEqual(
                    (len(t.args.args) + len(t.args.posonlyargs)),
                    ((len(todo) - bool(t.args.vararg)) - bool(t.args.kwarg)),
                )
                self.assertTrue(t.name.startswith("f"), t.name)
                for (index, c) in enumerate(t.name[1:]):
                    todo.remove(c)
                    if c == "v":
                        arg = t.args.vararg
                    elif c == "k":
                        arg = t.args.kwarg
                    else:
                        assert (
                            0
                            <= (ord(c) - ord("a"))
                            < len((t.args.posonlyargs + t.args.args))
                        )
                        if index < len(t.args.posonlyargs):
                            arg = t.args.posonlyargs[(ord(c) - ord("a"))]
                        else:
                            arg = t.args.args[
                                ((ord(c) - ord("a")) - len(t.args.posonlyargs))
                            ]
                    self.assertEqual(arg.arg, c)
                    self.assertEqual(arg.type_comment, arg.arg.upper())
                assert not todo
        tree = self.classic_parse(longargs)
        for t in tree.body:
            for arg in t.args.args + [t.args.vararg, t.args.kwarg]:
                if arg is not None:
                    self.assertIsNone(
                        arg.type_comment,
                        ("%s(%s:%r)" % (t.name, arg.arg, arg.type_comment)),
                    )

    def test_inappropriate_type_comments(self):
        "Tests for inappropriately-placed type comments.\n\n        These should be silently ignored with type comments off,\n        but raise SyntaxError with type comments on.\n\n        This is not meant to be exhaustive.\n        "

        def check_both_ways(source):
            ast.parse(source, type_comments=False)
            for tree in self.parse_all(source, maxver=0):
                pass

        check_both_ways("pass  # type: int\n")
        check_both_ways("foo()  # type: int\n")
        check_both_ways("x += 1  # type: int\n")
        check_both_ways("while True:  # type: int\n  continue\n")
        check_both_ways("while True:\n  continue  # type: int\n")
        check_both_ways("try:  # type: int\n  pass\nfinally:\n  pass\n")
        check_both_ways("try:\n  pass\nfinally:  # type: int\n  pass\n")
        check_both_ways("pass  # type: ignorewhatever\n")
        check_both_ways("pass  # type: ignoreé\n")

    def test_func_type_input(self):
        def parse_func_type_input(source):
            return ast.parse(source, "<unknown>", "func_type")

        tree = parse_func_type_input("() -> int")
        self.assertEqual(tree.argtypes, [])
        self.assertEqual(tree.returns.id, "int")
        tree = parse_func_type_input("(int) -> List[str]")
        self.assertEqual(len(tree.argtypes), 1)
        arg = tree.argtypes[0]
        self.assertEqual(arg.id, "int")
        self.assertEqual(tree.returns.value.id, "List")
        self.assertEqual(tree.returns.slice.id, "str")
        tree = parse_func_type_input("(int, *str, **Any) -> float")
        self.assertEqual(tree.argtypes[0].id, "int")
        self.assertEqual(tree.argtypes[1].id, "str")
        self.assertEqual(tree.argtypes[2].id, "Any")
        self.assertEqual(tree.returns.id, "float")
        tree = parse_func_type_input("(*int) -> None")
        self.assertEqual(tree.argtypes[0].id, "int")
        tree = parse_func_type_input("(**int) -> None")
        self.assertEqual(tree.argtypes[0].id, "int")
        tree = parse_func_type_input("(*int, **str) -> None")
        self.assertEqual(tree.argtypes[0].id, "int")
        self.assertEqual(tree.argtypes[1].id, "str")
        with self.assertRaises(SyntaxError):
            tree = parse_func_type_input("(int, *str, *Any) -> float")
        with self.assertRaises(SyntaxError):
            tree = parse_func_type_input("(int, **str, Any) -> float")
        with self.assertRaises(SyntaxError):
            tree = parse_func_type_input("(**int, **str) -> float")


if __name__ == "__main__":
    unittest.main()
