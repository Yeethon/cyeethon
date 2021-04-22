"Export the Python grammar and symbols."
import os
from .pgen2 import token
from .pgen2 import driver
from . import pytree

_GRAMMAR_FILE = os.path.join(os.path.dirname(__file__), "Grammar.txt")
_PATTERN_GRAMMAR_FILE = os.path.join(os.path.dirname(__file__), "PatternGrammar.txt")


class Symbols(object):
    def __init__(self, grammar):
        "Initializer.\n\n        Creates an attribute for each grammar symbol (nonterminal),\n        whose value is the symbol's type (an int >= 256).\n        "
        for (name, symbol) in grammar.symbol2number.items():
            setattr(self, name, symbol)


python_grammar = driver.load_packaged_grammar("lib2to3", _GRAMMAR_FILE)
python_symbols = Symbols(python_grammar)
python_grammar_no_print_statement = python_grammar.copy()
del python_grammar_no_print_statement.keywords["print"]
python_grammar_no_print_and_exec_statement = python_grammar_no_print_statement.copy()
del python_grammar_no_print_and_exec_statement.keywords["exec"]
pattern_grammar = driver.load_packaged_grammar("lib2to3", _PATTERN_GRAMMAR_FILE)
pattern_symbols = Symbols(pattern_grammar)
