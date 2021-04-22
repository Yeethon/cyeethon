import io
import textwrap
import unittest
from test import test_tools
from typing import Dict, Any
from tokenize import TokenInfo, NAME, NEWLINE, NUMBER, OP

test_tools.skip_if_missing("peg_generator")
with test_tools.imports_under_tool("peg_generator"):
    from pegen.grammar_parser import GeneratedParser as GrammarParser
    from pegen.testutil import parse_string, generate_parser, make_parser
    from pegen.grammar import GrammarVisitor, GrammarError, Grammar
    from pegen.grammar_visualizer import ASTGrammarPrinter
    from pegen.parser import Parser
    from pegen.python_generator import PythonParserGenerator


class TestPegen(unittest.TestCase):
    def test_parse_grammar(self) -> None:
        grammar_source = "\n        start: sum NEWLINE\n        sum: t1=term '+' t2=term { action } | term\n        term: NUMBER\n        "
        expected = "\n        start: sum NEWLINE\n        sum: term '+' term | term\n        term: NUMBER\n        "
        grammar: Grammar = parse_string(grammar_source, GrammarParser)
        rules = grammar.rules
        self.assertEqual(str(grammar), textwrap.dedent(expected).strip())
        self.assertEqual(str(rules["start"]), "start: sum NEWLINE")
        self.assertEqual(str(rules["sum"]), "sum: term '+' term | term")
        expected_repr = (
            "Rule('term', None, Rhs([Alt([NamedItem(None, NameLeaf('NUMBER'))])]))"
        )
        self.assertEqual(repr(rules["term"]), expected_repr)

    def test_long_rule_str(self) -> None:
        grammar_source = "\n        start: zero | one | one zero | one one | one zero zero | one zero one | one one zero | one one one\n        "
        expected = "\n        start:\n            | zero\n            | one\n            | one zero\n            | one one\n            | one zero zero\n            | one zero one\n            | one one zero\n            | one one one\n        "
        grammar: Grammar = parse_string(grammar_source, GrammarParser)
        self.assertEqual(str(grammar.rules["start"]), textwrap.dedent(expected).strip())

    def test_typed_rules(self) -> None:
        grammar = "\n        start[int]: sum NEWLINE\n        sum[int]: t1=term '+' t2=term { action } | term\n        term[int]: NUMBER\n        "
        rules = parse_string(grammar, GrammarParser).rules
        self.assertEqual(str(rules["start"]), "start: sum NEWLINE")
        self.assertEqual(str(rules["sum"]), "sum: term '+' term | term")
        self.assertEqual(
            repr(rules["term"]),
            "Rule('term', 'int', Rhs([Alt([NamedItem(None, NameLeaf('NUMBER'))])]))",
        )

    def test_gather(self) -> None:
        grammar = "\n        start: ','.thing+ NEWLINE\n        thing: NUMBER\n        "
        rules = parse_string(grammar, GrammarParser).rules
        self.assertEqual(str(rules["start"]), "start: ','.thing+ NEWLINE")
        self.assertTrue(
            repr(rules["start"]).startswith(
                "Rule('start', None, Rhs([Alt([NamedItem(None, Gather(StringLeaf(\"','\"), NameLeaf('thing'"
            )
        )
        self.assertEqual(str(rules["thing"]), "thing: NUMBER")
        parser_class = make_parser(grammar)
        node = parse_string("42\n", parser_class)
        assert node == [
            [[TokenInfo(NUMBER, string="42", start=(1, 0), end=(1, 2), line="42\n")]],
            TokenInfo(NEWLINE, string="\n", start=(1, 2), end=(1, 3), line="42\n"),
        ]
        node = parse_string("1, 2\n", parser_class)
        assert node == [
            [
                [
                    TokenInfo(
                        NUMBER, string="1", start=(1, 0), end=(1, 1), line="1, 2\n"
                    )
                ],
                [
                    TokenInfo(
                        NUMBER, string="2", start=(1, 3), end=(1, 4), line="1, 2\n"
                    )
                ],
            ],
            TokenInfo(NEWLINE, string="\n", start=(1, 4), end=(1, 5), line="1, 2\n"),
        ]

    def test_expr_grammar(self) -> None:
        grammar = "\n        start: sum NEWLINE\n        sum: term '+' term | term\n        term: NUMBER\n        "
        parser_class = make_parser(grammar)
        node = parse_string("42\n", parser_class)
        self.assertEqual(
            node,
            [
                [
                    [
                        TokenInfo(
                            NUMBER, string="42", start=(1, 0), end=(1, 2), line="42\n"
                        )
                    ]
                ],
                TokenInfo(NEWLINE, string="\n", start=(1, 2), end=(1, 3), line="42\n"),
            ],
        )

    def test_optional_operator(self) -> None:
        grammar = "\n        start: sum NEWLINE\n        sum: term ('+' term)?\n        term: NUMBER\n        "
        parser_class = make_parser(grammar)
        node = parse_string("1+2\n", parser_class)
        self.assertEqual(
            node,
            [
                [
                    [
                        TokenInfo(
                            NUMBER, string="1", start=(1, 0), end=(1, 1), line="1+2\n"
                        )
                    ],
                    [
                        TokenInfo(
                            OP, string="+", start=(1, 1), end=(1, 2), line="1+2\n"
                        ),
                        [
                            TokenInfo(
                                NUMBER,
                                string="2",
                                start=(1, 2),
                                end=(1, 3),
                                line="1+2\n",
                            )
                        ],
                    ],
                ],
                TokenInfo(NEWLINE, string="\n", start=(1, 3), end=(1, 4), line="1+2\n"),
            ],
        )
        node = parse_string("1\n", parser_class)
        self.assertEqual(
            node,
            [
                [
                    [
                        TokenInfo(
                            NUMBER, string="1", start=(1, 0), end=(1, 1), line="1\n"
                        )
                    ],
                    None,
                ],
                TokenInfo(NEWLINE, string="\n", start=(1, 1), end=(1, 2), line="1\n"),
            ],
        )

    def test_optional_literal(self) -> None:
        grammar = "\n        start: sum NEWLINE\n        sum: term '+' ?\n        term: NUMBER\n        "
        parser_class = make_parser(grammar)
        node = parse_string("1+\n", parser_class)
        self.assertEqual(
            node,
            [
                [
                    [
                        TokenInfo(
                            NUMBER, string="1", start=(1, 0), end=(1, 1), line="1+\n"
                        )
                    ],
                    TokenInfo(OP, string="+", start=(1, 1), end=(1, 2), line="1+\n"),
                ],
                TokenInfo(NEWLINE, string="\n", start=(1, 2), end=(1, 3), line="1+\n"),
            ],
        )
        node = parse_string("1\n", parser_class)
        self.assertEqual(
            node,
            [
                [
                    [
                        TokenInfo(
                            NUMBER, string="1", start=(1, 0), end=(1, 1), line="1\n"
                        )
                    ],
                    None,
                ],
                TokenInfo(NEWLINE, string="\n", start=(1, 1), end=(1, 2), line="1\n"),
            ],
        )

    def test_alt_optional_operator(self) -> None:
        grammar = "\n        start: sum NEWLINE\n        sum: term ['+' term]\n        term: NUMBER\n        "
        parser_class = make_parser(grammar)
        node = parse_string("1 + 2\n", parser_class)
        self.assertEqual(
            node,
            [
                [
                    [
                        TokenInfo(
                            NUMBER, string="1", start=(1, 0), end=(1, 1), line="1 + 2\n"
                        )
                    ],
                    [
                        TokenInfo(
                            OP, string="+", start=(1, 2), end=(1, 3), line="1 + 2\n"
                        ),
                        [
                            TokenInfo(
                                NUMBER,
                                string="2",
                                start=(1, 4),
                                end=(1, 5),
                                line="1 + 2\n",
                            )
                        ],
                    ],
                ],
                TokenInfo(
                    NEWLINE, string="\n", start=(1, 5), end=(1, 6), line="1 + 2\n"
                ),
            ],
        )
        node = parse_string("1\n", parser_class)
        self.assertEqual(
            node,
            [
                [
                    [
                        TokenInfo(
                            NUMBER, string="1", start=(1, 0), end=(1, 1), line="1\n"
                        )
                    ],
                    None,
                ],
                TokenInfo(NEWLINE, string="\n", start=(1, 1), end=(1, 2), line="1\n"),
            ],
        )

    def test_repeat_0_simple(self) -> None:
        grammar = (
            "\n        start: thing thing* NEWLINE\n        thing: NUMBER\n        "
        )
        parser_class = make_parser(grammar)
        node = parse_string("1 2 3\n", parser_class)
        self.assertEqual(
            node,
            [
                [
                    TokenInfo(
                        NUMBER, string="1", start=(1, 0), end=(1, 1), line="1 2 3\n"
                    )
                ],
                [
                    [
                        [
                            TokenInfo(
                                NUMBER,
                                string="2",
                                start=(1, 2),
                                end=(1, 3),
                                line="1 2 3\n",
                            )
                        ]
                    ],
                    [
                        [
                            TokenInfo(
                                NUMBER,
                                string="3",
                                start=(1, 4),
                                end=(1, 5),
                                line="1 2 3\n",
                            )
                        ]
                    ],
                ],
                TokenInfo(
                    NEWLINE, string="\n", start=(1, 5), end=(1, 6), line="1 2 3\n"
                ),
            ],
        )
        node = parse_string("1\n", parser_class)
        self.assertEqual(
            node,
            [
                [TokenInfo(NUMBER, string="1", start=(1, 0), end=(1, 1), line="1\n")],
                [],
                TokenInfo(NEWLINE, string="\n", start=(1, 1), end=(1, 2), line="1\n"),
            ],
        )

    def test_repeat_0_complex(self) -> None:
        grammar = (
            "\n        start: term ('+' term)* NEWLINE\n        term: NUMBER\n        "
        )
        parser_class = make_parser(grammar)
        node = parse_string("1 + 2 + 3\n", parser_class)
        self.assertEqual(
            node,
            [
                [
                    TokenInfo(
                        NUMBER, string="1", start=(1, 0), end=(1, 1), line="1 + 2 + 3\n"
                    )
                ],
                [
                    [
                        [
                            TokenInfo(
                                OP,
                                string="+",
                                start=(1, 2),
                                end=(1, 3),
                                line="1 + 2 + 3\n",
                            ),
                            [
                                TokenInfo(
                                    NUMBER,
                                    string="2",
                                    start=(1, 4),
                                    end=(1, 5),
                                    line="1 + 2 + 3\n",
                                )
                            ],
                        ]
                    ],
                    [
                        [
                            TokenInfo(
                                OP,
                                string="+",
                                start=(1, 6),
                                end=(1, 7),
                                line="1 + 2 + 3\n",
                            ),
                            [
                                TokenInfo(
                                    NUMBER,
                                    string="3",
                                    start=(1, 8),
                                    end=(1, 9),
                                    line="1 + 2 + 3\n",
                                )
                            ],
                        ]
                    ],
                ],
                TokenInfo(
                    NEWLINE, string="\n", start=(1, 9), end=(1, 10), line="1 + 2 + 3\n"
                ),
            ],
        )

    def test_repeat_1_simple(self) -> None:
        grammar = (
            "\n        start: thing thing+ NEWLINE\n        thing: NUMBER\n        "
        )
        parser_class = make_parser(grammar)
        node = parse_string("1 2 3\n", parser_class)
        self.assertEqual(
            node,
            [
                [
                    TokenInfo(
                        NUMBER, string="1", start=(1, 0), end=(1, 1), line="1 2 3\n"
                    )
                ],
                [
                    [
                        [
                            TokenInfo(
                                NUMBER,
                                string="2",
                                start=(1, 2),
                                end=(1, 3),
                                line="1 2 3\n",
                            )
                        ]
                    ],
                    [
                        [
                            TokenInfo(
                                NUMBER,
                                string="3",
                                start=(1, 4),
                                end=(1, 5),
                                line="1 2 3\n",
                            )
                        ]
                    ],
                ],
                TokenInfo(
                    NEWLINE, string="\n", start=(1, 5), end=(1, 6), line="1 2 3\n"
                ),
            ],
        )
        with self.assertRaises(SyntaxError):
            parse_string("1\n", parser_class)

    def test_repeat_1_complex(self) -> None:
        grammar = (
            "\n        start: term ('+' term)+ NEWLINE\n        term: NUMBER\n        "
        )
        parser_class = make_parser(grammar)
        node = parse_string("1 + 2 + 3\n", parser_class)
        self.assertEqual(
            node,
            [
                [
                    TokenInfo(
                        NUMBER, string="1", start=(1, 0), end=(1, 1), line="1 + 2 + 3\n"
                    )
                ],
                [
                    [
                        [
                            TokenInfo(
                                OP,
                                string="+",
                                start=(1, 2),
                                end=(1, 3),
                                line="1 + 2 + 3\n",
                            ),
                            [
                                TokenInfo(
                                    NUMBER,
                                    string="2",
                                    start=(1, 4),
                                    end=(1, 5),
                                    line="1 + 2 + 3\n",
                                )
                            ],
                        ]
                    ],
                    [
                        [
                            TokenInfo(
                                OP,
                                string="+",
                                start=(1, 6),
                                end=(1, 7),
                                line="1 + 2 + 3\n",
                            ),
                            [
                                TokenInfo(
                                    NUMBER,
                                    string="3",
                                    start=(1, 8),
                                    end=(1, 9),
                                    line="1 + 2 + 3\n",
                                )
                            ],
                        ]
                    ],
                ],
                TokenInfo(
                    NEWLINE, string="\n", start=(1, 9), end=(1, 10), line="1 + 2 + 3\n"
                ),
            ],
        )
        with self.assertRaises(SyntaxError):
            parse_string("1\n", parser_class)

    def test_repeat_with_sep_simple(self) -> None:
        grammar = "\n        start: ','.thing+ NEWLINE\n        thing: NUMBER\n        "
        parser_class = make_parser(grammar)
        node = parse_string("1, 2, 3\n", parser_class)
        self.assertEqual(
            node,
            [
                [
                    [
                        TokenInfo(
                            NUMBER,
                            string="1",
                            start=(1, 0),
                            end=(1, 1),
                            line="1, 2, 3\n",
                        )
                    ],
                    [
                        TokenInfo(
                            NUMBER,
                            string="2",
                            start=(1, 3),
                            end=(1, 4),
                            line="1, 2, 3\n",
                        )
                    ],
                    [
                        TokenInfo(
                            NUMBER,
                            string="3",
                            start=(1, 6),
                            end=(1, 7),
                            line="1, 2, 3\n",
                        )
                    ],
                ],
                TokenInfo(
                    NEWLINE, string="\n", start=(1, 7), end=(1, 8), line="1, 2, 3\n"
                ),
            ],
        )

    def test_left_recursive(self) -> None:
        grammar_source = "\n        start: expr NEWLINE\n        expr: ('-' term | expr '+' term | term)\n        term: NUMBER\n        foo: NAME+\n        bar: NAME*\n        baz: NAME?\n        "
        grammar: Grammar = parse_string(grammar_source, GrammarParser)
        parser_class = generate_parser(grammar)
        rules = grammar.rules
        self.assertFalse(rules["start"].left_recursive)
        self.assertTrue(rules["expr"].left_recursive)
        self.assertFalse(rules["term"].left_recursive)
        self.assertFalse(rules["foo"].left_recursive)
        self.assertFalse(rules["bar"].left_recursive)
        self.assertFalse(rules["baz"].left_recursive)
        node = parse_string("1 + 2 + 3\n", parser_class)
        self.assertEqual(
            node,
            [
                [
                    [
                        [
                            [
                                TokenInfo(
                                    NUMBER,
                                    string="1",
                                    start=(1, 0),
                                    end=(1, 1),
                                    line="1 + 2 + 3\n",
                                )
                            ]
                        ],
                        TokenInfo(
                            OP, string="+", start=(1, 2), end=(1, 3), line="1 + 2 + 3\n"
                        ),
                        [
                            TokenInfo(
                                NUMBER,
                                string="2",
                                start=(1, 4),
                                end=(1, 5),
                                line="1 + 2 + 3\n",
                            )
                        ],
                    ],
                    TokenInfo(
                        OP, string="+", start=(1, 6), end=(1, 7), line="1 + 2 + 3\n"
                    ),
                    [
                        TokenInfo(
                            NUMBER,
                            string="3",
                            start=(1, 8),
                            end=(1, 9),
                            line="1 + 2 + 3\n",
                        )
                    ],
                ],
                TokenInfo(
                    NEWLINE, string="\n", start=(1, 9), end=(1, 10), line="1 + 2 + 3\n"
                ),
            ],
        )

    def test_python_expr(self) -> None:
        grammar = "\n        start: expr NEWLINE? $ { ast.Expression(expr, lineno=1, col_offset=0) }\n        expr: ( expr '+' term { ast.BinOp(expr, ast.Add(), term, lineno=expr.lineno, col_offset=expr.col_offset, end_lineno=term.end_lineno, end_col_offset=term.end_col_offset) }\n            | expr '-' term { ast.BinOp(expr, ast.Sub(), term, lineno=expr.lineno, col_offset=expr.col_offset, end_lineno=term.end_lineno, end_col_offset=term.end_col_offset) }\n            | term { term }\n            )\n        term: ( l=term '*' r=factor { ast.BinOp(l, ast.Mult(), r, lineno=l.lineno, col_offset=l.col_offset, end_lineno=r.end_lineno, end_col_offset=r.end_col_offset) }\n            | l=term '/' r=factor { ast.BinOp(l, ast.Div(), r, lineno=l.lineno, col_offset=l.col_offset, end_lineno=r.end_lineno, end_col_offset=r.end_col_offset) }\n            | factor { factor }\n            )\n        factor: ( '(' expr ')' { expr }\n                | atom { atom }\n                )\n        atom: ( n=NAME { ast.Name(id=n.string, ctx=ast.Load(), lineno=n.start[0], col_offset=n.start[1], end_lineno=n.end[0], end_col_offset=n.end[1]) }\n            | n=NUMBER { ast.Constant(value=ast.literal_eval(n.string), lineno=n.start[0], col_offset=n.start[1], end_lineno=n.end[0], end_col_offset=n.end[1]) }\n            )\n        "
        parser_class = make_parser(grammar)
        node = parse_string("(1 + 2*3 + 5)/(6 - 2)\n", parser_class)
        code = compile(node, "", "eval")
        val = eval(code)
        self.assertEqual(val, 3.0)

    def test_nullable(self) -> None:
        grammar_source = (
            "\n        start: sign NUMBER\n        sign: ['-' | '+']\n        "
        )
        grammar: Grammar = parse_string(grammar_source, GrammarParser)
        out = io.StringIO()
        genr = PythonParserGenerator(grammar, out)
        rules = grammar.rules
        self.assertFalse(rules["start"].nullable)
        self.assertTrue(rules["sign"].nullable)

    def test_advanced_left_recursive(self) -> None:
        grammar_source = (
            "\n        start: NUMBER | sign start\n        sign: ['-']\n        "
        )
        grammar: Grammar = parse_string(grammar_source, GrammarParser)
        out = io.StringIO()
        genr = PythonParserGenerator(grammar, out)
        rules = grammar.rules
        self.assertFalse(rules["start"].nullable)
        self.assertTrue(rules["sign"].nullable)
        self.assertTrue(rules["start"].left_recursive)
        self.assertFalse(rules["sign"].left_recursive)

    def test_mutually_left_recursive(self) -> None:
        grammar_source = "\n        start: foo 'E'\n        foo: bar 'A' | 'B'\n        bar: foo 'C' | 'D'\n        "
        grammar: Grammar = parse_string(grammar_source, GrammarParser)
        out = io.StringIO()
        genr = PythonParserGenerator(grammar, out)
        rules = grammar.rules
        self.assertFalse(rules["start"].left_recursive)
        self.assertTrue(rules["foo"].left_recursive)
        self.assertTrue(rules["bar"].left_recursive)
        genr.generate("<string>")
        ns: Dict[(str, Any)] = {}
        exec(out.getvalue(), ns)
        parser_class: Type[Parser] = ns["GeneratedParser"]
        node = parse_string("D A C A E", parser_class)
        self.assertEqual(
            node,
            [
                [
                    [
                        [
                            [
                                TokenInfo(
                                    type=NAME,
                                    string="D",
                                    start=(1, 0),
                                    end=(1, 1),
                                    line="D A C A E",
                                )
                            ],
                            TokenInfo(
                                type=NAME,
                                string="A",
                                start=(1, 2),
                                end=(1, 3),
                                line="D A C A E",
                            ),
                        ],
                        TokenInfo(
                            type=NAME,
                            string="C",
                            start=(1, 4),
                            end=(1, 5),
                            line="D A C A E",
                        ),
                    ],
                    TokenInfo(
                        type=NAME,
                        string="A",
                        start=(1, 6),
                        end=(1, 7),
                        line="D A C A E",
                    ),
                ],
                TokenInfo(
                    type=NAME, string="E", start=(1, 8), end=(1, 9), line="D A C A E"
                ),
            ],
        )
        node = parse_string("B C A E", parser_class)
        self.assertIsNotNone(node)
        self.assertEqual(
            node,
            [
                [
                    [
                        [
                            TokenInfo(
                                type=NAME,
                                string="B",
                                start=(1, 0),
                                end=(1, 1),
                                line="B C A E",
                            )
                        ],
                        TokenInfo(
                            type=NAME,
                            string="C",
                            start=(1, 2),
                            end=(1, 3),
                            line="B C A E",
                        ),
                    ],
                    TokenInfo(
                        type=NAME, string="A", start=(1, 4), end=(1, 5), line="B C A E"
                    ),
                ],
                TokenInfo(
                    type=NAME, string="E", start=(1, 6), end=(1, 7), line="B C A E"
                ),
            ],
        )

    def test_nasty_mutually_left_recursive(self) -> None:
        grammar_source = "\n        start: target '='\n        target: maybe '+' | NAME\n        maybe: maybe '-' | target\n        "
        grammar: Grammar = parse_string(grammar_source, GrammarParser)
        out = io.StringIO()
        genr = PythonParserGenerator(grammar, out)
        genr.generate("<string>")
        ns: Dict[(str, Any)] = {}
        exec(out.getvalue(), ns)
        parser_class = ns["GeneratedParser"]
        with self.assertRaises(SyntaxError):
            parse_string("x - + =", parser_class)

    def test_lookahead(self) -> None:
        grammar = "\n        start: (expr_stmt | assign_stmt) &'.'\n        expr_stmt: !(target '=') expr\n        assign_stmt: target '=' expr\n        expr: term ('+' term)*\n        target: NAME\n        term: NUMBER\n        "
        parser_class = make_parser(grammar)
        node = parse_string("foo = 12 + 12 .", parser_class)
        self.assertEqual(
            node,
            [
                [
                    [
                        [
                            TokenInfo(
                                NAME,
                                string="foo",
                                start=(1, 0),
                                end=(1, 3),
                                line="foo = 12 + 12 .",
                            )
                        ],
                        TokenInfo(
                            OP,
                            string="=",
                            start=(1, 4),
                            end=(1, 5),
                            line="foo = 12 + 12 .",
                        ),
                        [
                            [
                                TokenInfo(
                                    NUMBER,
                                    string="12",
                                    start=(1, 6),
                                    end=(1, 8),
                                    line="foo = 12 + 12 .",
                                )
                            ],
                            [
                                [
                                    [
                                        TokenInfo(
                                            OP,
                                            string="+",
                                            start=(1, 9),
                                            end=(1, 10),
                                            line="foo = 12 + 12 .",
                                        ),
                                        [
                                            TokenInfo(
                                                NUMBER,
                                                string="12",
                                                start=(1, 11),
                                                end=(1, 13),
                                                line="foo = 12 + 12 .",
                                            )
                                        ],
                                    ]
                                ]
                            ],
                        ],
                    ]
                ]
            ],
        )

    def test_named_lookahead_error(self) -> None:
        grammar = "\n        start: foo=!'x' NAME\n        "
        with self.assertRaises(SyntaxError):
            make_parser(grammar)

    def test_start_leader(self) -> None:
        grammar = "\n        start: attr | NAME\n        attr: start '.' NAME\n        "
        make_parser(grammar)

    def test_opt_sequence(self) -> None:
        grammar = "\n        start: [NAME*]\n        "
        make_parser(grammar)

    def test_left_recursion_too_complex(self) -> None:
        grammar = "\n        start: foo\n        foo: bar '+' | baz '+' | '+'\n        bar: baz '-' | foo '-' | '-'\n        baz: foo '*' | bar '*' | '*'\n        "
        with self.assertRaises(ValueError) as errinfo:
            make_parser(grammar)
            self.assertTrue(("no leader" in str(errinfo.exception.value)))

    def test_cut(self) -> None:
        grammar = "\n        start: '(' ~ expr ')'\n        expr: NUMBER\n        "
        parser_class = make_parser(grammar)
        node = parse_string("(1)", parser_class)
        self.assertEqual(
            node,
            [
                TokenInfo(OP, string="(", start=(1, 0), end=(1, 1), line="(1)"),
                [TokenInfo(NUMBER, string="1", start=(1, 1), end=(1, 2), line="(1)")],
                TokenInfo(OP, string=")", start=(1, 2), end=(1, 3), line="(1)"),
            ],
        )

    def test_dangling_reference(self) -> None:
        grammar = "\n        start: foo ENDMARKER\n        foo: bar NAME\n        "
        with self.assertRaises(GrammarError):
            parser_class = make_parser(grammar)

    def test_bad_token_reference(self) -> None:
        grammar = "\n        start: foo\n        foo: NAMEE\n        "
        with self.assertRaises(GrammarError):
            parser_class = make_parser(grammar)

    def test_missing_start(self) -> None:
        grammar = "\n        foo: NAME\n        "
        with self.assertRaises(GrammarError):
            parser_class = make_parser(grammar)

    def test_invalid_rule_name(self) -> None:
        grammar = "\n        start: _a b\n        _a: 'a'\n        b: 'b'\n        "
        with self.assertRaisesRegex(GrammarError, "cannot start with underscore: '_a'"):
            parser_class = make_parser(grammar)

    def test_invalid_variable_name(self) -> None:
        grammar = "\n        start: a b\n        a: _x='a'\n        b: 'b'\n        "
        with self.assertRaisesRegex(GrammarError, "cannot start with underscore: '_x'"):
            parser_class = make_parser(grammar)

    def test_invalid_variable_name_in_temporal_rule(self) -> None:
        grammar = "\n        start: a b\n        a: (_x='a' | 'b') | 'c'\n        b: 'b'\n        "
        with self.assertRaisesRegex(GrammarError, "cannot start with underscore: '_x'"):
            parser_class = make_parser(grammar)


