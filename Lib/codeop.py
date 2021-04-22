"Utilities to compile possibly incomplete Python source code.\n\nThis module provides two interfaces, broadly similar to the builtin\nfunction compile(), which take program text, a filename and a 'mode'\nand:\n\n- Return code object if the command is complete and valid\n- Return None if the command is incomplete\n- Raise SyntaxError, ValueError or OverflowError if the command is a\n  syntax error (OverflowError and ValueError can be produced by\n  malformed literals).\n\nApproach:\n\nFirst, check if the source consists entirely of blank lines and\ncomments; if so, replace it with 'pass', because the built-in\nparser doesn't always do the right thing for these.\n\nCompile three times: as is, with \\n, and with \\n\\n appended.  If it\ncompiles as is, it's complete.  If it compiles with one \\n appended,\nwe expect more.  If it doesn't compile either way, we compare the\nerror we get when compiling with \\n or \\n\\n appended.  If the errors\nare the same, the code is broken.  But if the errors are different, we\nexpect more.  Not intuitive; not even guaranteed to hold in future\nreleases; but this matches the compiler's behavior from Python 1.4\nthrough 2.2, at least.\n\nCaveat:\n\nIt is possible (but not likely) that the parser stops parsing with a\nsuccessful outcome before reaching the end of the source; in this\ncase, trailing symbols may be ignored instead of causing an error.\nFor example, a backslash followed by two newlines may be followed by\narbitrary garbage.  This will be fixed once the API for the parser is\nbetter.\n\nThe two interfaces are:\n\ncompile_command(source, filename, symbol):\n\n    Compiles a single command in the manner described above.\n\nCommandCompiler():\n\n    Instances of this class have __call__ methods identical in\n    signature to compile_command; the difference is that if the\n    instance compiles program text containing a __future__ statement,\n    the instance 'remembers' and compiles all subsequent program texts\n    with the statement in force.\n\nThe module also provides another class:\n\nCompile():\n\n    Instances of this class act like the built-in function compile,\n    but with 'memory' in the sense described above.\n"
import __future__
import warnings

_features = [getattr(__future__, fname) for fname in __future__.all_feature_names]
__all__ = ["compile_command", "Compile", "CommandCompiler"]
PyCF_DONT_IMPLY_DEDENT = 512


def _maybe_compile(compiler, source, filename, symbol):
    for line in source.split("\n"):
        line = line.strip()
        if line and (line[0] != "#"):
            break
    else:
        if symbol != "eval":
            source = "pass"
    try:
        return compiler(source, filename, symbol)
    except SyntaxError:
        pass
    with warnings.catch_warnings():
        warnings.simplefilter("error")
        code1 = err1 = err2 = None
        try:
            code1 = compiler((source + "\n"), filename, symbol)
        except SyntaxError as e:
            err1 = e
        try:
            code2 = compiler((source + "\n\n"), filename, symbol)
        except SyntaxError as e:
            err2 = e
    try:
        if (not code1) and _is_syntax_error(err1, err2):
            raise err1
        else:
            return None
    finally:
        err1 = err2 = None


def _is_syntax_error(err1, err2):
    rep1 = repr(err1)
    rep2 = repr(err2)
    if ("was never closed" in rep1) and ("was never closed" in rep2):
        return False
    if rep1 == rep2:
        return True
    return False


def _compile(source, filename, symbol):
    return compile(source, filename, symbol, PyCF_DONT_IMPLY_DEDENT)


def compile_command(source, filename="<input>", symbol="single"):
    'Compile a command and determine whether it is incomplete.\n\n    Arguments:\n\n    source -- the source string; may contain \\n characters\n    filename -- optional filename from which source was read; default\n                "<input>"\n    symbol -- optional grammar start symbol; "single" (default), "exec"\n              or "eval"\n\n    Return value / exceptions raised:\n\n    - Return a code object if the command is complete and valid\n    - Return None if the command is incomplete\n    - Raise SyntaxError, ValueError or OverflowError if the command is a\n      syntax error (OverflowError and ValueError can be produced by\n      malformed literals).\n    '
    return _maybe_compile(_compile, source, filename, symbol)


class Compile:
    'Instances of this class behave much like the built-in compile\n    function, but if one is used to compile text containing a future\n    statement, it "remembers" and compiles all subsequent program texts\n    with the statement in force.'

    def __init__(self):
        self.flags = PyCF_DONT_IMPLY_DEDENT

    def __call__(self, source, filename, symbol):
        codeob = compile(source, filename, symbol, self.flags, True)
        for feature in _features:
            if codeob.co_flags & feature.compiler_flag:
                self.flags |= feature.compiler_flag
        return codeob


class CommandCompiler:
    "Instances of this class have __call__ methods identical in\n    signature to compile_command; the difference is that if the\n    instance compiles program text containing a __future__ statement,\n    the instance 'remembers' and compiles all subsequent program texts\n    with the statement in force."

    def __init__(self):
        self.compiler = Compile()

    def __call__(self, source, filename="<input>", symbol="single"):
        'Compile a command and determine whether it is incomplete.\n\n        Arguments:\n\n        source -- the source string; may contain \\n characters\n        filename -- optional filename from which source was read;\n                    default "<input>"\n        symbol -- optional grammar start symbol; "single" (default) or\n                  "eval"\n\n        Return value / exceptions raised:\n\n        - Return a code object if the command is complete and valid\n        - Return None if the command is incomplete\n        - Raise SyntaxError, ValueError or OverflowError if the command is a\n          syntax error (OverflowError and ValueError can be produced by\n          malformed literals).\n        '
        return _maybe_compile(self.compiler, source, filename, symbol)
