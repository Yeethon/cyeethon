import importlib.util
import io
import os
import pathlib
import sys
import textwrap
import tokenize
import token
from typing import Any, cast, Dict, IO, Type, Final
from pegen.build import compile_c_extension
from pegen.c_generator import CParserGenerator
from pegen.grammar import Grammar
from pegen.grammar_parser import GeneratedParser as GrammarParser
from pegen.parser import Parser
from pegen.python_generator import PythonParserGenerator
from pegen.tokenizer import Tokenizer

ALL_TOKENS = token.tok_name
EXACT_TOKENS = token.EXACT_TOKEN_TYPES
NON_EXACT_TOKENS = {
    name
    for (index, name) in token.tok_name.items()
    if (index not in EXACT_TOKENS.values())
}


def generate_parser(grammar: Grammar) -> Type[Parser]:
    out = io.StringIO()
    genr = PythonParserGenerator(grammar, out)
    genr.generate("<string>")
    ns: Dict[(str, Any)] = {}
    exec(out.getvalue(), ns)
    return ns["GeneratedParser"]


def run_parser(
    file: IO[bytes], parser_class: Type[Parser], *, verbose: bool = False
) -> Any:
    tokenizer = Tokenizer(tokenize.generate_tokens(file.readline))
    parser = parser_class(tokenizer, verbose=verbose)
    result = parser.start()
    if result is None:
        raise parser.make_syntax_error()
    return result


def parse_string(
    source: str,
    parser_class: Type[Parser],
    *,
    dedent: bool = True,
    verbose: bool = False,
) -> Any:
    if dedent:
        source = textwrap.dedent(source)
    file = io.StringIO(source)
    return run_parser(file, parser_class, verbose=verbose)


def make_parser(source: str) -> Type[Parser]:
    grammar = parse_string(source, GrammarParser)
    return generate_parser(grammar)


def import_file(full_name: str, path: str) -> Any:
    "Import a python module from a path"
    spec = importlib.util.spec_from_file_location(full_name, path)
    mod = importlib.util.module_from_spec(spec)
    loader = cast(Any, spec.loader)
    loader.exec_module(mod)
    return mod


def generate_c_parser_source(grammar: Grammar) -> str:
    out = io.StringIO()
    genr = CParserGenerator(grammar, ALL_TOKENS, EXACT_TOKENS, NON_EXACT_TOKENS, out)
    genr.generate("<string>")
    return out.getvalue()


def generate_parser_c_extension(
    grammar: Grammar, path: pathlib.PurePath, debug: bool = False
) -> Any:
    "Generate a parser c extension for the given grammar in the given path\n\n    Returns a module object with a parse_string() method.\n    TODO: express that using a Protocol.\n    "
    assert not os.listdir(path)
    source = path / "parse.c"
    with open(source, "w", encoding="utf-8") as file:
        genr = CParserGenerator(
            grammar, ALL_TOKENS, EXACT_TOKENS, NON_EXACT_TOKENS, file, debug=debug
        )
        genr.generate("parse.c")
    compile_c_extension(str(source), build_dir=str(path))


def print_memstats() -> bool:
    MiB: Final = 2 ** 20
    try:
        import psutil
    except ImportError:
        return False
    print("Memory stats:")
    process = psutil.Process()
    meminfo = process.memory_info()
    res = {}
    res["rss"] = meminfo.rss / MiB
    res["vms"] = meminfo.vms / MiB
    if sys.platform == "win32":
        res["maxrss"] = meminfo.peak_wset / MiB
    else:
        import resource

        rusage = resource.getrusage(resource.RUSAGE_SELF)
        if sys.platform == "darwin":
            factor = 1
        else:
            factor = 1024
        res["maxrss"] = (rusage.ru_maxrss * factor) / MiB
    for (key, value) in res.items():
        print(f"  {key:12.12s}: {value:10.0f} MiB")
    return True