class TestGrammarVisitor:
    class Visitor(GrammarVisitor):
        def __init__(self) -> None:
            self.n_nodes = 0

        def visit(self, node: Any, *args: Any, **kwargs: Any) -> None:
            self.n_nodes += 1
            super().visit(node, *args, **kwargs)

    def test_parse_trivial_grammar(self) -> None:
        grammar = "\n        start: 'a'\n        "
        rules = parse_string(grammar, GrammarParser)
        visitor = self.Visitor()
        visitor.visit(rules)
        self.assertEqual(visitor.n_nodes, 6)

    def test_parse_or_grammar(self) -> None:
        grammar = "\n        start: rule\n        rule: 'a' | 'b'\n        "
        rules = parse_string(grammar, GrammarParser)
        visitor = self.Visitor()
        visitor.visit(rules)
        self.assertEqual(visitor.n_nodes, 14)

    def test_parse_repeat1_grammar(self) -> None:
        grammar = "\n        start: 'a'+\n        "
        rules = parse_string(grammar, GrammarParser)
        visitor = self.Visitor()
        visitor.visit(rules)
        self.assertEqual(visitor.n_nodes, 7)

    def test_parse_repeat0_grammar(self) -> None:
        grammar = "\n        start: 'a'*\n        "
        rules = parse_string(grammar, GrammarParser)
        visitor = self.Visitor()
        visitor.visit(rules)
        self.assertEqual(visitor.n_nodes, 7)

    def test_parse_optional_grammar(self) -> None:
        grammar = "\n        start: 'a' ['b']\n        "
        rules = parse_string(grammar, GrammarParser)
        visitor = self.Visitor()
        visitor.visit(rules)
        self.assertEqual(visitor.n_nodes, 12)


