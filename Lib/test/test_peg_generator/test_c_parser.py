import sysconfig
import textwrap
import unittest
from distutils.tests.support import TempdirManager
from pathlib import Path
from test import test_tools
from test import support
from test.support import os_helper
from test.support.script_helper import assert_python_ok

_py_cflags_nodist = sysconfig.get_config_var("PY_CFLAGS_NODIST")
_pgo_flag = sysconfig.get_config_var("PGO_PROF_USE_FLAG")
if _pgo_flag and _py_cflags_nodist and (_pgo_flag in _py_cflags_nodist):
    raise unittest.SkipTest("peg_generator test disabled under PGO build")
test_tools.skip_if_missing("peg_generator")
with test_tools.imports_under_tool("peg_generator"):
    from pegen.grammar_parser import GeneratedParser as GrammarParser
    from pegen.testutil import (
        parse_string,
        generate_parser_c_extension,
        generate_c_parser_source,
    )
    from pegen.ast_dump import ast_dump
TEST_TEMPLATE = '\ntmp_dir = {extension_path!r}\n\nimport ast\nimport traceback\nimport sys\nimport unittest\n\nfrom test import test_tools\nwith test_tools.imports_under_tool("peg_generator"):\n    from pegen.ast_dump import ast_dump\n\nsys.path.insert(0, tmp_dir)\nimport parse\n\nclass Tests(unittest.TestCase):\n\n    def check_input_strings_for_grammar(\n        self,\n        valid_cases = (),\n        invalid_cases = (),\n    ):\n        if valid_cases:\n            for case in valid_cases:\n                parse.parse_string(case, mode=0)\n\n        if invalid_cases:\n            for case in invalid_cases:\n                with self.assertRaises(SyntaxError):\n                    parse.parse_string(case, mode=0)\n\n    def verify_ast_generation(self, stmt):\n        expected_ast = ast.parse(stmt)\n        actual_ast = parse.parse_string(stmt, mode=1)\n        self.assertEqual(ast_dump(expected_ast), ast_dump(actual_ast))\n\n    def test_parse(self):\n        {test_source}\n\nunittest.main()\n'


