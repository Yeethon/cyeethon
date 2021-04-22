'A simple non-validating parser for C99.\n\nThe functions and regex patterns here are not entirely suitable for\nvalidating C syntax.  Please rely on a proper compiler for that.\nInstead our goal here is merely matching and extracting information from\nvalid C code.\n\nFurthermore, the grammar rules for the C syntax (particularly as\ndescribed in the K&R book) actually describe a superset, of which the\nfull C langage is a proper subset.  Here are some of the extra\nconditions that must be applied when parsing C code:\n\n* ...\n\n(see: http://www.open-std.org/jtc1/sc22/wg14/www/docs/n1256.pdf)\n\nWe have taken advantage of the elements of the C grammar that are used\nonly in a few limited contexts, mostly as delimiters.  They allow us to\nfocus the regex patterns confidently.  Here are the relevant tokens and\nin which grammar rules they are used:\n\nseparators:\n* ";"\n   + (decl) struct/union:  at end of each member decl\n   + (decl) declaration:  at end of each (non-compound) decl\n   + (stmt) expr stmt:  at end of each stmt\n   + (stmt) for:  between exprs in "header"\n   + (stmt) goto:  at end\n   + (stmt) continue:  at end\n   + (stmt) break:  at end\n   + (stmt) return:  at end\n* ","\n   + (decl) struct/union:  between member declators\n   + (decl) param-list:  between params\n   + (decl) enum: between enumerators\n   + (decl) initializer (compound):  between initializers\n   + (expr) postfix:  between func call args\n   + (expr) expression:  between "assignment" exprs\n* ":"\n   + (decl) struct/union:  in member declators\n   + (stmt) label:  between label and stmt\n   + (stmt) case:  between expression and stmt\n   + (stmt) default:  between "default" and stmt\n* "="\n   + (decl) delaration:  between decl and initializer\n   + (decl) enumerator:  between identifier and "initializer"\n   + (expr) assignment:  between "var" and expr\n\nwrappers:\n* "(...)"\n   + (decl) declarator (func ptr):  to wrap ptr/name\n   + (decl) declarator (func ptr):  around params\n   + (decl) declarator:  around sub-declarator (for readability)\n   + (expr) postfix (func call):  around args\n   + (expr) primary:  around sub-expr\n   + (stmt) if:  around condition\n   + (stmt) switch:  around source expr\n   + (stmt) while:  around condition\n   + (stmt) do-while:  around condition\n   + (stmt) for:  around "header"\n* "{...}"\n   + (decl) enum:  around enumerators\n   + (decl) func:  around body\n   + (stmt) compound:  around stmts\n* "[...]"\n   * (decl) declarator:  for arrays\n   * (expr) postfix:  array access\n\nother:\n* "*"\n   + (decl) declarator:  for pointer types\n   + (expr) unary:  for pointer deref\n\n\nTo simplify the regular expressions used here, we\'ve takens some\nshortcuts and made certain assumptions about the code we are parsing.\nSome of these allow us to skip context-sensitive matching (e.g. braces)\nor otherwise still match arbitrary C code unambiguously.  However, in\nsome cases there are certain corner cases where the patterns are\nambiguous relative to arbitrary C code.  However, they are still\nunambiguous in the specific code we are parsing.\n\nHere are the cases where we\'ve taken shortcuts or made assumptions:\n\n* there is no overlap syntactically between the local context (func\n  bodies) and the global context (other than variable decls), so we\n  do not need to worry about ambiguity due to the overlap:\n   + the global context has no expressions or statements\n   + the local context has no function definitions or type decls\n* no "inline" type declarations (struct, union, enum) in function\n  parameters ~(including function pointers)~\n* no "inline" type decls in function return types\n* no superflous parentheses in declarators\n* var decls in for loops are always "simple" (e.g. no inline types)\n* only inline struct/union/enum decls may be anonymouns (without a name)\n* no function pointers in function pointer parameters\n* for loop "headers" do not have curly braces (e.g. compound init)\n* syntactically, variable decls do not overlap with stmts/exprs, except\n  in the following case:\n    spam (*eggs) (...)\n  This could be either a function pointer variable named "eggs"\n  or a call to a function named "spam", which returns a function\n  pointer that gets called.  The only differentiator is the\n  syntax used in the "..." part.  It will be comma-separated\n  parameters for the former and comma-separated expressions for\n  the latter.  Thus, if we expect such decls or calls then we must\n  parse the decl params.\n'
'\nTODO:\n* extract CPython-specific code\n* drop include injection (or only add when needed)\n* track position instead of slicing "text"\n* Parser class instead of the _iter_source() mess\n* alt impl using a state machine (& tokenizer or split on delimiters)\n'
from ..info import ParsedItem
from ._info import SourceInfo


def parse(srclines):
    if isinstance(srclines, str):
        raise NotImplementedError
    anon_name = anonymous_names()
    for result in _parse(srclines, anon_name):
        (yield ParsedItem.from_raw(result))


def anonymous_names():
    counter = 1

    def anon_name(prefix="anon-"):
        nonlocal counter
        name = f"{prefix}{counter}"
        counter += 1
        return name

    return anon_name


import logging

_logger = logging.getLogger(__name__)


def _parse(srclines, anon_name):
    from ._global import parse_globals

    source = _iter_source(srclines)
    for result in parse_globals(source, anon_name):
        (yield result)


def _iter_source(lines, *, maxtext=20000, maxlines=700, showtext=False):
    maxtext = maxtext if (maxtext and (maxtext > 0)) else None
    maxlines = maxlines if (maxlines and (maxlines > 0)) else None
    filestack = []
    allinfo = {}
    for (fileinfo, line) in lines:
        if fileinfo.filename in filestack:
            while fileinfo.filename != filestack[(-1)]:
                filename = filestack.pop()
                del allinfo[filename]
            filename = fileinfo.filename
            srcinfo = allinfo[filename]
        else:
            filename = fileinfo.filename
            srcinfo = SourceInfo(filename)
            filestack.append(filename)
            allinfo[filename] = srcinfo
        _logger.debug(f"-> {line}")
        srcinfo._add_line(line, fileinfo.lno)
        if srcinfo.too_much(maxtext, maxlines):
            break
        while srcinfo._used():
            (yield srcinfo)
            if showtext:
                _logger.debug(f"=> {srcinfo.text}")
    else:
        if not filestack:
            srcinfo = SourceInfo("???")
        else:
            filename = filestack[(-1)]
            srcinfo = allinfo[filename]
            while srcinfo._used():
                (yield srcinfo)
                if showtext:
                    _logger.debug(f"=> {srcinfo.text}")
        (yield srcinfo)
        if showtext:
            _logger.debug(f"=> {srcinfo.text}")
        if not srcinfo._ready:
            return
    (filename, lno, text) = (srcinfo.filename, srcinfo._start, srcinfo.text)
    if len(text) > 500:
        text = text[:500] + "..."
    raise Exception(
        f"""unmatched text ({filename} starting at line {lno}):
{text}"""
    )