class TestGrammarVisualizer(unittest.TestCase):
    def test_simple_rule(self) -> None:
        grammar = "\n        start: 'a' 'b'\n        "
        rules = parse_string(grammar, GrammarParser)
        printer = ASTGrammarPrinter()
        lines: List[str] = []
        printer.print_grammar_ast(rules, printer=lines.append)
        output = "\n".join(lines)
        expected_output = textwrap.dedent(
            "        └──Rule\n           └──Rhs\n              └──Alt\n                 ├──NamedItem\n                 │  └──StringLeaf(\"'a'\")\n                 └──NamedItem\n                    └──StringLeaf(\"'b'\")\n        "
        )
        self.assertEqual(output, expected_output)

    def test_multiple_rules(self) -> None:
        grammar = "\n        start: a b\n        a: 'a'\n        b: 'b'\n        "
        rules = parse_string(grammar, GrammarParser)
        printer = ASTGrammarPrinter()
        lines: List[str] = []
        printer.print_grammar_ast(rules, printer=lines.append)
        output = "\n".join(lines)
        expected_output = textwrap.dedent(
            "        └──Rule\n           └──Rhs\n              └──Alt\n                 ├──NamedItem\n                 │  └──NameLeaf('a')\n                 └──NamedItem\n                    └──NameLeaf('b')\n\n        └──Rule\n           └──Rhs\n              └──Alt\n                 └──NamedItem\n                    └──StringLeaf(\"'a'\")\n\n        └──Rule\n           └──Rhs\n              └──Alt\n                 └──NamedItem\n                    └──StringLeaf(\"'b'\")\n                        "
        )
        self.assertEqual(output, expected_output)

    def test_deep_nested_rule(self) -> None:
        grammar = "\n        start: 'a' ['b'['c'['d']]]\n        "
        rules = parse_string(grammar, GrammarParser)
        printer = ASTGrammarPrinter()
        lines: List[str] = []
        printer.print_grammar_ast(rules, printer=lines.append)
        output = "\n".join(lines)
        expected_output = textwrap.dedent(
            "        └──Rule\n           └──Rhs\n              └──Alt\n                 ├──NamedItem\n                 │  └──StringLeaf(\"'a'\")\n                 └──NamedItem\n                    └──Opt\n                       └──Rhs\n                          └──Alt\n                             ├──NamedItem\n                             │  └──StringLeaf(\"'b'\")\n                             └──NamedItem\n                                └──Opt\n                                   └──Rhs\n                                      └──Alt\n                                         ├──NamedItem\n                                         │  └──StringLeaf(\"'c'\")\n                                         └──NamedItem\n                                            └──Opt\n                                               └──Rhs\n                                                  └──Alt\n                                                     └──NamedItem\n                                                        └──StringLeaf(\"'d'\")\n                                "
        )
        self.assertEqual(output, expected_output)