class TestCParser(TempdirManager, unittest.TestCase):
    def setUp(self):
        cmd = support.missing_compiler_executable()
        if cmd is not None:
            self.skipTest(("The %r command is not found" % cmd))
        super(TestCParser, self).setUp()
        self.tmp_path = self.mkdtemp()
        change_cwd = os_helper.change_cwd(self.tmp_path)
        change_cwd.__enter__()
        self.addCleanup(change_cwd.__exit__, None, None, None)

    def tearDown(self):
        super(TestCParser, self).tearDown()

    def build_extension(self, grammar_source):
        grammar = parse_string(grammar_source, GrammarParser)
        generate_parser_c_extension(grammar, Path(self.tmp_path))

    def run_test(self, grammar_source, test_source):
        self.build_extension(grammar_source)
        test_source = textwrap.indent(textwrap.dedent(test_source), (8 * " "))
        assert_python_ok(
            "-c",
            TEST_TEMPLATE.format(extension_path=self.tmp_path, test_source=test_source),
        )

    def test_c_parser(self) -> None:
        grammar_source = "\n        start[mod_ty]: a[asdl_stmt_seq*]=stmt* $ { _PyAST_Module(a, NULL, p->arena) }\n        stmt[stmt_ty]: a=expr_stmt { a }\n        expr_stmt[stmt_ty]: a=expression NEWLINE { _PyAST_Expr(a, EXTRA) }\n        expression[expr_ty]: ( l=expression '+' r=term { _PyAST_BinOp(l, Add, r, EXTRA) }\n                            | l=expression '-' r=term { _PyAST_BinOp(l, Sub, r, EXTRA) }\n                            | t=term { t }\n                            )\n        term[expr_ty]: ( l=term '*' r=factor { _PyAST_BinOp(l, Mult, r, EXTRA) }\n                    | l=term '/' r=factor { _PyAST_BinOp(l, Div, r, EXTRA) }\n                    | f=factor { f }\n                    )\n        factor[expr_ty]: ('(' e=expression ')' { e }\n                        | a=atom { a }\n                        )\n        atom[expr_ty]: ( n=NAME { n }\n                    | n=NUMBER { n }\n                    | s=STRING { s }\n                    )\n        "
        test_source = '\n        expressions = [\n            "4+5",\n            "4-5",\n            "4*5",\n            "1+4*5",\n            "1+4/5",\n            "(1+1) + (1+1)",\n            "(1+1) - (1+1)",\n            "(1+1) * (1+1)",\n            "(1+1) / (1+1)",\n        ]\n\n        for expr in expressions:\n            the_ast = parse.parse_string(expr, mode=1)\n            expected_ast = ast.parse(expr)\n            self.assertEqual(ast_dump(the_ast), ast_dump(expected_ast))\n        '
        self.run_test(grammar_source, test_source)

    def test_lookahead(self) -> None:
        grammar_source = "\n        start: NAME &NAME expr NEWLINE? ENDMARKER\n        expr: NAME | NUMBER\n        "
        test_source = '\n        valid_cases = ["foo bar"]\n        invalid_cases = ["foo 34"]\n        self.check_input_strings_for_grammar(valid_cases, invalid_cases)\n        '
        self.run_test(grammar_source, test_source)

    def test_negative_lookahead(self) -> None:
        grammar_source = "\n        start: NAME !NAME expr NEWLINE? ENDMARKER\n        expr: NAME | NUMBER\n        "
        test_source = '\n        valid_cases = ["foo 34"]\n        invalid_cases = ["foo bar"]\n        self.check_input_strings_for_grammar(valid_cases, invalid_cases)\n        '
        self.run_test(grammar_source, test_source)

    def test_cut(self) -> None:
        grammar_source = "\n        start: X ~ Y Z | X Q S\n        X: 'x'\n        Y: 'y'\n        Z: 'z'\n        Q: 'q'\n        S: 's'\n        "
        test_source = '\n        valid_cases = ["x y z"]\n        invalid_cases = ["x q s"]\n        self.check_input_strings_for_grammar(valid_cases, invalid_cases)\n        '
        self.run_test(grammar_source, test_source)

    def test_gather(self) -> None:
        grammar_source = "\n        start: ';'.pass_stmt+ NEWLINE\n        pass_stmt: 'pass'\n        "
        test_source = '\n        valid_cases = ["pass", "pass; pass"]\n        invalid_cases = ["pass;", "pass; pass;"]\n        self.check_input_strings_for_grammar(valid_cases, invalid_cases)\n        '
        self.run_test(grammar_source, test_source)

    def test_left_recursion(self) -> None:
        grammar_source = "\n        start: expr NEWLINE\n        expr: ('-' term | expr '+' term | term)\n        term: NUMBER\n        "
        test_source = '\n        valid_cases = ["-34", "34", "34 + 12", "1 + 1 + 2 + 3"]\n        self.check_input_strings_for_grammar(valid_cases)\n        '
        self.run_test(grammar_source, test_source)

    def test_advanced_left_recursive(self) -> None:
        grammar_source = (
            "\n        start: NUMBER | sign start\n        sign: ['-']\n        "
        )
        test_source = '\n        valid_cases = ["23", "-34"]\n        self.check_input_strings_for_grammar(valid_cases)\n        '
        self.run_test(grammar_source, test_source)

    def test_mutually_left_recursive(self) -> None:
        grammar_source = "\n        start: foo 'E'\n        foo: bar 'A' | 'B'\n        bar: foo 'C' | 'D'\n        "
        test_source = '\n        valid_cases = ["B E", "D A C A E"]\n        self.check_input_strings_for_grammar(valid_cases)\n        '
        self.run_test(grammar_source, test_source)

    def test_nasty_mutually_left_recursive(self) -> None:
        grammar_source = "\n        start: target '='\n        target: maybe '+' | NAME\n        maybe: maybe '-' | target\n        "
        test_source = '\n        valid_cases = ["x ="]\n        invalid_cases = ["x - + ="]\n        self.check_input_strings_for_grammar(valid_cases, invalid_cases)\n        '
        self.run_test(grammar_source, test_source)

    def test_return_stmt_noexpr_action(self) -> None:
        grammar_source = "\n        start[mod_ty]: a=[statements] ENDMARKER { _PyAST_Module(a, NULL, p->arena) }\n        statements[asdl_stmt_seq*]: a[asdl_stmt_seq*]=statement+ { a }\n        statement[stmt_ty]: simple_stmt\n        simple_stmt[stmt_ty]: small_stmt\n        small_stmt[stmt_ty]: return_stmt\n        return_stmt[stmt_ty]: a='return' NEWLINE { _PyAST_Return(NULL, EXTRA) }\n        "
        test_source = '\n        stmt = "return"\n        self.verify_ast_generation(stmt)\n        '
        self.run_test(grammar_source, test_source)

    def test_gather_action_ast(self) -> None:
        grammar_source = "\n        start[mod_ty]: a[asdl_stmt_seq*]=';'.pass_stmt+ NEWLINE ENDMARKER { _PyAST_Module(a, NULL, p->arena) }\n        pass_stmt[stmt_ty]: a='pass' { _PyAST_Pass(EXTRA)}\n        "
        test_source = '\n        stmt = "pass; pass"\n        self.verify_ast_generation(stmt)\n        '
        self.run_test(grammar_source, test_source)

    def test_pass_stmt_action(self) -> None:
        grammar_source = "\n        start[mod_ty]: a=[statements] ENDMARKER { _PyAST_Module(a, NULL, p->arena) }\n        statements[asdl_stmt_seq*]: a[asdl_stmt_seq*]=statement+ { a }\n        statement[stmt_ty]: simple_stmt\n        simple_stmt[stmt_ty]: small_stmt\n        small_stmt[stmt_ty]: pass_stmt\n        pass_stmt[stmt_ty]: a='pass' NEWLINE { _PyAST_Pass(EXTRA) }\n        "
        test_source = '\n        stmt = "pass"\n        self.verify_ast_generation(stmt)\n        '
        self.run_test(grammar_source, test_source)

    def test_if_stmt_action(self) -> None:
        grammar_source = "\n        start[mod_ty]: a=[statements] ENDMARKER { _PyAST_Module(a, NULL, p->arena) }\n        statements[asdl_stmt_seq*]: a=statement+ { (asdl_stmt_seq*)_PyPegen_seq_flatten(p, a) }\n        statement[asdl_stmt_seq*]:  a=compound_stmt { (asdl_stmt_seq*)_PyPegen_singleton_seq(p, a) } | simple_stmt\n\n        simple_stmt[asdl_stmt_seq*]: a=small_stmt b=further_small_stmt* [';'] NEWLINE {\n                                            (asdl_stmt_seq*)_PyPegen_seq_insert_in_front(p, a, b) }\n        further_small_stmt[stmt_ty]: ';' a=small_stmt { a }\n\n        block: simple_stmt | NEWLINE INDENT a=statements DEDENT { a }\n\n        compound_stmt: if_stmt\n\n        if_stmt: 'if' a=full_expression ':' b=block { _PyAST_If(a, b, NULL, EXTRA) }\n\n        small_stmt[stmt_ty]: pass_stmt\n\n        pass_stmt[stmt_ty]: a='pass' { _PyAST_Pass(EXTRA) }\n\n        full_expression: NAME\n        "
        test_source = '\n        stmt = "pass"\n        self.verify_ast_generation(stmt)\n        '
        self.run_test(grammar_source, test_source)

    def test_same_name_different_types(self) -> None:
        grammar_source = "\n        start[mod_ty]: a[asdl_stmt_seq*]=import_from+ NEWLINE ENDMARKER { _PyAST_Module(a, NULL, p->arena)}\n        import_from[stmt_ty]: ( a='from' !'import' c=simple_name 'import' d=import_as_names_from {\n                                _PyAST_ImportFrom(c->v.Name.id, d, 0, EXTRA) }\n                            | a='from' '.' 'import' c=import_as_names_from {\n                                _PyAST_ImportFrom(NULL, c, 1, EXTRA) }\n                            )\n        simple_name[expr_ty]: NAME\n        import_as_names_from[asdl_alias_seq*]: a[asdl_alias_seq*]=','.import_as_name_from+ { a }\n        import_as_name_from[alias_ty]: a=NAME 'as' b=NAME { _PyAST_alias(((expr_ty) a)->v.Name.id, ((expr_ty) b)->v.Name.id, EXTRA) }\n        "
        test_source = '\n        for stmt in ("from a import b as c", "from . import a as b"):\n            expected_ast = ast.parse(stmt)\n            actual_ast = parse.parse_string(stmt, mode=1)\n            self.assertEqual(ast_dump(expected_ast), ast_dump(actual_ast))\n        '
        self.run_test(grammar_source, test_source)

    def test_with_stmt_with_paren(self) -> None:
        grammar_source = "\n        start[mod_ty]: a=[statements] ENDMARKER { _PyAST_Module(a, NULL, p->arena) }\n        statements[asdl_stmt_seq*]: a=statement+ { (asdl_stmt_seq*)_PyPegen_seq_flatten(p, a) }\n        statement[asdl_stmt_seq*]: a=compound_stmt { (asdl_stmt_seq*)_PyPegen_singleton_seq(p, a) }\n        compound_stmt[stmt_ty]: with_stmt\n        with_stmt[stmt_ty]: (\n            a='with' '(' b[asdl_withitem_seq*]=','.with_item+ ')' ':' c=block {\n                _PyAST_With(b, (asdl_stmt_seq*) _PyPegen_singleton_seq(p, c), NULL, EXTRA) }\n        )\n        with_item[withitem_ty]: (\n            e=NAME o=['as' t=NAME { t }] { _PyAST_withitem(e, _PyPegen_set_expr_context(p, o, Store), p->arena) }\n        )\n        block[stmt_ty]: a=pass_stmt NEWLINE { a } | NEWLINE INDENT a=pass_stmt DEDENT { a }\n        pass_stmt[stmt_ty]: a='pass' { _PyAST_Pass(EXTRA) }\n        "
        test_source = "\n        stmt = \"with (\\n    a as b,\\n    c as d\\n): pass\"\n        the_ast = parse.parse_string(stmt, mode=1)\n        self.assertTrue(ast_dump(the_ast).startswith(\n            \"Module(body=[With(items=[withitem(context_expr=Name(id='a', ctx=Load()), optional_vars=Name(id='b', ctx=Store())), \"\n            \"withitem(context_expr=Name(id='c', ctx=Load()), optional_vars=Name(id='d', ctx=Store()))]\"\n        ))\n        "
        self.run_test(grammar_source, test_source)

    def test_ternary_operator(self) -> None:
        grammar_source = "\n        start[mod_ty]: a=expr ENDMARKER { _PyAST_Module(a, NULL, p->arena) }\n        expr[asdl_stmt_seq*]: a=listcomp NEWLINE { (asdl_stmt_seq*)_PyPegen_singleton_seq(p, _PyAST_Expr(a, EXTRA)) }\n        listcomp[expr_ty]: (\n            a='[' b=NAME c=for_if_clauses d=']' { _PyAST_ListComp(b, c, EXTRA) }\n        )\n        for_if_clauses[asdl_comprehension_seq*]: (\n            a[asdl_comprehension_seq*]=(y=[ASYNC] 'for' a=NAME 'in' b=NAME c[asdl_expr_seq*]=('if' z=NAME { z })*\n                { _PyAST_comprehension(_PyAST_Name(((expr_ty) a)->v.Name.id, Store, EXTRA), b, c, (y == NULL) ? 0 : 1, p->arena) })+ { a }\n        )\n        "
        test_source = '\n        stmt = "[i for i in a if b]"\n        self.verify_ast_generation(stmt)\n        '
        self.run_test(grammar_source, test_source)

    def test_syntax_error_for_string(self) -> None:
        grammar_source = (
            "\n        start: expr+ NEWLINE? ENDMARKER\n        expr: NAME\n        "
        )
        test_source = '\n        for text in ("a b 42 b a", "\\u540d \\u540d 42 \\u540d \\u540d"):\n            try:\n                parse.parse_string(text, mode=0)\n            except SyntaxError as e:\n                tb = traceback.format_exc()\n            self.assertTrue(\'File "<string>", line 1\' in tb)\n            self.assertTrue(f"SyntaxError: invalid syntax" in tb)\n        '
        self.run_test(grammar_source, test_source)

    def test_headers_and_trailer(self) -> None:
        grammar_source = "\n        @header 'SOME HEADER'\n        @subheader 'SOME SUBHEADER'\n        @trailer 'SOME TRAILER'\n        start: expr+ NEWLINE? ENDMARKER\n        expr: x=NAME\n        "
        grammar = parse_string(grammar_source, GrammarParser)
        parser_source = generate_c_parser_source(grammar)
        self.assertTrue(("SOME HEADER" in parser_source))
        self.assertTrue(("SOME SUBHEADER" in parser_source))
        self.assertTrue(("SOME TRAILER" in parser_source))

    def test_error_in_rules(self) -> None:
        grammar_source = "\n        start: expr+ NEWLINE? ENDMARKER\n        expr: NAME {PyTuple_New(-1)}\n        "
        test_source = '\n        with self.assertRaises(SystemError):\n            parse.parse_string("a", mode=0)\n        '
        self.run_test(grammar_source, test_source)

    def test_no_soft_keywords(self) -> None:
        grammar_source = (
            "\n        start: expr+ NEWLINE? ENDMARKER\n        expr: 'foo'\n        "
        )
        grammar = parse_string(grammar_source, GrammarParser)
        parser_source = generate_c_parser_source(grammar)
        assert "expect_soft_keyword" not in parser_source

    def test_soft_keywords(self) -> None:
        grammar_source = (
            '\n        start: expr+ NEWLINE? ENDMARKER\n        expr: "foo"\n        '
        )
        grammar = parse_string(grammar_source, GrammarParser)
        parser_source = generate_c_parser_source(grammar)
        assert "expect_soft_keyword" in parser_source

    def test_soft_keywords_parse(self) -> None:
        grammar_source = "\n        start: \"if\" expr '+' expr NEWLINE\n        expr: NAME\n        "
        test_source = '\n        valid_cases = ["if if + if"]\n        invalid_cases = ["if if"]\n        self.check_input_strings_for_grammar(valid_cases, invalid_cases)\n        '
        self.run_test(grammar_source, test_source)

    def test_soft_keywords_lookahead(self) -> None:
        grammar_source = '\n        start: &"if" "if" expr \'+\' expr NEWLINE\n        expr: NAME\n        '
        test_source = '\n        valid_cases = ["if if + if"]\n        invalid_cases = ["if if"]\n        self.check_input_strings_for_grammar(valid_cases, invalid_cases)\n        '
        self.run_test(grammar_source, test_source)
