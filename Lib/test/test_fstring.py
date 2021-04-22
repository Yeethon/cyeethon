import ast
import os
import re
import types
import decimal
import unittest
from test.support.os_helper import temp_cwd
from test.support.script_helper import assert_python_failure

a_global = "global variable"


class TestCase(unittest.TestCase):
    def assertAllRaise(self, exception_type, regex, error_strings):
        for str in error_strings:
            with self.subTest(str=str):
                with self.assertRaisesRegex(exception_type, regex):
                    eval(str)

    def test__format__lookup(self):
        class X:
            def __format__(self, spec):
                return "class"

        x = X()
        y = X()
        y.__format__ = types.MethodType((lambda self, spec: "instance"), y)
        self.assertEqual(f"{y}", format(y))
        self.assertEqual(f"{y}", "class")
        self.assertEqual(format(x), format(y))
        self.assertEqual(x.__format__(""), "class")
        self.assertEqual(y.__format__(""), "instance")
        self.assertEqual(type(x).__format__(x, ""), "class")
        self.assertEqual(type(y).__format__(y, ""), "class")

    def test_ast(self):
        class X:
            def __init__(self):
                self.called = False

            def __call__(self):
                self.called = True
                return 4

        x = X()
        expr = "\na = 10\nf'{a * x()}'"
        t = ast.parse(expr)
        c = compile(t, "", "exec")
        self.assertFalse(x.called)
        exec(c)
        self.assertTrue(x.called)

    def test_ast_line_numbers(self):
        expr = "\na = 10\nf'{a * x()}'"
        t = ast.parse(expr)
        self.assertEqual(type(t), ast.Module)
        self.assertEqual(len(t.body), 2)
        self.assertEqual(type(t.body[0]), ast.Assign)
        self.assertEqual(t.body[0].lineno, 2)
        self.assertEqual(type(t.body[1]), ast.Expr)
        self.assertEqual(type(t.body[1].value), ast.JoinedStr)
        self.assertEqual(len(t.body[1].value.values), 1)
        self.assertEqual(type(t.body[1].value.values[0]), ast.FormattedValue)
        self.assertEqual(t.body[1].lineno, 3)
        self.assertEqual(t.body[1].value.lineno, 3)
        self.assertEqual(t.body[1].value.values[0].lineno, 3)
        binop = t.body[1].value.values[0].value
        self.assertEqual(type(binop), ast.BinOp)
        self.assertEqual(type(binop.left), ast.Name)
        self.assertEqual(type(binop.op), ast.Mult)
        self.assertEqual(type(binop.right), ast.Call)
        self.assertEqual(binop.lineno, 3)
        self.assertEqual(binop.left.lineno, 3)
        self.assertEqual(binop.right.lineno, 3)
        self.assertEqual(binop.col_offset, 3)
        self.assertEqual(binop.left.col_offset, 3)
        self.assertEqual(binop.right.col_offset, 7)

    def test_ast_line_numbers_multiple_formattedvalues(self):
        expr = "\nf'no formatted values'\nf'eggs {a * x()} spam {b + y()}'"
        t = ast.parse(expr)
        self.assertEqual(type(t), ast.Module)
        self.assertEqual(len(t.body), 2)
        self.assertEqual(type(t.body[0]), ast.Expr)
        self.assertEqual(type(t.body[0].value), ast.JoinedStr)
        self.assertEqual(t.body[0].lineno, 2)
        self.assertEqual(type(t.body[1]), ast.Expr)
        self.assertEqual(type(t.body[1].value), ast.JoinedStr)
        self.assertEqual(len(t.body[1].value.values), 4)
        self.assertEqual(type(t.body[1].value.values[0]), ast.Constant)
        self.assertEqual(type(t.body[1].value.values[0].value), str)
        self.assertEqual(type(t.body[1].value.values[1]), ast.FormattedValue)
        self.assertEqual(type(t.body[1].value.values[2]), ast.Constant)
        self.assertEqual(type(t.body[1].value.values[2].value), str)
        self.assertEqual(type(t.body[1].value.values[3]), ast.FormattedValue)
        self.assertEqual(t.body[1].lineno, 3)
        self.assertEqual(t.body[1].value.lineno, 3)
        self.assertEqual(t.body[1].value.values[0].lineno, 3)
        self.assertEqual(t.body[1].value.values[1].lineno, 3)
        self.assertEqual(t.body[1].value.values[2].lineno, 3)
        self.assertEqual(t.body[1].value.values[3].lineno, 3)
        binop1 = t.body[1].value.values[1].value
        self.assertEqual(type(binop1), ast.BinOp)
        self.assertEqual(type(binop1.left), ast.Name)
        self.assertEqual(type(binop1.op), ast.Mult)
        self.assertEqual(type(binop1.right), ast.Call)
        self.assertEqual(binop1.lineno, 3)
        self.assertEqual(binop1.left.lineno, 3)
        self.assertEqual(binop1.right.lineno, 3)
        self.assertEqual(binop1.col_offset, 8)
        self.assertEqual(binop1.left.col_offset, 8)
        self.assertEqual(binop1.right.col_offset, 12)
        binop2 = t.body[1].value.values[3].value
        self.assertEqual(type(binop2), ast.BinOp)
        self.assertEqual(type(binop2.left), ast.Name)
        self.assertEqual(type(binop2.op), ast.Add)
        self.assertEqual(type(binop2.right), ast.Call)
        self.assertEqual(binop2.lineno, 3)
        self.assertEqual(binop2.left.lineno, 3)
        self.assertEqual(binop2.right.lineno, 3)
        self.assertEqual(binop2.col_offset, 23)
        self.assertEqual(binop2.left.col_offset, 23)
        self.assertEqual(binop2.right.col_offset, 27)

    def test_ast_line_numbers_nested(self):
        expr = "\na = 10\nf'{a * f\"-{x()}-\"}'"
        t = ast.parse(expr)
        self.assertEqual(type(t), ast.Module)
        self.assertEqual(len(t.body), 2)
        self.assertEqual(type(t.body[0]), ast.Assign)
        self.assertEqual(t.body[0].lineno, 2)
        self.assertEqual(type(t.body[1]), ast.Expr)
        self.assertEqual(type(t.body[1].value), ast.JoinedStr)
        self.assertEqual(len(t.body[1].value.values), 1)
        self.assertEqual(type(t.body[1].value.values[0]), ast.FormattedValue)
        self.assertEqual(t.body[1].lineno, 3)
        self.assertEqual(t.body[1].value.lineno, 3)
        self.assertEqual(t.body[1].value.values[0].lineno, 3)
        binop = t.body[1].value.values[0].value
        self.assertEqual(type(binop), ast.BinOp)
        self.assertEqual(type(binop.left), ast.Name)
        self.assertEqual(type(binop.op), ast.Mult)
        self.assertEqual(type(binop.right), ast.JoinedStr)
        self.assertEqual(binop.lineno, 3)
        self.assertEqual(binop.left.lineno, 3)
        self.assertEqual(binop.right.lineno, 3)
        self.assertEqual(binop.col_offset, 3)
        self.assertEqual(binop.left.col_offset, 3)
        self.assertEqual(binop.right.col_offset, 7)
        self.assertEqual(len(binop.right.values), 3)
        self.assertEqual(type(binop.right.values[0]), ast.Constant)
        self.assertEqual(type(binop.right.values[0].value), str)
        self.assertEqual(type(binop.right.values[1]), ast.FormattedValue)
        self.assertEqual(type(binop.right.values[2]), ast.Constant)
        self.assertEqual(type(binop.right.values[2].value), str)
        self.assertEqual(binop.right.values[0].lineno, 3)
        self.assertEqual(binop.right.values[1].lineno, 3)
        self.assertEqual(binop.right.values[2].lineno, 3)
        call = binop.right.values[1].value
        self.assertEqual(type(call), ast.Call)
        self.assertEqual(call.lineno, 3)
        self.assertEqual(call.col_offset, 11)

    def test_ast_line_numbers_duplicate_expression(self):
        "Duplicate expression\n\n        NOTE: this is currently broken, always sets location of the first\n        expression.\n        "
        expr = "\na = 10\nf'{a * x()} {a * x()} {a * x()}'\n"
        t = ast.parse(expr)
        self.assertEqual(type(t), ast.Module)
        self.assertEqual(len(t.body), 2)
        self.assertEqual(type(t.body[0]), ast.Assign)
        self.assertEqual(t.body[0].lineno, 2)
        self.assertEqual(type(t.body[1]), ast.Expr)
        self.assertEqual(type(t.body[1].value), ast.JoinedStr)
        self.assertEqual(len(t.body[1].value.values), 5)
        self.assertEqual(type(t.body[1].value.values[0]), ast.FormattedValue)
        self.assertEqual(type(t.body[1].value.values[1]), ast.Constant)
        self.assertEqual(type(t.body[1].value.values[1].value), str)
        self.assertEqual(type(t.body[1].value.values[2]), ast.FormattedValue)
        self.assertEqual(type(t.body[1].value.values[3]), ast.Constant)
        self.assertEqual(type(t.body[1].value.values[3].value), str)
        self.assertEqual(type(t.body[1].value.values[4]), ast.FormattedValue)
        self.assertEqual(t.body[1].lineno, 3)
        self.assertEqual(t.body[1].value.lineno, 3)
        self.assertEqual(t.body[1].value.values[0].lineno, 3)
        self.assertEqual(t.body[1].value.values[1].lineno, 3)
        self.assertEqual(t.body[1].value.values[2].lineno, 3)
        self.assertEqual(t.body[1].value.values[3].lineno, 3)
        self.assertEqual(t.body[1].value.values[4].lineno, 3)
        binop = t.body[1].value.values[0].value
        self.assertEqual(type(binop), ast.BinOp)
        self.assertEqual(type(binop.left), ast.Name)
        self.assertEqual(type(binop.op), ast.Mult)
        self.assertEqual(type(binop.right), ast.Call)
        self.assertEqual(binop.lineno, 3)
        self.assertEqual(binop.left.lineno, 3)
        self.assertEqual(binop.right.lineno, 3)
        self.assertEqual(binop.col_offset, 3)
        self.assertEqual(binop.left.col_offset, 3)
        self.assertEqual(binop.right.col_offset, 7)
        binop = t.body[1].value.values[2].value
        self.assertEqual(type(binop), ast.BinOp)
        self.assertEqual(type(binop.left), ast.Name)
        self.assertEqual(type(binop.op), ast.Mult)
        self.assertEqual(type(binop.right), ast.Call)
        self.assertEqual(binop.lineno, 3)
        self.assertEqual(binop.left.lineno, 3)
        self.assertEqual(binop.right.lineno, 3)
        self.assertEqual(binop.col_offset, 3)
        self.assertEqual(binop.left.col_offset, 3)
        self.assertEqual(binop.right.col_offset, 7)
        binop = t.body[1].value.values[4].value
        self.assertEqual(type(binop), ast.BinOp)
        self.assertEqual(type(binop.left), ast.Name)
        self.assertEqual(type(binop.op), ast.Mult)
        self.assertEqual(type(binop.right), ast.Call)
        self.assertEqual(binop.lineno, 3)
        self.assertEqual(binop.left.lineno, 3)
        self.assertEqual(binop.right.lineno, 3)
        self.assertEqual(binop.col_offset, 3)
        self.assertEqual(binop.left.col_offset, 3)
        self.assertEqual(binop.right.col_offset, 7)

    def test_ast_line_numbers_multiline_fstring(self):
        expr = "\na = 10\nf'''\n  {a\n     *\n       x()}\nnon-important content\n'''\n"
        t = ast.parse(expr)
        self.assertEqual(type(t), ast.Module)
        self.assertEqual(len(t.body), 2)
        self.assertEqual(type(t.body[0]), ast.Assign)
        self.assertEqual(t.body[0].lineno, 2)
        self.assertEqual(type(t.body[1]), ast.Expr)
        self.assertEqual(type(t.body[1].value), ast.JoinedStr)
        self.assertEqual(len(t.body[1].value.values), 3)
        self.assertEqual(type(t.body[1].value.values[0]), ast.Constant)
        self.assertEqual(type(t.body[1].value.values[0].value), str)
        self.assertEqual(type(t.body[1].value.values[1]), ast.FormattedValue)
        self.assertEqual(type(t.body[1].value.values[2]), ast.Constant)
        self.assertEqual(type(t.body[1].value.values[2].value), str)
        self.assertEqual(t.body[1].lineno, 3)
        self.assertEqual(t.body[1].value.lineno, 3)
        self.assertEqual(t.body[1].value.values[0].lineno, 3)
        self.assertEqual(t.body[1].value.values[1].lineno, 3)
        self.assertEqual(t.body[1].value.values[2].lineno, 3)
        self.assertEqual(t.body[1].col_offset, 0)
        self.assertEqual(t.body[1].value.col_offset, 0)
        self.assertEqual(t.body[1].value.values[0].col_offset, 0)
        self.assertEqual(t.body[1].value.values[1].col_offset, 0)
        self.assertEqual(t.body[1].value.values[2].col_offset, 0)
        binop = t.body[1].value.values[1].value
        self.assertEqual(type(binop), ast.BinOp)
        self.assertEqual(type(binop.left), ast.Name)
        self.assertEqual(type(binop.op), ast.Mult)
        self.assertEqual(type(binop.right), ast.Call)
        self.assertEqual(binop.lineno, 4)
        self.assertEqual(binop.left.lineno, 4)
        self.assertEqual(binop.right.lineno, 6)
        self.assertEqual(binop.col_offset, 4)
        self.assertEqual(binop.left.col_offset, 4)
        self.assertEqual(binop.right.col_offset, 7)

    def test_ast_line_numbers_with_parentheses(self):
        expr = '\nx = (\n    f" {test(t)}"\n)'
        t = ast.parse(expr)
        self.assertEqual(type(t), ast.Module)
        self.assertEqual(len(t.body), 1)
        call = t.body[0].value.values[1].value
        self.assertEqual(type(call), ast.Call)
        self.assertEqual(call.lineno, 3)
        self.assertEqual(call.end_lineno, 3)
        self.assertEqual(call.col_offset, 8)
        self.assertEqual(call.end_col_offset, 15)
        expr = "\nx = (\n        'PERL_MM_OPT', (\n            f'wat'\n            f'some_string={f(x)} '\n            f'wat'\n        ),\n)\n"
        t = ast.parse(expr)
        self.assertEqual(type(t), ast.Module)
        self.assertEqual(len(t.body), 1)
        fstring = t.body[0].value.elts[1]
        self.assertEqual(type(fstring), ast.JoinedStr)
        self.assertEqual(len(fstring.values), 3)
        (wat1, middle, wat2) = fstring.values
        self.assertEqual(type(wat1), ast.Constant)
        self.assertEqual(wat1.lineno, 4)
        self.assertEqual(wat1.end_lineno, 6)
        self.assertEqual(wat1.col_offset, 12)
        self.assertEqual(wat1.end_col_offset, 18)
        call = middle.value
        self.assertEqual(type(call), ast.Call)
        self.assertEqual(call.lineno, 5)
        self.assertEqual(call.end_lineno, 5)
        self.assertEqual(call.col_offset, 27)
        self.assertEqual(call.end_col_offset, 31)
        self.assertEqual(type(wat2), ast.Constant)
        self.assertEqual(wat2.lineno, 4)
        self.assertEqual(wat2.end_lineno, 6)
        self.assertEqual(wat2.col_offset, 12)
        self.assertEqual(wat2.end_col_offset, 18)

    def test_docstring(self):
        def f():
            f"Not a docstring"

        self.assertIsNone(f.__doc__)

        def g():
            f"Not a docstring"

        self.assertIsNone(g.__doc__)

    def test_literal_eval(self):
        with self.assertRaisesRegex(ValueError, "malformed node or string"):
            ast.literal_eval("f'x'")

    def test_ast_compile_time_concat(self):
        x = [""]
        expr = "x[0] = 'foo' f'{3}'"
        t = ast.parse(expr)
        c = compile(t, "", "exec")
        exec(c)
        self.assertEqual(x[0], "foo3")

    def test_compile_time_concat_errors(self):
        self.assertAllRaise(
            SyntaxError,
            "cannot mix bytes and nonbytes literals",
            ["f'' b''", "b'' f''"],
        )

    def test_literal(self):
        self.assertEqual(f"", "")
        self.assertEqual(f"a", "a")
        self.assertEqual(f" ", " ")

    def test_unterminated_string(self):
        self.assertAllRaise(
            SyntaxError,
            "f-string: unterminated string",
            ["f'{\"x'", "f'{\"x}'", "f'{(\"x'", "f'{(\"x}'"],
        )

    def test_mismatched_parens(self):
        self.assertAllRaise(
            SyntaxError,
            "f-string: closing parenthesis '\\}' does not match opening parenthesis '\\('",
            ["f'{((}'"],
        )
        self.assertAllRaise(
            SyntaxError,
            "f-string: closing parenthesis '\\)' does not match opening parenthesis '\\['",
            ["f'{a[4)}'"],
        )
        self.assertAllRaise(
            SyntaxError,
            "f-string: closing parenthesis '\\]' does not match opening parenthesis '\\('",
            ["f'{a(4]}'"],
        )
        self.assertAllRaise(
            SyntaxError,
            "f-string: closing parenthesis '\\}' does not match opening parenthesis '\\['",
            ["f'{a[4}'"],
        )
        self.assertAllRaise(
            SyntaxError,
            "f-string: closing parenthesis '\\}' does not match opening parenthesis '\\('",
            ["f'{a(4}'"],
        )
        self.assertRaises(SyntaxError, eval, (("f'{" + ("(" * 500)) + "}'"))

    def test_double_braces(self):
        self.assertEqual(f"{{", "{")
        self.assertEqual(f"a{{", "a{")
        self.assertEqual(f"{{b", "{b")
        self.assertEqual(f"a{{b", "a{b")
        self.assertEqual(f"}}", "}")
        self.assertEqual(f"a}}", "a}")
        self.assertEqual(f"}}b", "}b")
        self.assertEqual(f"a}}b", "a}b")
        self.assertEqual(f"{{}}", "{}")
        self.assertEqual(f"a{{}}", "a{}")
        self.assertEqual(f"{{b}}", "{b}")
        self.assertEqual(f"{{}}c", "{}c")
        self.assertEqual(f"a{{b}}", "a{b}")
        self.assertEqual(f"a{{}}c", "a{}c")
        self.assertEqual(f"{{b}}c", "{b}c")
        self.assertEqual(f"a{{b}}c", "a{b}c")
        self.assertEqual(f"{{{10}", "{10")
        self.assertEqual(f"}}{10}", "}10")
        self.assertEqual(f"}}{{{10}", "}{10")
        self.assertEqual(f"}}a{{{10}", "}a{10")
        self.assertEqual(f"{10}{{", "10{")
        self.assertEqual(f"{10}}}", "10}")
        self.assertEqual(f"{10}}}{{", "10}{")
        self.assertEqual(f"{10}}}a{{}}", "10}a{}")
        self.assertEqual(f"{'{{}}'}", "{{}}")
        self.assertAllRaise(TypeError, "unhashable type", ["f'{ {{}} }'"])

    def test_compile_time_concat(self):
        x = "def"
        self.assertEqual(f"abc## {x}ghi", "abc## defghi")
        self.assertEqual(f"abc{x}ghi", "abcdefghi")
        self.assertEqual(f"abc{x}ghi{x:4}", "abcdefghidef ")
        self.assertEqual(f"{{x}}{x}", "{x}def")
        self.assertEqual(f"{{x{x}", "{xdef")
        self.assertEqual(f"{{x}}{x}", "{x}def")
        self.assertEqual(f"{{{{x}}}}{x}", "{{x}}def")
        self.assertEqual(f"{{{{x{x}", "{{xdef")
        self.assertEqual(f"x}}}}{x}", "x}}def")
        self.assertEqual(f"{x}x}}}}", "defx}}")
        self.assertEqual(f"{x}", "def")
        self.assertEqual(f"{x}", "def")
        self.assertEqual(f"{x}", "def")
        self.assertEqual(f"{x}2", "def2")
        self.assertEqual(f"1{x}2", "1def2")
        self.assertEqual(f"1{x}", "1def")
        self.assertEqual(f"{x}-{x}", "def-def")
        self.assertEqual(f"", "")
        self.assertEqual(f"", "")
        self.assertEqual(f"", "")
        self.assertEqual(f"", "")
        self.assertEqual(f"", "")
        self.assertEqual(f"", "")
        self.assertEqual(f"", "")
        self.assertAllRaise(SyntaxError, "f-string: expecting '}'", ["f'{3' f'}'"])

    def test_comments(self):
        d = {"#": "hash"}
        self.assertEqual(f"{'#'}", "#")
        self.assertEqual(f"{d['#']}", "hash")
        self.assertAllRaise(
            SyntaxError,
            "f-string expression part cannot include '#'",
            ["f'{1#}'", "f'{3(#)}'", "f'{#}'"],
        )
        self.assertAllRaise(SyntaxError, "f-string: unmatched '\\)'", ["f'{)#}'"])

    def test_many_expressions(self):
        def build_fstr(n, extra=""):
            return (("f'" + ("{x} " * n)) + extra) + "'"

        x = "X"
        width = 1
        for i in range(250, 260):
            self.assertEqual(eval(build_fstr(i)), ((x + " ") * i))
        self.assertEqual(eval((build_fstr(255) * 256)), ((x + " ") * (255 * 256)))
        s = build_fstr(253, "{x:{width}} ")
        self.assertEqual(eval(s), ((x + " ") * 254))
        s = "f'{1}' 'x' 'y'" * 1024
        self.assertEqual(eval(s), ("1xy" * 1024))

    def test_format_specifier_expressions(self):
        width = 10
        precision = 4
        value = decimal.Decimal("12.34567")
        self.assertEqual(f"result: {value:{width}.{precision}}", "result:      12.35")
        self.assertEqual(f"result: {value:{width!r}.{precision}}", "result:      12.35")
        self.assertEqual(
            f"result: {value:{width:0}.{precision:1}}", "result:      12.35"
        )
        self.assertEqual(
            f"result: {value:{1}{0:0}.{precision:1}}", "result:      12.35"
        )
        self.assertEqual(
            f"result: {value:{1}{0:0}.{precision:1}}", "result:      12.35"
        )
        self.assertEqual(f"{10:#{1}0x}", "       0xa")
        self.assertEqual(f"{10:{'#'}1{0}{'x'}}", "       0xa")
        self.assertEqual(f"{(- 10):-{'#'}1{0}x}", "      -0xa")
        self.assertEqual(f"{(- 10):{'-'}#{1}0{'x'}}", "      -0xa")
        self.assertEqual(f"{10:#{((3 != {4: 5}) and width)}x}", "       0xa")
        self.assertAllRaise(
            SyntaxError, "f-string: expecting '}'", ['f\'{"s"!r{":10"}}\'']
        )
        self.assertAllRaise(SyntaxError, "f-string: invalid syntax", ["f'{4:{/5}}'"])
        self.assertAllRaise(
            SyntaxError,
            "f-string: expressions nested too deeply",
            ["f'result: {value:{width:{0}}.{precision:1}}'"],
        )
        self.assertAllRaise(
            SyntaxError, "f-string: invalid conversion character", ['f\'{"s"!{"r"}}\'']
        )

    def test_side_effect_order(self):
        class X:
            def __init__(self):
                self.i = 0

            def __format__(self, spec):
                self.i += 1
                return str(self.i)

        x = X()
        self.assertEqual(f"{x} {x}", "1 2")

    def test_missing_expression(self):
        self.assertAllRaise(
            SyntaxError,
            "f-string: empty expression not allowed",
            [
                "f'{}'",
                "f'{ }'f' {} '",
                "f'{!r}'",
                "f'{ !r}'",
                "f'{10:{ }}'",
                "f' { } '",
                "f'''{\t\x0c\r\n}'''",
                "f'{!x}'",
                "f'{ !xr}'",
                "f'{!x:}'",
                "f'{!x:a}'",
                "f'{ !xr:}'",
                "f'{ !xr:a}'",
                "f'{!}'",
                "f'{:}'",
                "f'{!'",
                "f'{!s:'",
                "f'{:'",
                "f'{:x'",
            ],
        )
        self.assertAllRaise(
            SyntaxError,
            "invalid non-printable character U\\+00A0",
            ["f'''{\xa0}'''", "\xa0"],
        )

    def test_parens_in_expressions(self):
        self.assertEqual(f"{(3,)}", "(3,)")
        self.assertAllRaise(
            SyntaxError, "f-string: invalid syntax", ["f'{,}'", "f'{,}'"]
        )
        self.assertAllRaise(SyntaxError, "f-string: unmatched '\\)'", ["f'{3)+(4}'"])
        self.assertAllRaise(SyntaxError, "unterminated string literal", ["f'{\n}'"])

    def test_newlines_before_syntax_error(self):
        self.assertAllRaise(
            SyntaxError, "invalid syntax", ["f'{.}'", "\nf'{.}'", "\n\nf'{.}'"]
        )

    def test_backslashes_in_string_part(self):
        self.assertEqual(f"	", "\t")
        self.assertEqual("\\t", "\\t")
        self.assertEqual(f"\t", "\\t")
        self.assertEqual(f"{2}	", "2\t")
        self.assertEqual(f"{2}	{3}", "2\t3")
        self.assertEqual(f"	{3}", "\t3")
        self.assertEqual(f"Δ", "Δ")
        self.assertEqual("\\u0394", "\\u0394")
        self.assertEqual(f"\u0394", "\\u0394")
        self.assertEqual(f"{2}Δ", "2Δ")
        self.assertEqual(f"{2}Δ{3}", "2Δ3")
        self.assertEqual(f"Δ{3}", "Δ3")
        self.assertEqual(f"Δ", "Δ")
        self.assertEqual("\\U00000394", "\\U00000394")
        self.assertEqual(f"\U00000394", "\\U00000394")
        self.assertEqual(f"{2}Δ", "2Δ")
        self.assertEqual(f"{2}Δ{3}", "2Δ3")
        self.assertEqual(f"Δ{3}", "Δ3")
        self.assertEqual(f"Δ", "Δ")
        self.assertEqual(f"{2}Δ", "2Δ")
        self.assertEqual(f"{2}Δ{3}", "2Δ3")
        self.assertEqual(f"Δ{3}", "Δ3")
        self.assertEqual(f"2Δ", "2Δ")
        self.assertEqual(f"2Δ3", "2Δ3")
        self.assertEqual(f"Δ3", "Δ3")
        self.assertEqual(f" ", " ")
        self.assertEqual("\\x20", "\\x20")
        self.assertEqual(f"\x20", "\\x20")
        self.assertEqual(f"{2} ", "2 ")
        self.assertEqual(f"{2} {3}", "2 3")
        self.assertEqual(f" {3}", " 3")
        self.assertEqual(f"2 ", "2 ")
        self.assertEqual(f"2 3", "2 3")
        self.assertEqual(f" 3", " 3")
        with self.assertWarns(DeprecationWarning):
            value = eval("f'\\{6*7}'")
        self.assertEqual(value, "\\42")
        self.assertEqual(f"\{(6 * 7)}", "\\42")
        self.assertEqual(f"\{(6 * 7)}", "\\42")
        AMPERSAND = "spam"
        self.assertEqual(f"&", "&")
        self.assertEqual(f"\N{AMPERSAND}", "\\Nspam")
        self.assertEqual(f"\N{AMPERSAND}", "\\Nspam")
        self.assertEqual(f"\&", "\\&")

    def test_misformed_unicode_character_name(self):
        self.assertAllRaise(
            SyntaxError,
            "\\(unicode error\\) 'unicodeescape' codec can't decode bytes in position .*: malformed \\\\N character escape",
            [
                "f'\\N'",
                "f'\\N{'",
                "f'\\N{GREEK CAPITAL LETTER DELTA'",
                "'\\N'",
                "'\\N{'",
                "'\\N{GREEK CAPITAL LETTER DELTA'",
            ],
        )

    def test_no_backslashes_in_expression_part(self):
        self.assertAllRaise(
            SyntaxError,
            "f-string expression part cannot include a backslash",
            [
                "f'{\\'a\\'}'",
                "f'{\\t3}'",
                "f'{\\}'",
                "rf'{\\'a\\'}'",
                "rf'{\\t3}'",
                "rf'{\\}'",
                "rf'{\"\\N{LEFT CURLY BRACKET}\"}'",
                "f'{\\n}'",
            ],
        )

    def test_no_escapes_for_braces(self):
        "\n        Only literal curly braces begin an expression.\n        "
        self.assertEqual(f"{{1+1}}", "{1+1}")
        self.assertEqual(f"{{1+1", "{1+1")
        self.assertEqual(f"{{1+1", "{1+1")
        self.assertEqual(f"{{1+1}}", "{1+1}")

    def test_newlines_in_expressions(self):
        self.assertEqual(f"{0}", "0")
        self.assertEqual(f"{(3 + 4)}", "7")

    def test_lambda(self):
        x = 5
        self.assertEqual(f"{(lambda y: (x * y))('8')!r}", "'88888'")
        self.assertEqual(f"{(lambda y: (x * y))('8')!r:10}", "'88888'   ")
        self.assertEqual(f"{(lambda y: (x * y))('8'):10}", "88888     ")
        self.assertAllRaise(
            SyntaxError, "f-string: invalid syntax", ["f'{lambda x:x}'"]
        )

    def test_yield(self):
        def fn(y):
            f"y:{(yield (y * 2))}"
            f"{(yield)}"

        g = fn(4)
        self.assertEqual(next(g), 8)
        self.assertEqual(next(g), None)

    def test_yield_send(self):
        def fn(x):
            (yield f"x:{(yield (lambda i: (x * i)))}")

        g = fn(10)
        the_lambda = next(g)
        self.assertEqual(the_lambda(4), 40)
        self.assertEqual(g.send("string"), "x:string")

    def test_expressions_with_triple_quoted_strings(self):
        self.assertEqual(f"{'x'}", "x")
        self.assertEqual(f"""{"eric's"}""", "eric's")
        self.assertEqual(f"""{'xeric"sy'}""", 'xeric"sy')
        self.assertEqual(f"""{'xeric"s'}""", 'xeric"s')
        self.assertEqual(f"""{'eric"sy'}""", 'eric"sy')
        self.assertEqual(f"""{'xeric"sy'}""", 'xeric"sy')
        self.assertEqual(f"""{'xeric"sy'}""", 'xeric"sy')
        self.assertEqual(f"""{'xeric"sy'}""", 'xeric"sy')

    def test_multiple_vars(self):
        x = 98
        y = "abc"
        self.assertEqual(f"{x}{y}", "98abc")
        self.assertEqual(f"X{x}{y}", "X98abc")
        self.assertEqual(f"{x}X{y}", "98Xabc")
        self.assertEqual(f"{x}{y}X", "98abcX")
        self.assertEqual(f"X{x}Y{y}", "X98Yabc")
        self.assertEqual(f"X{x}{y}Y", "X98abcY")
        self.assertEqual(f"{x}X{y}Y", "98XabcY")
        self.assertEqual(f"X{x}Y{y}Z", "X98YabcZ")

    def test_closure(self):
        def outer(x):
            def inner():
                return f"x:{x}"

            return inner

        self.assertEqual(outer("987")(), "x:987")
        self.assertEqual(outer(7)(), "x:7")

    def test_arguments(self):
        y = 2

        def f(x, width):
            return f"x={(x * y):{width}}"

        self.assertEqual(f("foo", 10), "x=foofoo    ")
        x = "bar"
        self.assertEqual(f(10, 10), "x=        20")

    def test_locals(self):
        value = 123
        self.assertEqual(f"v:{value}", "v:123")

    def test_missing_variable(self):
        with self.assertRaises(NameError):
            f"v:{value}"

    def test_missing_format_spec(self):
        class O:
            def __format__(self, spec):
                if not spec:
                    return "*"
                return spec

        self.assertEqual(f"{O():x}", "x")
        self.assertEqual(f"{O()}", "*")
        self.assertEqual(f"{O():}", "*")
        self.assertEqual(f"{3:}", "3")
        self.assertEqual(f"{3!s:}", "3")

    def test_global(self):
        self.assertEqual(f"g:{a_global}", "g:global variable")
        self.assertEqual(f"g:{a_global!r}", "g:'global variable'")
        a_local = "local variable"
        self.assertEqual(
            f"g:{a_global} l:{a_local}", "g:global variable l:local variable"
        )
        self.assertEqual(f"g:{a_global!r}", "g:'global variable'")
        self.assertEqual(
            f"g:{a_global} l:{a_local!r}", "g:global variable l:'local variable'"
        )
        self.assertIn("module 'unittest' from", f"{unittest}")

    def test_shadowed_global(self):
        a_global = "really a local"
        self.assertEqual(f"g:{a_global}", "g:really a local")
        self.assertEqual(f"g:{a_global!r}", "g:'really a local'")
        a_local = "local variable"
        self.assertEqual(
            f"g:{a_global} l:{a_local}", "g:really a local l:local variable"
        )
        self.assertEqual(f"g:{a_global!r}", "g:'really a local'")
        self.assertEqual(
            f"g:{a_global} l:{a_local!r}", "g:really a local l:'local variable'"
        )

    def test_call(self):
        def foo(x):
            return "x=" + str(x)

        self.assertEqual(f"{foo(10)}", "x=10")

    def test_nested_fstrings(self):
        y = 5
        self.assertEqual(f"{(f'{0}' * 3)}", "000")
        self.assertEqual(f"{(f'{y}' * 3)}", "555")

    def test_invalid_string_prefixes(self):
        single_quote_cases = [
            "fu''",
            "uf''",
            "Fu''",
            "fU''",
            "Uf''",
            "uF''",
            "ufr''",
            "urf''",
            "fur''",
            "fru''",
            "rfu''",
            "ruf''",
            "FUR''",
            "Fur''",
            "fb''",
            "fB''",
            "Fb''",
            "FB''",
            "bf''",
            "bF''",
            "Bf''",
            "BF''",
        ]
        double_quote_cases = [case.replace("'", '"') for case in single_quote_cases]
        self.assertAllRaise(
            SyntaxError,
            "unexpected EOF while parsing",
            (single_quote_cases + double_quote_cases),
        )

    def test_leading_trailing_spaces(self):
        self.assertEqual(f"{3}", "3")
        self.assertEqual(f"{3}", "3")
        self.assertEqual(f"{3}", "3")
        self.assertEqual(f"{3}", "3")
        self.assertEqual(f"expr={ {x: y for (x, y) in [(1, 2)]}}", "expr={1: 2}")
        self.assertEqual(f"expr={ {x: y for (x, y) in [(1, 2)]}}", "expr={1: 2}")

    def test_not_equal(self):
        self.assertEqual(f"{(3 != 4)}", "True")
        self.assertEqual(f"{(3 != 4):}", "True")
        self.assertEqual(f"{(3 != 4)!s}", "True")
        self.assertEqual(f"{(3 != 4)!s:.3}", "Tru")

    def test_equal_equal(self):
        self.assertEqual(f"{(0 == 1)}", "False")

    def test_conversions(self):
        self.assertEqual(f"{3.14:10.10}", "      3.14")
        self.assertEqual(f"{3.14!s:10.10}", "3.14      ")
        self.assertEqual(f"{3.14!r:10.10}", "3.14      ")
        self.assertEqual(f"{3.14!a:10.10}", "3.14      ")
        self.assertEqual(f"{'a'}", "a")
        self.assertEqual(f"{'a'!r}", "'a'")
        self.assertEqual(f"{'a'!a}", "'a'")
        self.assertEqual(f"{'a!r'}", "a!r")
        self.assertEqual(f"{3.14:!<10.10}", "3.14!!!!!!")
        self.assertAllRaise(
            SyntaxError,
            "f-string: invalid conversion character",
            [
                "f'{3!g}'",
                "f'{3!A}'",
                "f'{3!3}'",
                "f'{3!G}'",
                "f'{3!!}'",
                "f'{3!:}'",
                "f'{3! s}'",
            ],
        )
        self.assertAllRaise(
            SyntaxError,
            "f-string: expecting '}'",
            ["f'{x!s{y}}'", "f'{3!ss}'", "f'{3!ss:}'", "f'{3!ss:s}'"],
        )

    def test_assignment(self):
        self.assertAllRaise(
            SyntaxError, "invalid syntax", ["f'' = 3", "f'{0}' = x", "f'{x}' = x"]
        )

    def test_del(self):
        self.assertAllRaise(SyntaxError, "invalid syntax", ["del f''", "del '' f''"])

    def test_mismatched_braces(self):
        self.assertAllRaise(
            SyntaxError,
            "f-string: single '}' is not allowed",
            [
                "f'{{}'",
                "f'{{}}}'",
                "f'}'",
                "f'x}'",
                "f'x}x'",
                "f'\\u007b}'",
                "f'{3:}>10}'",
                "f'{3:}}>10}'",
            ],
        )
        self.assertAllRaise(
            SyntaxError,
            "f-string: expecting '}'",
            [
                "f'{3:{{>10}'",
                "f'{3'",
                "f'{3!'",
                "f'{3:'",
                "f'{3!s'",
                "f'{3!s:'",
                "f'{3!s:3'",
                "f'x{'",
                "f'x{x'",
                "f'{x'",
                "f'{3:s'",
                "f'{{{'",
                "f'{{}}{'",
                "f'{'",
            ],
        )
        self.assertEqual(f"{'{'}", "{")
        self.assertEqual(f"{'}'}", "}")
        self.assertEqual(f"{3:{'}'}>10}", "}}}}}}}}}3")
        self.assertEqual(f"{2:{'{'}>10}", "{{{{{{{{{2")

    def test_if_conditional(self):
        def test_fstring(x, expected):
            flag = 0
            if f"{x}":
                flag = 1
            else:
                flag = 2
            self.assertEqual(flag, expected)

        def test_concat_empty(x, expected):
            flag = 0
            if f"{x}":
                flag = 1
            else:
                flag = 2
            self.assertEqual(flag, expected)

        def test_concat_non_empty(x, expected):
            flag = 0
            if f" {x}":
                flag = 1
            else:
                flag = 2
            self.assertEqual(flag, expected)

        test_fstring("", 2)
        test_fstring(" ", 1)
        test_concat_empty("", 2)
        test_concat_empty(" ", 1)
        test_concat_non_empty("", 1)
        test_concat_non_empty(" ", 1)

    def test_empty_format_specifier(self):
        x = "test"
        self.assertEqual(f"{x}", "test")
        self.assertEqual(f"{x:}", "test")
        self.assertEqual(f"{x!s:}", "test")
        self.assertEqual(f"{x!r:}", "'test'")

    def test_str_format_differences(self):
        d = {"a": "string", 0: "integer"}
        a = 0
        self.assertEqual(f"{d[0]}", "integer")
        self.assertEqual(f"{d['a']}", "string")
        self.assertEqual(f"{d[a]}", "integer")
        self.assertEqual("{d[a]}".format(d=d), "string")
        self.assertEqual("{d[0]}".format(d=d), "integer")

    def test_errors(self):
        self.assertAllRaise(
            TypeError, "unsupported", ["f'{(lambda: 0):x}'", "f'{(0,):x}'"]
        )
        self.assertAllRaise(
            ValueError, "Unknown format code", ["f'{1000:j}'", "f'{1000:j}'"]
        )

    def test_filename_in_syntaxerror(self):
        with temp_cwd() as cwd:
            file_path = os.path.join(cwd, "t.py")
            with open(file_path, "w", encoding="utf-8") as f:
                f.write('f"{a b}"')
            (_, _, stderr) = assert_python_failure(file_path, PYTHONIOENCODING="ascii")
        self.assertIn(file_path.encode("ascii", "backslashreplace"), stderr)

    def test_loop(self):
        for i in range(1000):
            self.assertEqual(f"i:{i}", ("i:" + str(i)))

    def test_dict(self):
        d = {'"': "dquote", "'": "squote", "foo": "bar"}
        self.assertEqual(f"""{d["'"]}""", "squote")
        self.assertEqual(f"""{d['"']}""", "dquote")
        self.assertEqual(f"{d['foo']}", "bar")
        self.assertEqual(f"{d['foo']}", "bar")

    def test_backslash_char(self):
        self.assertEqual(eval('f"\\\n"'), "")
        self.assertEqual(eval('f"\\\r"'), "")

    def test_debug_conversion(self):
        x = "A string"
        self.assertEqual(f"x={x!r}", ("x=" + repr(x)))
        self.assertEqual(f"x ={x!r}", ("x =" + repr(x)))
        self.assertEqual(f"x={x!s}", ("x=" + str(x)))
        self.assertEqual(f"x={x!r}", ("x=" + repr(x)))
        self.assertEqual(f"x={x!a}", ("x=" + ascii(x)))
        x = 2.71828
        self.assertEqual(f"x={x:.2f}", ("x=" + format(x, ".2f")))
        self.assertEqual(f"x={x:}", ("x=" + format(x, "")))
        self.assertEqual(f"x={x!r:^20}", ("x=" + format(repr(x), "^20")))
        self.assertEqual(f"x={x!s:^20}", ("x=" + format(str(x), "^20")))
        self.assertEqual(f"x={x!a:^20}", ("x=" + format(ascii(x), "^20")))
        x = 9
        self.assertEqual(f"3*x+15={((3 * x) + 15)!r}", "3*x+15=42")
        tenπ = 31.4
        self.assertEqual(f"tenπ={tenπ:.2f}", "tenπ=31.40")
        self.assertEqual(f""""Σ"={'Σ'!r}""", "\"Σ\"='Σ'")
        self.assertEqual(f"{f'3.1415={3.1415:.1f}':*^20}", "*****3.1415=3.1*****")
        pi = "π"
        self.assertEqual(f"alpha α pi={pi!r} ω omega", "alpha α pi='π' ω omega")
        self.assertEqual(
            f"""
3
={3!r}""",
            "\n3\n=3",
        )
        self.assertEqual(f"{(0 == 1)}", "False")
        self.assertEqual(f"{(0 != 1)}", "True")
        self.assertEqual(f"{(0 <= 1)}", "True")
        self.assertEqual(f"{(0 >= 1)}", "False")
        self.assertEqual(f"{(x := '5')}", "5")
        self.assertEqual(x, "5")
        self.assertEqual(f"{(x := 5)}", "5")
        self.assertEqual(x, 5)
        self.assertEqual(f"{'='}", "=")
        x = 20
        self.assertEqual(f"{x:=10}", "        20")

        def f(a):
            nonlocal x
            oldx = x
            x = a
            return oldx

        x = 0
        self.assertEqual(f"{f(a='3=')}", "0")
        self.assertEqual(x, "3=")
        self.assertEqual(f"{f(a=4)}", "3=")
        self.assertEqual(x, 4)

        class C:
            def __format__(self, s):
                return f"FORMAT-{s}"

            def __repr__(self):
                return "REPR"

        self.assertEqual(f"C()={C()!r}", "C()=REPR")
        self.assertEqual(f"C()={C()!r}", "C()=REPR")
        self.assertEqual(f"C()={C():}", "C()=FORMAT-")
        self.assertEqual(f"C()={C(): }", "C()=FORMAT- ")
        self.assertEqual(f"C()={C():x}", "C()=FORMAT-x")
        self.assertEqual(f"C()={C()!r:*^20}", "C()=********REPR********")
        self.assertRaises(SyntaxError, eval, "f'{C=]'")
        x = "foo"
        self.assertEqual(f"Xx={x!r}Y", (("Xx=" + repr(x)) + "Y"))
        self.assertEqual(f"Xx  ={x!r}Y", (("Xx  =" + repr(x)) + "Y"))
        self.assertEqual(f"Xx=  {x!r}Y", (("Xx=  " + repr(x)) + "Y"))
        self.assertEqual(f"Xx  =  {x!r}Y", (("Xx  =  " + repr(x)) + "Y"))

    def test_walrus(self):
        x = 20
        self.assertEqual(f"{x:=10}", "        20")
        self.assertEqual(f"{(x := 10)}", "10")
        self.assertEqual(x, 10)

    def test_invalid_syntax_error_message(self):
        with self.assertRaisesRegex(SyntaxError, "f-string: invalid syntax"):
            compile("f'{a $ b}'", "?", "exec")

    def test_with_two_commas_in_format_specifier(self):
        error_msg = re.escape("Cannot specify ',' with ','.")
        with self.assertRaisesRegex(ValueError, error_msg):
            f"{1:,,}"

    def test_with_two_underscore_in_format_specifier(self):
        error_msg = re.escape("Cannot specify '_' with '_'.")
        with self.assertRaisesRegex(ValueError, error_msg):
            f"{1:__}"

    def test_with_a_commas_and_an_underscore_in_format_specifier(self):
        error_msg = re.escape("Cannot specify both ',' and '_'.")
        with self.assertRaisesRegex(ValueError, error_msg):
            f"{1:,_}"

    def test_with_an_underscore_and_a_comma_in_format_specifier(self):
        error_msg = re.escape("Cannot specify both ',' and '_'.")
        with self.assertRaisesRegex(ValueError, error_msg):
            f"{1:_,}"

    def test_syntax_error_for_starred_expressions(self):
        error_msg = re.escape("cannot use starred expression here")
        with self.assertRaisesRegex(SyntaxError, error_msg):
            compile("f'{*a}'", "?", "exec")
        error_msg = re.escape("cannot use double starred expression here")
        with self.assertRaisesRegex(SyntaxError, error_msg):
            compile("f'{**a}'", "?", "exec")


if __name__ == "__main__":
    unittest.main()
