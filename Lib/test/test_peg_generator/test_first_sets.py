import unittest
from test import test_tools
from typing import Dict, Set

test_tools.skip_if_missing("peg_generator")
with test_tools.imports_under_tool("peg_generator"):
    from pegen.grammar_parser import GeneratedParser as GrammarParser
    from pegen.testutil import parse_string
    from pegen.first_sets import FirstSetCalculator
    from pegen.grammar import Grammar


class TestFirstSets(unittest.TestCase):
    def calculate_first_sets(self, grammar_source: str) -> Dict[(str, Set[str])]:
        grammar: Grammar = parse_string(grammar_source, GrammarParser)
        return FirstSetCalculator(grammar.rules).calculate()

    def test_alternatives(self) -> None:
        grammar = "\n            start: expr NEWLINE? ENDMARKER\n            expr: A | B\n            A: 'a' | '-'\n            B: 'b' | '+'\n        "
        self.assertEqual(
            self.calculate_first_sets(grammar),
            {
                "A": {"'a'", "'-'"},
                "B": {"'+'", "'b'"},
                "expr": {"'+'", "'a'", "'b'", "'-'"},
                "start": {"'+'", "'a'", "'b'", "'-'"},
            },
        )

    def test_optionals(self) -> None:
        grammar = "\n            start: expr NEWLINE\n            expr: ['a'] ['b'] 'c'\n        "
        self.assertEqual(
            self.calculate_first_sets(grammar),
            {"expr": {"'c'", "'a'", "'b'"}, "start": {"'c'", "'a'", "'b'"}},
        )

    def test_repeat_with_separator(self) -> None:
        grammar = "\n        start: ','.thing+ NEWLINE\n        thing: NUMBER\n        "
        self.assertEqual(
            self.calculate_first_sets(grammar),
            {"thing": {"NUMBER"}, "start": {"NUMBER"}},
        )

    def test_optional_operator(self) -> None:
        grammar = "\n        start: sum NEWLINE\n        sum: (term)? 'b'\n        term: NUMBER\n        "
        self.assertEqual(
            self.calculate_first_sets(grammar),
            {"term": {"NUMBER"}, "sum": {"NUMBER", "'b'"}, "start": {"'b'", "NUMBER"}},
        )

    def test_optional_literal(self) -> None:
        grammar = "\n        start: sum NEWLINE\n        sum: '+' ? term\n        term: NUMBER\n        "
        self.assertEqual(
            self.calculate_first_sets(grammar),
            {"term": {"NUMBER"}, "sum": {"'+'", "NUMBER"}, "start": {"'+'", "NUMBER"}},
        )

    def test_optional_after(self) -> None:
        grammar = "\n        start: term NEWLINE\n        term: NUMBER ['+']\n        "
        self.assertEqual(
            self.calculate_first_sets(grammar),
            {"term": {"NUMBER"}, "start": {"NUMBER"}},
        )

    def test_optional_before(self) -> None:
        grammar = "\n        start: term NEWLINE\n        term: ['+'] NUMBER\n        "
        self.assertEqual(
            self.calculate_first_sets(grammar),
            {"term": {"NUMBER", "'+'"}, "start": {"NUMBER", "'+'"}},
        )

    def test_repeat_0(self) -> None:
        grammar = '\n        start: thing* "+" NEWLINE\n        thing: NUMBER\n        '
        self.assertEqual(
            self.calculate_first_sets(grammar),
            {"thing": {"NUMBER"}, "start": {'"+"', "NUMBER"}},
        )

    def test_repeat_0_with_group(self) -> None:
        grammar = (
            "\n        start: ('+' '-')* term NEWLINE\n        term: NUMBER\n        "
        )
        self.assertEqual(
            self.calculate_first_sets(grammar),
            {"term": {"NUMBER"}, "start": {"'+'", "NUMBER"}},
        )

    def test_repeat_1(self) -> None:
        grammar = "\n        start: thing+ '-' NEWLINE\n        thing: NUMBER\n        "
        self.assertEqual(
            self.calculate_first_sets(grammar),
            {"thing": {"NUMBER"}, "start": {"NUMBER"}},
        )

    def test_repeat_1_with_group(self) -> None:
        grammar = (
            "\n        start: ('+' term)+ term NEWLINE\n        term: NUMBER\n        "
        )
        self.assertEqual(
            self.calculate_first_sets(grammar), {"term": {"NUMBER"}, "start": {"'+'"}}
        )

    def test_gather(self) -> None:
        grammar = "\n        start: ','.thing+ NEWLINE\n        thing: NUMBER\n        "
        self.assertEqual(
            self.calculate_first_sets(grammar),
            {"thing": {"NUMBER"}, "start": {"NUMBER"}},
        )

    def test_positive_lookahead(self) -> None:
        grammar = "\n        start: expr NEWLINE\n        expr: &'a' opt\n        opt: 'a' | 'b' | 'c'\n        "
        self.assertEqual(
            self.calculate_first_sets(grammar),
            {"expr": {"'a'"}, "start": {"'a'"}, "opt": {"'b'", "'c'", "'a'"}},
        )

    def test_negative_lookahead(self) -> None:
        grammar = "\n        start: expr NEWLINE\n        expr: !'a' opt\n        opt: 'a' | 'b' | 'c'\n        "
        self.assertEqual(
            self.calculate_first_sets(grammar),
            {
                "opt": {"'b'", "'a'", "'c'"},
                "expr": {"'b'", "'c'"},
                "start": {"'b'", "'c'"},
            },
        )

    def test_left_recursion(self) -> None:
        grammar = "\n        start: expr NEWLINE\n        expr: ('-' term | expr '+' term | term)\n        term: NUMBER\n        foo: 'foo'\n        bar: 'bar'\n        baz: 'baz'\n        "
        self.assertEqual(
            self.calculate_first_sets(grammar),
            {
                "expr": {"NUMBER", "'-'"},
                "term": {"NUMBER"},
                "start": {"NUMBER", "'-'"},
                "foo": {"'foo'"},
                "bar": {"'bar'"},
                "baz": {"'baz'"},
            },
        )

    def test_advance_left_recursion(self) -> None:
        grammar = "\n        start: NUMBER | sign start\n        sign: ['-']\n        "
        self.assertEqual(
            self.calculate_first_sets(grammar),
            {"sign": {"'-'", ""}, "start": {"'-'", "NUMBER"}},
        )

    def test_mutual_left_recursion(self) -> None:
        grammar = "\n        start: foo 'E'\n        foo: bar 'A' | 'B'\n        bar: foo 'C' | 'D'\n        "
        self.assertEqual(
            self.calculate_first_sets(grammar),
            {"foo": {"'D'", "'B'"}, "bar": {"'D'"}, "start": {"'D'", "'B'"}},
        )

    def test_nasty_left_recursion(self) -> None:
        grammar = "\n        start: target '='\n        target: maybe '+' | NAME\n        maybe: maybe '-' | target\n        "
        self.assertEqual(
            self.calculate_first_sets(grammar),
            {"maybe": set(), "target": {"NAME"}, "start": {"NAME"}},
        )

    def test_nullable_rule(self) -> None:
        grammar = "\n        start: sign thing $\n        sign: ['-']\n        thing: NUMBER\n        "
        self.assertEqual(
            self.calculate_first_sets(grammar),
            {"sign": {"", "'-'"}, "thing": {"NUMBER"}, "start": {"NUMBER", "'-'"}},
        )

    def test_epsilon_production_in_start_rule(self) -> None:
        grammar = "\n        start: ['-'] $\n        "
        self.assertEqual(
            self.calculate_first_sets(grammar), {"start": {"ENDMARKER", "'-'"}}
        )

    def test_multiple_nullable_rules(self) -> None:
        grammar = "\n        start: sign thing other another $\n        sign: ['-']\n        thing: ['+']\n        other: '*'\n        another: '/'\n        "
        self.assertEqual(
            self.calculate_first_sets(grammar),
            {
                "sign": {"", "'-'"},
                "thing": {"'+'", ""},
                "start": {"'+'", "'-'", "'*'"},
                "other": {"'*'"},
                "another": {"'/'"},
            },
        )
