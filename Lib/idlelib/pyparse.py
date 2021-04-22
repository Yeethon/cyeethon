"Define partial Python code Parser used by editor and hyperparser.\n\nInstances of ParseMap are used with str.translate.\n\nThe following bound search and match functions are defined:\n_synchre - start of popular statement;\n_junkre - whitespace or comment line;\n_match_stringre: string, possibly without closer;\n_itemre - line that may have bracket structure start;\n_closere - line that must be followed by dedent.\n_chew_ordinaryre - non-special characters.\n"
import re

(C_NONE, C_BACKSLASH, C_STRING_FIRST_LINE, C_STRING_NEXT_LINES, C_BRACKET) = range(5)
_synchre = re.compile(
    "\n    ^\n    [ \\t]*\n    (?: while\n    |   else\n    |   def\n    |   return\n    |   assert\n    |   break\n    |   class\n    |   continue\n    |   elif\n    |   try\n    |   except\n    |   raise\n    |   import\n    |   yield\n    )\n    \\b\n",
    (re.VERBOSE | re.MULTILINE),
).search
_junkre = re.compile(
    "\n    [ \\t]*\n    (?: \\# \\S .* )?\n    \\n\n", re.VERBOSE
).match
_match_stringre = re.compile(
    "\n    \\\"\"\" [^\"\\\\]* (?:\n                     (?: \\\\. | \"(?!\"\") )\n                     [^\"\\\\]*\n                 )*\n    (?: \\\"\"\" )?\n\n|   \" [^\"\\\\\\n]* (?: \\\\. [^\"\\\\\\n]* )* \"?\n\n|   ''' [^'\\\\]* (?:\n                   (?: \\\\. | '(?!'') )\n                   [^'\\\\]*\n                )*\n    (?: ''' )?\n\n|   ' [^'\\\\\\n]* (?: \\\\. [^'\\\\\\n]* )* '?\n",
    (re.VERBOSE | re.DOTALL),
).match
_itemre = re.compile(
    "\n    [ \\t]*\n    [^\\s#\\\\]    # if we match, m.end()-1 is the interesting char\n",
    re.VERBOSE,
).match
_closere = re.compile(
    "\n    \\s*\n    (?: return\n    |   break\n    |   continue\n    |   raise\n    |   pass\n    )\n    \\b\n",
    re.VERBOSE,
).match
_chew_ordinaryre = re.compile("\n    [^[\\](){}#'\"\\\\]+\n", re.VERBOSE).match


class ParseMap(dict):
    "Dict subclass that maps anything not in dict to 'x'.\n\n    This is designed to be used with str.translate in study1.\n    Anything not specifically mapped otherwise becomes 'x'.\n    Example: replace everything except whitespace with 'x'.\n\n    >>> keepwhite = ParseMap((ord(c), ord(c)) for c in ' \\t\\n\\r')\n    >>> \"a + b\\tc\\nd\".translate(keepwhite)\n    'x x x\\tx\\nx'\n    "

    def __missing__(self, key):
        return 120


trans = ParseMap.fromkeys(range(128), 120)
trans.update(((ord(c), ord("(")) for c in "({["))
trans.update(((ord(c), ord(")")) for c in ")}]"))
trans.update(((ord(c), ord(c)) for c in "\"'\\\n#"))


class Parser:
    def __init__(self, indentwidth, tabwidth):
        self.indentwidth = indentwidth
        self.tabwidth = tabwidth

    def set_code(self, s):
        assert (len(s) == 0) or (s[(-1)] == "\n")
        self.code = s
        self.study_level = 0

    def find_good_parse_start(self, is_char_in_string):
        '\n        Return index of a good place to begin parsing, as close to the\n        end of the string as possible.  This will be the start of some\n        popular stmt like "if" or "def".  Return None if none found:\n        the caller should pass more prior context then, if possible, or\n        if not (the entire program text up until the point of interest\n        has already been tried) pass 0 to set_lo().\n\n        This will be reliable iff given a reliable is_char_in_string()\n        function, meaning that when it says "no", it\'s absolutely\n        guaranteed that the char is not in a string.\n        '
        (code, pos) = (self.code, None)
        limit = len(code)
        for tries in range(5):
            i = code.rfind(":\n", 0, limit)
            if i < 0:
                break
            i = code.rfind("\n", 0, i) + 1
            m = _synchre(code, i, limit)
            if m and (not is_char_in_string(m.start())):
                pos = m.start()
                break
            limit = i
        if pos is None:
            m = _synchre(code)
            if m and (not is_char_in_string(m.start())):
                pos = m.start()
            return pos
        i = pos + 1
        while 1:
            m = _synchre(code, i)
            if m:
                (s, i) = m.span()
                if not is_char_in_string(s):
                    pos = s
            else:
                break
        return pos

    def set_lo(self, lo):
        " Throw away the start of the string.\n\n        Intended to be called with the result of find_good_parse_start().\n        "
        assert (lo == 0) or (self.code[(lo - 1)] == "\n")
        if lo > 0:
            self.code = self.code[lo:]

    def _study1(self):
        "Find the line numbers of non-continuation lines.\n\n        As quickly as humanly possible <wink>, find the line numbers (0-\n        based) of the non-continuation lines.\n        Creates self.{goodlines, continuation}.\n        "
        if self.study_level >= 1:
            return
        self.study_level = 1
        code = self.code
        code = code.translate(trans)
        code = code.replace("xxxxxxxx", "x")
        code = code.replace("xxxx", "x")
        code = code.replace("xx", "x")
        code = code.replace("xx", "x")
        code = code.replace("\nx", "\n")
        continuation = C_NONE
        level = lno = 0
        self.goodlines = goodlines = [0]
        push_good = goodlines.append
        (i, n) = (0, len(code))
        while i < n:
            ch = code[i]
            i = i + 1
            if ch == "x":
                continue
            if ch == "\n":
                lno = lno + 1
                if level == 0:
                    push_good(lno)
                continue
            if ch == "(":
                level = level + 1
                continue
            if ch == ")":
                if level:
                    level = level - 1
                continue
            if (ch == '"') or (ch == "'"):
                quote = ch
                if code[(i - 1) : (i + 2)] == (quote * 3):
                    quote = quote * 3
                firstlno = lno
                w = len(quote) - 1
                i = i + w
                while i < n:
                    ch = code[i]
                    i = i + 1
                    if ch == "x":
                        continue
                    if code[(i - 1) : (i + w)] == quote:
                        i = i + w
                        break
                    if ch == "\n":
                        lno = lno + 1
                        if w == 0:
                            if level == 0:
                                push_good(lno)
                            break
                        continue
                    if ch == "\\":
                        assert i < n
                        if code[i] == "\n":
                            lno = lno + 1
                        i = i + 1
                        continue
                else:
                    if (lno - 1) == firstlno:
                        continuation = C_STRING_FIRST_LINE
                    else:
                        continuation = C_STRING_NEXT_LINES
                continue
            if ch == "#":
                i = code.find("\n", i)
                assert i >= 0
                continue
            assert ch == "\\"
            assert i < n
            if code[i] == "\n":
                lno = lno + 1
                if (i + 1) == n:
                    continuation = C_BACKSLASH
            i = i + 1
        if (
            (continuation != C_STRING_FIRST_LINE)
            and (continuation != C_STRING_NEXT_LINES)
            and (level > 0)
        ):
            continuation = C_BRACKET
        self.continuation = continuation
        assert (continuation == C_NONE) == (goodlines[(-1)] == lno)
        if goodlines[(-1)] != lno:
            push_good(lno)

    def get_continuation_type(self):
        self._study1()
        return self.continuation

    def _study2(self):
        '\n        study1 was sufficient to determine the continuation status,\n        but doing more requires looking at every character.  study2\n        does this for the last interesting statement in the block.\n        Creates:\n            self.stmt_start, stmt_end\n                slice indices of last interesting stmt\n            self.stmt_bracketing\n                the bracketing structure of the last interesting stmt; for\n                example, for the statement "say(boo) or die",\n                stmt_bracketing will be ((0, 0), (0, 1), (2, 0), (2, 1),\n                (4, 0)). Strings and comments are treated as brackets, for\n                the matter.\n            self.lastch\n                last interesting character before optional trailing comment\n            self.lastopenbracketpos\n                if continuation is C_BRACKET, index of last open bracket\n        '
        if self.study_level >= 2:
            return
        self._study1()
        self.study_level = 2
        (code, goodlines) = (self.code, self.goodlines)
        i = len(goodlines) - 1
        p = len(code)
        while i:
            assert p
            q = p
            for nothing in range(goodlines[(i - 1)], goodlines[i]):
                p = code.rfind("\n", 0, (p - 1)) + 1
            if _junkre(code, p):
                i = i - 1
            else:
                break
        if i == 0:
            assert p == 0
            q = p
        (self.stmt_start, self.stmt_end) = (p, q)
        lastch = ""
        stack = []
        push_stack = stack.append
        bracketing = [(p, 0)]
        while p < q:
            m = _chew_ordinaryre(code, p, q)
            if m:
                newp = m.end()
                i = newp - 1
                while (i >= p) and (code[i] in " \t\n"):
                    i = i - 1
                if i >= p:
                    lastch = code[i]
                p = newp
                if p >= q:
                    break
            ch = code[p]
            if ch in "([{":
                push_stack(p)
                bracketing.append((p, len(stack)))
                lastch = ch
                p = p + 1
                continue
            if ch in ")]}":
                if stack:
                    del stack[(-1)]
                lastch = ch
                p = p + 1
                bracketing.append((p, len(stack)))
                continue
            if (ch == '"') or (ch == "'"):
                bracketing.append((p, (len(stack) + 1)))
                lastch = ch
                p = _match_stringre(code, p, q).end()
                bracketing.append((p, len(stack)))
                continue
            if ch == "#":
                bracketing.append((p, (len(stack) + 1)))
                p = code.find("\n", p, q) + 1
                assert p > 0
                bracketing.append((p, len(stack)))
                continue
            assert ch == "\\"
            p = p + 1
            assert p < q
            if code[p] != "\n":
                lastch = ch + code[p]
            p = p + 1
        self.lastch = lastch
        self.lastopenbracketpos = stack[(-1)] if stack else None
        self.stmt_bracketing = tuple(bracketing)

    def compute_bracket_indent(self):
        "Return number of spaces the next line should be indented.\n\n        Line continuation must be C_BRACKET.\n        "
        self._study2()
        assert self.continuation == C_BRACKET
        j = self.lastopenbracketpos
        code = self.code
        n = len(code)
        origi = i = code.rfind("\n", 0, j) + 1
        j = j + 1
        while j < n:
            m = _itemre(code, j)
            if m:
                j = m.end() - 1
                extra = 0
                break
            else:
                i = j = code.find("\n", j) + 1
        else:
            j = i = origi
            while code[j] in " \t":
                j = j + 1
            extra = self.indentwidth
        return len(code[i:j].expandtabs(self.tabwidth)) + extra

    def get_num_lines_in_stmt(self):
        "Return number of physical lines in last stmt.\n\n        The statement doesn't have to be an interesting statement.  This is\n        intended to be called when continuation is C_BACKSLASH.\n        "
        self._study1()
        goodlines = self.goodlines
        return goodlines[(-1)] - goodlines[(-2)]

    def compute_backslash_indent(self):
        "Return number of spaces the next line should be indented.\n\n        Line continuation must be C_BACKSLASH.  Also assume that the new\n        line is the first one following the initial line of the stmt.\n        "
        self._study2()
        assert self.continuation == C_BACKSLASH
        code = self.code
        i = self.stmt_start
        while code[i] in " \t":
            i = i + 1
        startpos = i
        endpos = code.find("\n", startpos) + 1
        found = level = 0
        while i < endpos:
            ch = code[i]
            if ch in "([{":
                level = level + 1
                i = i + 1
            elif ch in ")]}":
                if level:
                    level = level - 1
                i = i + 1
            elif (ch == '"') or (ch == "'"):
                i = _match_stringre(code, i, endpos).end()
            elif ch == "#":
                break
            elif (
                (level == 0)
                and (ch == "=")
                and ((i == 0) or (code[(i - 1)] not in "=<>!"))
                and (code[(i + 1)] != "=")
            ):
                found = 1
                break
            else:
                i = i + 1
        if found:
            i = i + 1
            found = re.match("\\s*\\\\", code[i:endpos]) is None
        if not found:
            i = startpos
            while code[i] not in " \t\n":
                i = i + 1
        return len(code[self.stmt_start : i].expandtabs(self.tabwidth)) + 1

    def get_base_indent_string(self):
        "Return the leading whitespace on the initial line of the last\n        interesting stmt.\n        "
        self._study2()
        (i, n) = (self.stmt_start, self.stmt_end)
        j = i
        code = self.code
        while (j < n) and (code[j] in " \t"):
            j = j + 1
        return code[i:j]

    def is_block_opener(self):
        "Return True if the last interesting statement opens a block."
        self._study2()
        return self.lastch == ":"

    def is_block_closer(self):
        "Return True if the last interesting statement closes a block."
        self._study2()
        return _closere(self.code, self.stmt_start) is not None

    def get_last_stmt_bracketing(self):
        "Return bracketing structure of the last interesting statement.\n\n        The returned tuple is in the format defined in _study2().\n        "
        self._study2()
        return self.stmt_bracketing


if __name__ == "__main__":
    from unittest import main

    main("idlelib.idle_test.test_pyparse", verbosity=2)
