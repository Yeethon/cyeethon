'\nModule difflib -- helpers for computing deltas between objects.\n\nFunction get_close_matches(word, possibilities, n=3, cutoff=0.6):\n    Use SequenceMatcher to return list of the best "good enough" matches.\n\nFunction context_diff(a, b):\n    For two lists of strings, return a delta in context diff format.\n\nFunction ndiff(a, b):\n    Return a delta: the difference between `a` and `b` (lists of strings).\n\nFunction restore(delta, which):\n    Return one of the two sequences that generated an ndiff delta.\n\nFunction unified_diff(a, b):\n    For two lists of strings, return a delta in unified diff format.\n\nClass SequenceMatcher:\n    A flexible class for comparing pairs of sequences of any type.\n\nClass Differ:\n    For producing human-readable deltas from sequences of lines of text.\n\nClass HtmlDiff:\n    For producing HTML side by side comparison with change highlights.\n'
__all__ = [
    "get_close_matches",
    "ndiff",
    "restore",
    "SequenceMatcher",
    "Differ",
    "IS_CHARACTER_JUNK",
    "IS_LINE_JUNK",
    "context_diff",
    "unified_diff",
    "diff_bytes",
    "HtmlDiff",
    "Match",
]
from heapq import nlargest as _nlargest
from collections import namedtuple as _namedtuple
from types import GenericAlias

Match = _namedtuple("Match", "a b size")


def _calculate_ratio(matches, length):
    if length:
        return (2.0 * matches) / length
    return 1.0


class SequenceMatcher:
    '\n    SequenceMatcher is a flexible class for comparing pairs of sequences of\n    any type, so long as the sequence elements are hashable.  The basic\n    algorithm predates, and is a little fancier than, an algorithm\n    published in the late 1980\'s by Ratcliff and Obershelp under the\n    hyperbolic name "gestalt pattern matching".  The basic idea is to find\n    the longest contiguous matching subsequence that contains no "junk"\n    elements (R-O doesn\'t address junk).  The same idea is then applied\n    recursively to the pieces of the sequences to the left and to the right\n    of the matching subsequence.  This does not yield minimal edit\n    sequences, but does tend to yield matches that "look right" to people.\n\n    SequenceMatcher tries to compute a "human-friendly diff" between two\n    sequences.  Unlike e.g. UNIX(tm) diff, the fundamental notion is the\n    longest *contiguous* & junk-free matching subsequence.  That\'s what\n    catches peoples\' eyes.  The Windows(tm) windiff has another interesting\n    notion, pairing up elements that appear uniquely in each sequence.\n    That, and the method here, appear to yield more intuitive difference\n    reports than does diff.  This method appears to be the least vulnerable\n    to synching up on blocks of "junk lines", though (like blank lines in\n    ordinary text files, or maybe "<P>" lines in HTML files).  That may be\n    because this is the only method of the 3 that has a *concept* of\n    "junk" <wink>.\n\n    Example, comparing two strings, and considering blanks to be "junk":\n\n    >>> s = SequenceMatcher(lambda x: x == " ",\n    ...                     "private Thread currentThread;",\n    ...                     "private volatile Thread currentThread;")\n    >>>\n\n    .ratio() returns a float in [0, 1], measuring the "similarity" of the\n    sequences.  As a rule of thumb, a .ratio() value over 0.6 means the\n    sequences are close matches:\n\n    >>> print(round(s.ratio(), 3))\n    0.866\n    >>>\n\n    If you\'re only interested in where the sequences match,\n    .get_matching_blocks() is handy:\n\n    >>> for block in s.get_matching_blocks():\n    ...     print("a[%d] and b[%d] match for %d elements" % block)\n    a[0] and b[0] match for 8 elements\n    a[8] and b[17] match for 21 elements\n    a[29] and b[38] match for 0 elements\n\n    Note that the last tuple returned by .get_matching_blocks() is always a\n    dummy, (len(a), len(b), 0), and this is the only case in which the last\n    tuple element (number of elements matched) is 0.\n\n    If you want to know how to change the first sequence into the second,\n    use .get_opcodes():\n\n    >>> for opcode in s.get_opcodes():\n    ...     print("%6s a[%d:%d] b[%d:%d]" % opcode)\n     equal a[0:8] b[0:8]\n    insert a[8:8] b[8:17]\n     equal a[8:29] b[17:38]\n\n    See the Differ class for a fancy human-friendly file differencer, which\n    uses SequenceMatcher both to compare sequences of lines, and to compare\n    sequences of characters within similar (near-matching) lines.\n\n    See also function get_close_matches() in this module, which shows how\n    simple code building on SequenceMatcher can be used to do useful work.\n\n    Timing:  Basic R-O is cubic time worst case and quadratic time expected\n    case.  SequenceMatcher is quadratic time for the worst case and has\n    expected-case behavior dependent in a complicated way on how many\n    elements the sequences have in common; best case time is linear.\n\n    Methods:\n\n    __init__(isjunk=None, a=\'\', b=\'\')\n        Construct a SequenceMatcher.\n\n    set_seqs(a, b)\n        Set the two sequences to be compared.\n\n    set_seq1(a)\n        Set the first sequence to be compared.\n\n    set_seq2(b)\n        Set the second sequence to be compared.\n\n    find_longest_match(alo=0, ahi=None, blo=0, bhi=None)\n        Find longest matching block in a[alo:ahi] and b[blo:bhi].\n\n    get_matching_blocks()\n        Return list of triples describing matching subsequences.\n\n    get_opcodes()\n        Return list of 5-tuples describing how to turn a into b.\n\n    ratio()\n        Return a measure of the sequences\' similarity (float in [0,1]).\n\n    quick_ratio()\n        Return an upper bound on .ratio() relatively quickly.\n\n    real_quick_ratio()\n        Return an upper bound on ratio() very quickly.\n    '

    def __init__(self, isjunk=None, a="", b="", autojunk=True):
        'Construct a SequenceMatcher.\n\n        Optional arg isjunk is None (the default), or a one-argument\n        function that takes a sequence element and returns true iff the\n        element is junk.  None is equivalent to passing "lambda x: 0", i.e.\n        no elements are considered to be junk.  For example, pass\n            lambda x: x in " \\t"\n        if you\'re comparing lines as sequences of characters, and don\'t\n        want to synch up on blanks or hard tabs.\n\n        Optional arg a is the first of two sequences to be compared.  By\n        default, an empty string.  The elements of a must be hashable.  See\n        also .set_seqs() and .set_seq1().\n\n        Optional arg b is the second of two sequences to be compared.  By\n        default, an empty string.  The elements of b must be hashable. See\n        also .set_seqs() and .set_seq2().\n\n        Optional arg autojunk should be set to False to disable the\n        "automatic junk heuristic" that treats popular elements as junk\n        (see module documentation for more information).\n        '
        self.isjunk = isjunk
        self.a = self.b = None
        self.autojunk = autojunk
        self.set_seqs(a, b)

    def set_seqs(self, a, b):
        'Set the two sequences to be compared.\n\n        >>> s = SequenceMatcher()\n        >>> s.set_seqs("abcd", "bcde")\n        >>> s.ratio()\n        0.75\n        '
        self.set_seq1(a)
        self.set_seq2(b)

    def set_seq1(self, a):
        'Set the first sequence to be compared.\n\n        The second sequence to be compared is not changed.\n\n        >>> s = SequenceMatcher(None, "abcd", "bcde")\n        >>> s.ratio()\n        0.75\n        >>> s.set_seq1("bcde")\n        >>> s.ratio()\n        1.0\n        >>>\n\n        SequenceMatcher computes and caches detailed information about the\n        second sequence, so if you want to compare one sequence S against\n        many sequences, use .set_seq2(S) once and call .set_seq1(x)\n        repeatedly for each of the other sequences.\n\n        See also set_seqs() and set_seq2().\n        '
        if a is self.a:
            return
        self.a = a
        self.matching_blocks = self.opcodes = None

    def set_seq2(self, b):
        'Set the second sequence to be compared.\n\n        The first sequence to be compared is not changed.\n\n        >>> s = SequenceMatcher(None, "abcd", "bcde")\n        >>> s.ratio()\n        0.75\n        >>> s.set_seq2("abcd")\n        >>> s.ratio()\n        1.0\n        >>>\n\n        SequenceMatcher computes and caches detailed information about the\n        second sequence, so if you want to compare one sequence S against\n        many sequences, use .set_seq2(S) once and call .set_seq1(x)\n        repeatedly for each of the other sequences.\n\n        See also set_seqs() and set_seq1().\n        '
        if b is self.b:
            return
        self.b = b
        self.matching_blocks = self.opcodes = None
        self.fullbcount = None
        self.__chain_b()

    def __chain_b(self):
        b = self.b
        self.b2j = b2j = {}
        for (i, elt) in enumerate(b):
            indices = b2j.setdefault(elt, [])
            indices.append(i)
        self.bjunk = junk = set()
        isjunk = self.isjunk
        if isjunk:
            for elt in b2j.keys():
                if isjunk(elt):
                    junk.add(elt)
            for elt in junk:
                del b2j[elt]
        self.bpopular = popular = set()
        n = len(b)
        if self.autojunk and (n >= 200):
            ntest = (n // 100) + 1
            for (elt, idxs) in b2j.items():
                if len(idxs) > ntest:
                    popular.add(elt)
            for elt in popular:
                del b2j[elt]

    def find_longest_match(self, alo=0, ahi=None, blo=0, bhi=None):
        'Find longest matching block in a[alo:ahi] and b[blo:bhi].\n\n        By default it will find the longest match in the entirety of a and b.\n\n        If isjunk is not defined:\n\n        Return (i,j,k) such that a[i:i+k] is equal to b[j:j+k], where\n            alo <= i <= i+k <= ahi\n            blo <= j <= j+k <= bhi\n        and for all (i\',j\',k\') meeting those conditions,\n            k >= k\'\n            i <= i\'\n            and if i == i\', j <= j\'\n\n        In other words, of all maximal matching blocks, return one that\n        starts earliest in a, and of all those maximal matching blocks that\n        start earliest in a, return the one that starts earliest in b.\n\n        >>> s = SequenceMatcher(None, " abcd", "abcd abcd")\n        >>> s.find_longest_match(0, 5, 0, 9)\n        Match(a=0, b=4, size=5)\n\n        If isjunk is defined, first the longest matching block is\n        determined as above, but with the additional restriction that no\n        junk element appears in the block.  Then that block is extended as\n        far as possible by matching (only) junk elements on both sides.  So\n        the resulting block never matches on junk except as identical junk\n        happens to be adjacent to an "interesting" match.\n\n        Here\'s the same example as before, but considering blanks to be\n        junk.  That prevents " abcd" from matching the " abcd" at the tail\n        end of the second sequence directly.  Instead only the "abcd" can\n        match, and matches the leftmost "abcd" in the second sequence:\n\n        >>> s = SequenceMatcher(lambda x: x==" ", " abcd", "abcd abcd")\n        >>> s.find_longest_match(0, 5, 0, 9)\n        Match(a=1, b=0, size=4)\n\n        If no blocks match, return (alo, blo, 0).\n\n        >>> s = SequenceMatcher(None, "ab", "c")\n        >>> s.find_longest_match(0, 2, 0, 1)\n        Match(a=0, b=0, size=0)\n        '
        (a, b, b2j, isbjunk) = (self.a, self.b, self.b2j, self.bjunk.__contains__)
        if ahi is None:
            ahi = len(a)
        if bhi is None:
            bhi = len(b)
        (besti, bestj, bestsize) = (alo, blo, 0)
        j2len = {}
        nothing = []
        for i in range(alo, ahi):
            j2lenget = j2len.get
            newj2len = {}
            for j in b2j.get(a[i], nothing):
                if j < blo:
                    continue
                if j >= bhi:
                    break
                k = newj2len[j] = j2lenget((j - 1), 0) + 1
                if k > bestsize:
                    (besti, bestj, bestsize) = (((i - k) + 1), ((j - k) + 1), k)
            j2len = newj2len
        while (
            (besti > alo)
            and (bestj > blo)
            and (not isbjunk(b[(bestj - 1)]))
            and (a[(besti - 1)] == b[(bestj - 1)])
        ):
            (besti, bestj, bestsize) = ((besti - 1), (bestj - 1), (bestsize + 1))
        while (
            ((besti + bestsize) < ahi)
            and ((bestj + bestsize) < bhi)
            and (not isbjunk(b[(bestj + bestsize)]))
            and (a[(besti + bestsize)] == b[(bestj + bestsize)])
        ):
            bestsize += 1
        while (
            (besti > alo)
            and (bestj > blo)
            and isbjunk(b[(bestj - 1)])
            and (a[(besti - 1)] == b[(bestj - 1)])
        ):
            (besti, bestj, bestsize) = ((besti - 1), (bestj - 1), (bestsize + 1))
        while (
            ((besti + bestsize) < ahi)
            and ((bestj + bestsize) < bhi)
            and isbjunk(b[(bestj + bestsize)])
            and (a[(besti + bestsize)] == b[(bestj + bestsize)])
        ):
            bestsize = bestsize + 1
        return Match(besti, bestj, bestsize)

    def get_matching_blocks(self):
        "Return list of triples describing matching subsequences.\n\n        Each triple is of the form (i, j, n), and means that\n        a[i:i+n] == b[j:j+n].  The triples are monotonically increasing in\n        i and in j.  New in Python 2.5, it's also guaranteed that if\n        (i, j, n) and (i', j', n') are adjacent triples in the list, and\n        the second is not the last triple in the list, then i+n != i' or\n        j+n != j'.  IOW, adjacent triples never describe adjacent equal\n        blocks.\n\n        The last triple is a dummy, (len(a), len(b), 0), and is the only\n        triple with n==0.\n\n        >>> s = SequenceMatcher(None, \"abxcd\", \"abcd\")\n        >>> list(s.get_matching_blocks())\n        [Match(a=0, b=0, size=2), Match(a=3, b=2, size=2), Match(a=5, b=4, size=0)]\n        "
        if self.matching_blocks is not None:
            return self.matching_blocks
        (la, lb) = (len(self.a), len(self.b))
        queue = [(0, la, 0, lb)]
        matching_blocks = []
        while queue:
            (alo, ahi, blo, bhi) = queue.pop()
            (i, j, k) = x = self.find_longest_match(alo, ahi, blo, bhi)
            if k:
                matching_blocks.append(x)
                if (alo < i) and (blo < j):
                    queue.append((alo, i, blo, j))
                if ((i + k) < ahi) and ((j + k) < bhi):
                    queue.append(((i + k), ahi, (j + k), bhi))
        matching_blocks.sort()
        i1 = j1 = k1 = 0
        non_adjacent = []
        for (i2, j2, k2) in matching_blocks:
            if ((i1 + k1) == i2) and ((j1 + k1) == j2):
                k1 += k2
            else:
                if k1:
                    non_adjacent.append((i1, j1, k1))
                (i1, j1, k1) = (i2, j2, k2)
        if k1:
            non_adjacent.append((i1, j1, k1))
        non_adjacent.append((la, lb, 0))
        self.matching_blocks = list(map(Match._make, non_adjacent))
        return self.matching_blocks

    def get_opcodes(self):
        "Return list of 5-tuples describing how to turn a into b.\n\n        Each tuple is of the form (tag, i1, i2, j1, j2).  The first tuple\n        has i1 == j1 == 0, and remaining tuples have i1 == the i2 from the\n        tuple preceding it, and likewise for j1 == the previous j2.\n\n        The tags are strings, with these meanings:\n\n        'replace':  a[i1:i2] should be replaced by b[j1:j2]\n        'delete':   a[i1:i2] should be deleted.\n                    Note that j1==j2 in this case.\n        'insert':   b[j1:j2] should be inserted at a[i1:i1].\n                    Note that i1==i2 in this case.\n        'equal':    a[i1:i2] == b[j1:j2]\n\n        >>> a = \"qabxcd\"\n        >>> b = \"abycdf\"\n        >>> s = SequenceMatcher(None, a, b)\n        >>> for tag, i1, i2, j1, j2 in s.get_opcodes():\n        ...    print((\"%7s a[%d:%d] (%s) b[%d:%d] (%s)\" %\n        ...           (tag, i1, i2, a[i1:i2], j1, j2, b[j1:j2])))\n         delete a[0:1] (q) b[0:0] ()\n          equal a[1:3] (ab) b[0:2] (ab)\n        replace a[3:4] (x) b[2:3] (y)\n          equal a[4:6] (cd) b[3:5] (cd)\n         insert a[6:6] () b[5:6] (f)\n        "
        if self.opcodes is not None:
            return self.opcodes
        i = j = 0
        self.opcodes = answer = []
        for (ai, bj, size) in self.get_matching_blocks():
            tag = ""
            if (i < ai) and (j < bj):
                tag = "replace"
            elif i < ai:
                tag = "delete"
            elif j < bj:
                tag = "insert"
            if tag:
                answer.append((tag, i, ai, j, bj))
            (i, j) = ((ai + size), (bj + size))
            if size:
                answer.append(("equal", ai, i, bj, j))
        return answer

    def get_grouped_opcodes(self, n=3):
        " Isolate change clusters by eliminating ranges with no changes.\n\n        Return a generator of groups with up to n lines of context.\n        Each group is in the same format as returned by get_opcodes().\n\n        >>> from pprint import pprint\n        >>> a = list(map(str, range(1,40)))\n        >>> b = a[:]\n        >>> b[8:8] = ['i']     # Make an insertion\n        >>> b[20] += 'x'       # Make a replacement\n        >>> b[23:28] = []      # Make a deletion\n        >>> b[30] += 'y'       # Make another replacement\n        >>> pprint(list(SequenceMatcher(None,a,b).get_grouped_opcodes()))\n        [[('equal', 5, 8, 5, 8), ('insert', 8, 8, 8, 9), ('equal', 8, 11, 9, 12)],\n         [('equal', 16, 19, 17, 20),\n          ('replace', 19, 20, 20, 21),\n          ('equal', 20, 22, 21, 23),\n          ('delete', 22, 27, 23, 23),\n          ('equal', 27, 30, 23, 26)],\n         [('equal', 31, 34, 27, 30),\n          ('replace', 34, 35, 30, 31),\n          ('equal', 35, 38, 31, 34)]]\n        "
        codes = self.get_opcodes()
        if not codes:
            codes = [("equal", 0, 1, 0, 1)]
        if codes[0][0] == "equal":
            (tag, i1, i2, j1, j2) = codes[0]
            codes[0] = (tag, max(i1, (i2 - n)), i2, max(j1, (j2 - n)), j2)
        if codes[(-1)][0] == "equal":
            (tag, i1, i2, j1, j2) = codes[(-1)]
            codes[(-1)] = (tag, i1, min(i2, (i1 + n)), j1, min(j2, (j1 + n)))
        nn = n + n
        group = []
        for (tag, i1, i2, j1, j2) in codes:
            if (tag == "equal") and ((i2 - i1) > nn):
                group.append((tag, i1, min(i2, (i1 + n)), j1, min(j2, (j1 + n))))
                (yield group)
                group = []
                (i1, j1) = (max(i1, (i2 - n)), max(j1, (j2 - n)))
            group.append((tag, i1, i2, j1, j2))
        if group and (not ((len(group) == 1) and (group[0][0] == "equal"))):
            (yield group)

    def ratio(self):
        'Return a measure of the sequences\' similarity (float in [0,1]).\n\n        Where T is the total number of elements in both sequences, and\n        M is the number of matches, this is 2.0*M / T.\n        Note that this is 1 if the sequences are identical, and 0 if\n        they have nothing in common.\n\n        .ratio() is expensive to compute if you haven\'t already computed\n        .get_matching_blocks() or .get_opcodes(), in which case you may\n        want to try .quick_ratio() or .real_quick_ratio() first to get an\n        upper bound.\n\n        >>> s = SequenceMatcher(None, "abcd", "bcde")\n        >>> s.ratio()\n        0.75\n        >>> s.quick_ratio()\n        0.75\n        >>> s.real_quick_ratio()\n        1.0\n        '
        matches = sum((triple[(-1)] for triple in self.get_matching_blocks()))
        return _calculate_ratio(matches, (len(self.a) + len(self.b)))

    def quick_ratio(self):
        "Return an upper bound on ratio() relatively quickly.\n\n        This isn't defined beyond that it is an upper bound on .ratio(), and\n        is faster to compute.\n        "
        if self.fullbcount is None:
            self.fullbcount = fullbcount = {}
            for elt in self.b:
                fullbcount[elt] = fullbcount.get(elt, 0) + 1
        fullbcount = self.fullbcount
        avail = {}
        (availhas, matches) = (avail.__contains__, 0)
        for elt in self.a:
            if availhas(elt):
                numb = avail[elt]
            else:
                numb = fullbcount.get(elt, 0)
            avail[elt] = numb - 1
            if numb > 0:
                matches = matches + 1
        return _calculate_ratio(matches, (len(self.a) + len(self.b)))

    def real_quick_ratio(self):
        "Return an upper bound on ratio() very quickly.\n\n        This isn't defined beyond that it is an upper bound on .ratio(), and\n        is faster to compute than either .ratio() or .quick_ratio().\n        "
        (la, lb) = (len(self.a), len(self.b))
        return _calculate_ratio(min(la, lb), (la + lb))

    __class_getitem__ = classmethod(GenericAlias)


def get_close_matches(word, possibilities, n=3, cutoff=0.6):
    'Use SequenceMatcher to return list of the best "good enough" matches.\n\n    word is a sequence for which close matches are desired (typically a\n    string).\n\n    possibilities is a list of sequences against which to match word\n    (typically a list of strings).\n\n    Optional arg n (default 3) is the maximum number of close matches to\n    return.  n must be > 0.\n\n    Optional arg cutoff (default 0.6) is a float in [0, 1].  Possibilities\n    that don\'t score at least that similar to word are ignored.\n\n    The best (no more than n) matches among the possibilities are returned\n    in a list, sorted by similarity score, most similar first.\n\n    >>> get_close_matches("appel", ["ape", "apple", "peach", "puppy"])\n    [\'apple\', \'ape\']\n    >>> import keyword as _keyword\n    >>> get_close_matches("wheel", _keyword.kwlist)\n    [\'while\']\n    >>> get_close_matches("Apple", _keyword.kwlist)\n    []\n    >>> get_close_matches("accept", _keyword.kwlist)\n    [\'except\']\n    '
    if not (n > 0):
        raise ValueError(("n must be > 0: %r" % (n,)))
    if not (0.0 <= cutoff <= 1.0):
        raise ValueError(("cutoff must be in [0.0, 1.0]: %r" % (cutoff,)))
    result = []
    s = SequenceMatcher()
    s.set_seq2(word)
    for x in possibilities:
        s.set_seq1(x)
        if (
            (s.real_quick_ratio() >= cutoff)
            and (s.quick_ratio() >= cutoff)
            and (s.ratio() >= cutoff)
        ):
            result.append((s.ratio(), x))
    result = _nlargest(n, result)
    return [x for (score, x) in result]


def _keep_original_ws(s, tag_s):
    "Replace whitespace with the original whitespace characters in `s`"
    return "".join(
        (
            (c if ((tag_c == " ") and c.isspace()) else tag_c)
            for (c, tag_c) in zip(s, tag_s)
        )
    )


class Differ:
    "\n    Differ is a class for comparing sequences of lines of text, and\n    producing human-readable differences or deltas.  Differ uses\n    SequenceMatcher both to compare sequences of lines, and to compare\n    sequences of characters within similar (near-matching) lines.\n\n    Each line of a Differ delta begins with a two-letter code:\n\n        '- '    line unique to sequence 1\n        '+ '    line unique to sequence 2\n        '  '    line common to both sequences\n        '? '    line not present in either input sequence\n\n    Lines beginning with '? ' attempt to guide the eye to intraline\n    differences, and were not present in either input sequence.  These lines\n    can be confusing if the sequences contain tab characters.\n\n    Note that Differ makes no claim to produce a *minimal* diff.  To the\n    contrary, minimal diffs are often counter-intuitive, because they synch\n    up anywhere possible, sometimes accidental matches 100 pages apart.\n    Restricting synch points to contiguous matches preserves some notion of\n    locality, at the occasional cost of producing a longer diff.\n\n    Example: Comparing two texts.\n\n    First we set up the texts, sequences of individual single-line strings\n    ending with newlines (such sequences can also be obtained from the\n    `readlines()` method of file-like objects):\n\n    >>> text1 = '''  1. Beautiful is better than ugly.\n    ...   2. Explicit is better than implicit.\n    ...   3. Simple is better than complex.\n    ...   4. Complex is better than complicated.\n    ... '''.splitlines(keepends=True)\n    >>> len(text1)\n    4\n    >>> text1[0][-1]\n    '\\n'\n    >>> text2 = '''  1. Beautiful is better than ugly.\n    ...   3.   Simple is better than complex.\n    ...   4. Complicated is better than complex.\n    ...   5. Flat is better than nested.\n    ... '''.splitlines(keepends=True)\n\n    Next we instantiate a Differ object:\n\n    >>> d = Differ()\n\n    Note that when instantiating a Differ object we may pass functions to\n    filter out line and character 'junk'.  See Differ.__init__ for details.\n\n    Finally, we compare the two:\n\n    >>> result = list(d.compare(text1, text2))\n\n    'result' is a list of strings, so let's pretty-print it:\n\n    >>> from pprint import pprint as _pprint\n    >>> _pprint(result)\n    ['    1. Beautiful is better than ugly.\\n',\n     '-   2. Explicit is better than implicit.\\n',\n     '-   3. Simple is better than complex.\\n',\n     '+   3.   Simple is better than complex.\\n',\n     '?     ++\\n',\n     '-   4. Complex is better than complicated.\\n',\n     '?            ^                     ---- ^\\n',\n     '+   4. Complicated is better than complex.\\n',\n     '?           ++++ ^                      ^\\n',\n     '+   5. Flat is better than nested.\\n']\n\n    As a single multi-line string it looks like this:\n\n    >>> print(''.join(result), end=\"\")\n        1. Beautiful is better than ugly.\n    -   2. Explicit is better than implicit.\n    -   3. Simple is better than complex.\n    +   3.   Simple is better than complex.\n    ?     ++\n    -   4. Complex is better than complicated.\n    ?            ^                     ---- ^\n    +   4. Complicated is better than complex.\n    ?           ++++ ^                      ^\n    +   5. Flat is better than nested.\n\n    Methods:\n\n    __init__(linejunk=None, charjunk=None)\n        Construct a text differencer, with optional filters.\n\n    compare(a, b)\n        Compare two sequences of lines; generate the resulting delta.\n    "

    def __init__(self, linejunk=None, charjunk=None):
        "\n        Construct a text differencer, with optional filters.\n\n        The two optional keyword parameters are for filter functions:\n\n        - `linejunk`: A function that should accept a single string argument,\n          and return true iff the string is junk. The module-level function\n          `IS_LINE_JUNK` may be used to filter out lines without visible\n          characters, except for at most one splat ('#').  It is recommended\n          to leave linejunk None; the underlying SequenceMatcher class has\n          an adaptive notion of \"noise\" lines that's better than any static\n          definition the author has ever been able to craft.\n\n        - `charjunk`: A function that should accept a string of length 1. The\n          module-level function `IS_CHARACTER_JUNK` may be used to filter out\n          whitespace characters (a blank or tab; **note**: bad idea to include\n          newline in this!).  Use of IS_CHARACTER_JUNK is recommended.\n        "
        self.linejunk = linejunk
        self.charjunk = charjunk

    def compare(self, a, b):
        "\n        Compare two sequences of lines; generate the resulting delta.\n\n        Each sequence must contain individual single-line strings ending with\n        newlines. Such sequences can be obtained from the `readlines()` method\n        of file-like objects.  The delta generated also consists of newline-\n        terminated strings, ready to be printed as-is via the writeline()\n        method of a file-like object.\n\n        Example:\n\n        >>> print(''.join(Differ().compare('one\\ntwo\\nthree\\n'.splitlines(True),\n        ...                                'ore\\ntree\\nemu\\n'.splitlines(True))),\n        ...       end=\"\")\n        - one\n        ?  ^\n        + ore\n        ?  ^\n        - two\n        - three\n        ?  -\n        + tree\n        + emu\n        "
        cruncher = SequenceMatcher(self.linejunk, a, b)
        for (tag, alo, ahi, blo, bhi) in cruncher.get_opcodes():
            if tag == "replace":
                g = self._fancy_replace(a, alo, ahi, b, blo, bhi)
            elif tag == "delete":
                g = self._dump("-", a, alo, ahi)
            elif tag == "insert":
                g = self._dump("+", b, blo, bhi)
            elif tag == "equal":
                g = self._dump(" ", a, alo, ahi)
            else:
                raise ValueError(("unknown tag %r" % (tag,)))
            (yield from g)

    def _dump(self, tag, x, lo, hi):
        "Generate comparison results for a same-tagged range."
        for i in range(lo, hi):
            (yield ("%s %s" % (tag, x[i])))

    def _plain_replace(self, a, alo, ahi, b, blo, bhi):
        assert (alo < ahi) and (blo < bhi)
        if (bhi - blo) < (ahi - alo):
            first = self._dump("+", b, blo, bhi)
            second = self._dump("-", a, alo, ahi)
        else:
            first = self._dump("-", a, alo, ahi)
            second = self._dump("+", b, blo, bhi)
        for g in (first, second):
            (yield from g)

    def _fancy_replace(self, a, alo, ahi, b, blo, bhi):
        "\n        When replacing one block of lines with another, search the blocks\n        for *similar* lines; the best-matching pair (if any) is used as a\n        synch point, and intraline difference marking is done on the\n        similar pair. Lots of work, but often worth it.\n\n        Example:\n\n        >>> d = Differ()\n        >>> results = d._fancy_replace(['abcDefghiJkl\\n'], 0, 1,\n        ...                            ['abcdefGhijkl\\n'], 0, 1)\n        >>> print(''.join(results), end=\"\")\n        - abcDefghiJkl\n        ?    ^  ^  ^\n        + abcdefGhijkl\n        ?    ^  ^  ^\n        "
        (best_ratio, cutoff) = (0.74, 0.75)
        cruncher = SequenceMatcher(self.charjunk)
        (eqi, eqj) = (None, None)
        for j in range(blo, bhi):
            bj = b[j]
            cruncher.set_seq2(bj)
            for i in range(alo, ahi):
                ai = a[i]
                if ai == bj:
                    if eqi is None:
                        (eqi, eqj) = (i, j)
                    continue
                cruncher.set_seq1(ai)
                if (
                    (cruncher.real_quick_ratio() > best_ratio)
                    and (cruncher.quick_ratio() > best_ratio)
                    and (cruncher.ratio() > best_ratio)
                ):
                    (best_ratio, best_i, best_j) = (cruncher.ratio(), i, j)
        if best_ratio < cutoff:
            if eqi is None:
                (yield from self._plain_replace(a, alo, ahi, b, blo, bhi))
                return
            (best_i, best_j, best_ratio) = (eqi, eqj, 1.0)
        else:
            eqi = None
        (yield from self._fancy_helper(a, alo, best_i, b, blo, best_j))
        (aelt, belt) = (a[best_i], b[best_j])
        if eqi is None:
            atags = btags = ""
            cruncher.set_seqs(aelt, belt)
            for (tag, ai1, ai2, bj1, bj2) in cruncher.get_opcodes():
                (la, lb) = ((ai2 - ai1), (bj2 - bj1))
                if tag == "replace":
                    atags += "^" * la
                    btags += "^" * lb
                elif tag == "delete":
                    atags += "-" * la
                elif tag == "insert":
                    btags += "+" * lb
                elif tag == "equal":
                    atags += " " * la
                    btags += " " * lb
                else:
                    raise ValueError(("unknown tag %r" % (tag,)))
            (yield from self._qformat(aelt, belt, atags, btags))
        else:
            (yield ("  " + aelt))
        (yield from self._fancy_helper(a, (best_i + 1), ahi, b, (best_j + 1), bhi))

    def _fancy_helper(self, a, alo, ahi, b, blo, bhi):
        g = []
        if alo < ahi:
            if blo < bhi:
                g = self._fancy_replace(a, alo, ahi, b, blo, bhi)
            else:
                g = self._dump("-", a, alo, ahi)
        elif blo < bhi:
            g = self._dump("+", b, blo, bhi)
        (yield from g)

    def _qformat(self, aline, bline, atags, btags):
        "\n        Format \"?\" output and deal with tabs.\n\n        Example:\n\n        >>> d = Differ()\n        >>> results = d._qformat('\\tabcDefghiJkl\\n', '\\tabcdefGhijkl\\n',\n        ...                      '  ^ ^  ^      ', '  ^ ^  ^      ')\n        >>> for line in results: print(repr(line))\n        ...\n        '- \\tabcDefghiJkl\\n'\n        '? \\t ^ ^  ^\\n'\n        '+ \\tabcdefGhijkl\\n'\n        '? \\t ^ ^  ^\\n'\n        "
        atags = _keep_original_ws(aline, atags).rstrip()
        btags = _keep_original_ws(bline, btags).rstrip()
        (yield ("- " + aline))
        if atags:
            (
                yield f"""? {atags}
"""
            )
        (yield ("+ " + bline))
        if btags:
            (
                yield f"""? {btags}
"""
            )


import re


def IS_LINE_JUNK(line, pat=re.compile("\\s*(?:#\\s*)?$").match):
    "\n    Return True for ignorable line: iff `line` is blank or contains a single '#'.\n\n    Examples:\n\n    >>> IS_LINE_JUNK('\\n')\n    True\n    >>> IS_LINE_JUNK('  #   \\n')\n    True\n    >>> IS_LINE_JUNK('hello\\n')\n    False\n    "
    return pat(line) is not None


def IS_CHARACTER_JUNK(ch, ws=" \t"):
    "\n    Return True for ignorable character: iff `ch` is a space or tab.\n\n    Examples:\n\n    >>> IS_CHARACTER_JUNK(' ')\n    True\n    >>> IS_CHARACTER_JUNK('\\t')\n    True\n    >>> IS_CHARACTER_JUNK('\\n')\n    False\n    >>> IS_CHARACTER_JUNK('x')\n    False\n    "
    return ch in ws


def _format_range_unified(start, stop):
    'Convert range to the "ed" format'
    beginning = start + 1
    length = stop - start
    if length == 1:
        return "{}".format(beginning)
    if not length:
        beginning -= 1
    return "{},{}".format(beginning, length)


def unified_diff(
    a, b, fromfile="", tofile="", fromfiledate="", tofiledate="", n=3, lineterm="\n"
):
    "\n    Compare two sequences of lines; generate the delta as a unified diff.\n\n    Unified diffs are a compact way of showing line changes and a few\n    lines of context.  The number of context lines is set by 'n' which\n    defaults to three.\n\n    By default, the diff control lines (those with ---, +++, or @@) are\n    created with a trailing newline.  This is helpful so that inputs\n    created from file.readlines() result in diffs that are suitable for\n    file.writelines() since both the inputs and outputs have trailing\n    newlines.\n\n    For inputs that do not have trailing newlines, set the lineterm\n    argument to \"\" so that the output will be uniformly newline free.\n\n    The unidiff format normally has a header for filenames and modification\n    times.  Any or all of these may be specified using strings for\n    'fromfile', 'tofile', 'fromfiledate', and 'tofiledate'.\n    The modification times are normally expressed in the ISO 8601 format.\n\n    Example:\n\n    >>> for line in unified_diff('one two three four'.split(),\n    ...             'zero one tree four'.split(), 'Original', 'Current',\n    ...             '2005-01-26 23:30:50', '2010-04-02 10:20:52',\n    ...             lineterm=''):\n    ...     print(line)                 # doctest: +NORMALIZE_WHITESPACE\n    --- Original        2005-01-26 23:30:50\n    +++ Current         2010-04-02 10:20:52\n    @@ -1,4 +1,4 @@\n    +zero\n     one\n    -two\n    -three\n    +tree\n     four\n    "
    _check_types(a, b, fromfile, tofile, fromfiledate, tofiledate, lineterm)
    started = False
    for group in SequenceMatcher(None, a, b).get_grouped_opcodes(n):
        if not started:
            started = True
            fromdate = "\t{}".format(fromfiledate) if fromfiledate else ""
            todate = "\t{}".format(tofiledate) if tofiledate else ""
            (yield "--- {}{}{}".format(fromfile, fromdate, lineterm))
            (yield "+++ {}{}{}".format(tofile, todate, lineterm))
        (first, last) = (group[0], group[(-1)])
        file1_range = _format_range_unified(first[1], last[2])
        file2_range = _format_range_unified(first[3], last[4])
        (yield "@@ -{} +{} @@{}".format(file1_range, file2_range, lineterm))
        for (tag, i1, i2, j1, j2) in group:
            if tag == "equal":
                for line in a[i1:i2]:
                    (yield (" " + line))
                continue
            if tag in {"replace", "delete"}:
                for line in a[i1:i2]:
                    (yield ("-" + line))
            if tag in {"replace", "insert"}:
                for line in b[j1:j2]:
                    (yield ("+" + line))


def _format_range_context(start, stop):
    'Convert range to the "ed" format'
    beginning = start + 1
    length = stop - start
    if not length:
        beginning -= 1
    if length <= 1:
        return "{}".format(beginning)
    return "{},{}".format(beginning, ((beginning + length) - 1))


def context_diff(
    a, b, fromfile="", tofile="", fromfiledate="", tofiledate="", n=3, lineterm="\n"
):
    "\n    Compare two sequences of lines; generate the delta as a context diff.\n\n    Context diffs are a compact way of showing line changes and a few\n    lines of context.  The number of context lines is set by 'n' which\n    defaults to three.\n\n    By default, the diff control lines (those with *** or ---) are\n    created with a trailing newline.  This is helpful so that inputs\n    created from file.readlines() result in diffs that are suitable for\n    file.writelines() since both the inputs and outputs have trailing\n    newlines.\n\n    For inputs that do not have trailing newlines, set the lineterm\n    argument to \"\" so that the output will be uniformly newline free.\n\n    The context diff format normally has a header for filenames and\n    modification times.  Any or all of these may be specified using\n    strings for 'fromfile', 'tofile', 'fromfiledate', and 'tofiledate'.\n    The modification times are normally expressed in the ISO 8601 format.\n    If not specified, the strings default to blanks.\n\n    Example:\n\n    >>> print(''.join(context_diff('one\\ntwo\\nthree\\nfour\\n'.splitlines(True),\n    ...       'zero\\none\\ntree\\nfour\\n'.splitlines(True), 'Original', 'Current')),\n    ...       end=\"\")\n    *** Original\n    --- Current\n    ***************\n    *** 1,4 ****\n      one\n    ! two\n    ! three\n      four\n    --- 1,4 ----\n    + zero\n      one\n    ! tree\n      four\n    "
    _check_types(a, b, fromfile, tofile, fromfiledate, tofiledate, lineterm)
    prefix = dict(insert="+ ", delete="- ", replace="! ", equal="  ")
    started = False
    for group in SequenceMatcher(None, a, b).get_grouped_opcodes(n):
        if not started:
            started = True
            fromdate = "\t{}".format(fromfiledate) if fromfiledate else ""
            todate = "\t{}".format(tofiledate) if tofiledate else ""
            (yield "*** {}{}{}".format(fromfile, fromdate, lineterm))
            (yield "--- {}{}{}".format(tofile, todate, lineterm))
        (first, last) = (group[0], group[(-1)])
        (yield ("***************" + lineterm))
        file1_range = _format_range_context(first[1], last[2])
        (yield "*** {} ****{}".format(file1_range, lineterm))
        if any(((tag in {"replace", "delete"}) for (tag, _, _, _, _) in group)):
            for (tag, i1, i2, _, _) in group:
                if tag != "insert":
                    for line in a[i1:i2]:
                        (yield (prefix[tag] + line))
        file2_range = _format_range_context(first[3], last[4])
        (yield "--- {} ----{}".format(file2_range, lineterm))
        if any(((tag in {"replace", "insert"}) for (tag, _, _, _, _) in group)):
            for (tag, _, _, j1, j2) in group:
                if tag != "delete":
                    for line in b[j1:j2]:
                        (yield (prefix[tag] + line))


def _check_types(a, b, *args):
    if a and (not isinstance(a[0], str)):
        raise TypeError(
            ("lines to compare must be str, not %s (%r)" % (type(a[0]).__name__, a[0]))
        )
    if b and (not isinstance(b[0], str)):
        raise TypeError(
            ("lines to compare must be str, not %s (%r)" % (type(b[0]).__name__, b[0]))
        )
    for arg in args:
        if not isinstance(arg, str):
            raise TypeError(("all arguments must be str, not: %r" % (arg,)))


def diff_bytes(
    dfunc,
    a,
    b,
    fromfile=b"",
    tofile=b"",
    fromfiledate=b"",
    tofiledate=b"",
    n=3,
    lineterm=b"\n",
):
    "\n    Compare `a` and `b`, two sequences of lines represented as bytes rather\n    than str. This is a wrapper for `dfunc`, which is typically either\n    unified_diff() or context_diff(). Inputs are losslessly converted to\n    strings so that `dfunc` only has to worry about strings, and encoded\n    back to bytes on return. This is necessary to compare files with\n    unknown or inconsistent encoding. All other inputs (except `n`) must be\n    bytes rather than str.\n    "

    def decode(s):
        try:
            return s.decode("ascii", "surrogateescape")
        except AttributeError as err:
            msg = "all arguments must be bytes, not %s (%r)" % (type(s).__name__, s)
            raise TypeError(msg) from err

    a = list(map(decode, a))
    b = list(map(decode, b))
    fromfile = decode(fromfile)
    tofile = decode(tofile)
    fromfiledate = decode(fromfiledate)
    tofiledate = decode(tofiledate)
    lineterm = decode(lineterm)
    lines = dfunc(a, b, fromfile, tofile, fromfiledate, tofiledate, n, lineterm)
    for line in lines:
        (yield line.encode("ascii", "surrogateescape"))


def ndiff(a, b, linejunk=None, charjunk=IS_CHARACTER_JUNK):
    "\n    Compare `a` and `b` (lists of strings); return a `Differ`-style delta.\n\n    Optional keyword parameters `linejunk` and `charjunk` are for filter\n    functions, or can be None:\n\n    - linejunk: A function that should accept a single string argument and\n      return true iff the string is junk.  The default is None, and is\n      recommended; the underlying SequenceMatcher class has an adaptive\n      notion of \"noise\" lines.\n\n    - charjunk: A function that accepts a character (string of length\n      1), and returns true iff the character is junk. The default is\n      the module-level function IS_CHARACTER_JUNK, which filters out\n      whitespace characters (a blank or tab; note: it's a bad idea to\n      include newline in this!).\n\n    Tools/scripts/ndiff.py is a command-line front-end to this function.\n\n    Example:\n\n    >>> diff = ndiff('one\\ntwo\\nthree\\n'.splitlines(keepends=True),\n    ...              'ore\\ntree\\nemu\\n'.splitlines(keepends=True))\n    >>> print(''.join(diff), end=\"\")\n    - one\n    ?  ^\n    + ore\n    ?  ^\n    - two\n    - three\n    ?  -\n    + tree\n    + emu\n    "
    return Differ(linejunk, charjunk).compare(a, b)


def _mdiff(fromlines, tolines, context=None, linejunk=None, charjunk=IS_CHARACTER_JUNK):
    "Returns generator yielding marked up from/to side by side differences.\n\n    Arguments:\n    fromlines -- list of text lines to compared to tolines\n    tolines -- list of text lines to be compared to fromlines\n    context -- number of context lines to display on each side of difference,\n               if None, all from/to text lines will be generated.\n    linejunk -- passed on to ndiff (see ndiff documentation)\n    charjunk -- passed on to ndiff (see ndiff documentation)\n\n    This function returns an iterator which returns a tuple:\n    (from line tuple, to line tuple, boolean flag)\n\n    from/to line tuple -- (line num, line text)\n        line num -- integer or None (to indicate a context separation)\n        line text -- original line text with following markers inserted:\n            '\\0+' -- marks start of added text\n            '\\0-' -- marks start of deleted text\n            '\\0^' -- marks start of changed text\n            '\\1' -- marks end of added/deleted/changed text\n\n    boolean flag -- None indicates context separation, True indicates\n        either \"from\" or \"to\" line contains a change, otherwise False.\n\n    This function/iterator was originally developed to generate side by side\n    file difference for making HTML pages (see HtmlDiff class for example\n    usage).\n\n    Note, this function utilizes the ndiff function to generate the side by\n    side difference markup.  Optional ndiff arguments may be passed to this\n    function and they in turn will be passed to ndiff.\n    "
    import re

    change_re = re.compile("(\\++|\\-+|\\^+)")
    diff_lines_iterator = ndiff(fromlines, tolines, linejunk, charjunk)

    def _make_line(lines, format_key, side, num_lines=[0, 0]):
        "Returns line of text with user's change markup and line formatting.\n\n        lines -- list of lines from the ndiff generator to produce a line of\n                 text from.  When producing the line of text to return, the\n                 lines used are removed from this list.\n        format_key -- '+' return first line in list with \"add\" markup around\n                          the entire line.\n                      '-' return first line in list with \"delete\" markup around\n                          the entire line.\n                      '?' return first line in list with add/delete/change\n                          intraline markup (indices obtained from second line)\n                      None return first line in list with no markup\n        side -- indice into the num_lines list (0=from,1=to)\n        num_lines -- from/to current line number.  This is NOT intended to be a\n                     passed parameter.  It is present as a keyword argument to\n                     maintain memory of the current line numbers between calls\n                     of this function.\n\n        Note, this function is purposefully not defined at the module scope so\n        that data it needs from its parent function (within whose context it\n        is defined) does not need to be of module scope.\n        "
        num_lines[side] += 1
        if format_key is None:
            return (num_lines[side], lines.pop(0)[2:])
        if format_key == "?":
            (text, markers) = (lines.pop(0), lines.pop(0))
            sub_info = []

            def record_sub_info(match_object, sub_info=sub_info):
                sub_info.append([match_object.group(1)[0], match_object.span()])
                return match_object.group(1)

            change_re.sub(record_sub_info, markers)
            for (key, (begin, end)) in reversed(sub_info):
                text = (
                    (((text[0:begin] + "\x00") + key) + text[begin:end]) + "\x01"
                ) + text[end:]
            text = text[2:]
        else:
            text = lines.pop(0)[2:]
            if not text:
                text = " "
            text = (("\x00" + format_key) + text) + "\x01"
        return (num_lines[side], text)

    def _line_iterator():
        'Yields from/to lines of text with a change indication.\n\n        This function is an iterator.  It itself pulls lines from a\n        differencing iterator, processes them and yields them.  When it can\n        it yields both a "from" and a "to" line, otherwise it will yield one\n        or the other.  In addition to yielding the lines of from/to text, a\n        boolean flag is yielded to indicate if the text line(s) have\n        differences in them.\n\n        Note, this function is purposefully not defined at the module scope so\n        that data it needs from its parent function (within whose context it\n        is defined) does not need to be of module scope.\n        '
        lines = []
        (num_blanks_pending, num_blanks_to_yield) = (0, 0)
        while True:
            while len(lines) < 4:
                lines.append(next(diff_lines_iterator, "X"))
            s = "".join([line[0] for line in lines])
            if s.startswith("X"):
                num_blanks_to_yield = num_blanks_pending
            elif s.startswith("-?+?"):
                (yield (_make_line(lines, "?", 0), _make_line(lines, "?", 1), True))
                continue
            elif s.startswith("--++"):
                num_blanks_pending -= 1
                (yield (_make_line(lines, "-", 0), None, True))
                continue
            elif s.startswith(("--?+", "--+", "- ")):
                (from_line, to_line) = (_make_line(lines, "-", 0), None)
                (num_blanks_to_yield, num_blanks_pending) = (
                    (num_blanks_pending - 1),
                    0,
                )
            elif s.startswith("-+?"):
                (yield (_make_line(lines, None, 0), _make_line(lines, "?", 1), True))
                continue
            elif s.startswith("-?+"):
                (yield (_make_line(lines, "?", 0), _make_line(lines, None, 1), True))
                continue
            elif s.startswith("-"):
                num_blanks_pending -= 1
                (yield (_make_line(lines, "-", 0), None, True))
                continue
            elif s.startswith("+--"):
                num_blanks_pending += 1
                (yield (None, _make_line(lines, "+", 1), True))
                continue
            elif s.startswith(("+ ", "+-")):
                (from_line, to_line) = (None, _make_line(lines, "+", 1))
                (num_blanks_to_yield, num_blanks_pending) = (
                    (num_blanks_pending + 1),
                    0,
                )
            elif s.startswith("+"):
                num_blanks_pending += 1
                (yield (None, _make_line(lines, "+", 1), True))
                continue
            elif s.startswith(" "):
                (
                    yield (
                        _make_line(lines[:], None, 0),
                        _make_line(lines, None, 1),
                        False,
                    )
                )
                continue
            while num_blanks_to_yield < 0:
                num_blanks_to_yield += 1
                (yield (None, ("", "\n"), True))
            while num_blanks_to_yield > 0:
                num_blanks_to_yield -= 1
                (yield (("", "\n"), None, True))
            if s.startswith("X"):
                return
            else:
                (yield (from_line, to_line, True))

    def _line_pair_iterator():
        "Yields from/to lines of text with a change indication.\n\n        This function is an iterator.  It itself pulls lines from the line\n        iterator.  Its difference from that iterator is that this function\n        always yields a pair of from/to text lines (with the change\n        indication).  If necessary it will collect single from/to lines\n        until it has a matching pair from/to pair to yield.\n\n        Note, this function is purposefully not defined at the module scope so\n        that data it needs from its parent function (within whose context it\n        is defined) does not need to be of module scope.\n        "
        line_iterator = _line_iterator()
        (fromlines, tolines) = ([], [])
        while True:
            while (len(fromlines) == 0) or (len(tolines) == 0):
                try:
                    (from_line, to_line, found_diff) = next(line_iterator)
                except StopIteration:
                    return
                if from_line is not None:
                    fromlines.append((from_line, found_diff))
                if to_line is not None:
                    tolines.append((to_line, found_diff))
            (from_line, fromDiff) = fromlines.pop(0)
            (to_line, to_diff) = tolines.pop(0)
            (yield (from_line, to_line, (fromDiff or to_diff)))

    line_pair_iterator = _line_pair_iterator()
    if context is None:
        (yield from line_pair_iterator)
    else:
        context += 1
        lines_to_write = 0
        while True:
            (index, contextLines) = (0, ([None] * context))
            found_diff = False
            while found_diff is False:
                try:
                    (from_line, to_line, found_diff) = next(line_pair_iterator)
                except StopIteration:
                    return
                i = index % context
                contextLines[i] = (from_line, to_line, found_diff)
                index += 1
            if index > context:
                (yield (None, None, None))
                lines_to_write = context
            else:
                lines_to_write = index
                index = 0
            while lines_to_write:
                i = index % context
                index += 1
                (yield contextLines[i])
                lines_to_write -= 1
            lines_to_write = context - 1
            try:
                while lines_to_write:
                    (from_line, to_line, found_diff) = next(line_pair_iterator)
                    if found_diff:
                        lines_to_write = context - 1
                    else:
                        lines_to_write -= 1
                    (yield (from_line, to_line, found_diff))
            except StopIteration:
                return


_file_template = '\n<!DOCTYPE html PUBLIC "-//W3C//DTD XHTML 1.0 Transitional//EN"\n          "http://www.w3.org/TR/xhtml1/DTD/xhtml1-transitional.dtd">\n\n<html>\n\n<head>\n    <meta http-equiv="Content-Type"\n          content="text/html; charset=%(charset)s" />\n    <title></title>\n    <style type="text/css">%(styles)s\n    </style>\n</head>\n\n<body>\n    %(table)s%(legend)s\n</body>\n\n</html>'
_styles = "\n        table.diff {font-family:Courier; border:medium;}\n        .diff_header {background-color:#e0e0e0}\n        td.diff_header {text-align:right}\n        .diff_next {background-color:#c0c0c0}\n        .diff_add {background-color:#aaffaa}\n        .diff_chg {background-color:#ffff77}\n        .diff_sub {background-color:#ffaaaa}"
_table_template = '\n    <table class="diff" id="difflib_chg_%(prefix)s_top"\n           cellspacing="0" cellpadding="0" rules="groups" >\n        <colgroup></colgroup> <colgroup></colgroup> <colgroup></colgroup>\n        <colgroup></colgroup> <colgroup></colgroup> <colgroup></colgroup>\n        %(header_row)s\n        <tbody>\n%(data_rows)s        </tbody>\n    </table>'
_legend = '\n    <table class="diff" summary="Legends">\n        <tr> <th colspan="2"> Legends </th> </tr>\n        <tr> <td> <table border="" summary="Colors">\n                      <tr><th> Colors </th> </tr>\n                      <tr><td class="diff_add">&nbsp;Added&nbsp;</td></tr>\n                      <tr><td class="diff_chg">Changed</td> </tr>\n                      <tr><td class="diff_sub">Deleted</td> </tr>\n                  </table></td>\n             <td> <table border="" summary="Links">\n                      <tr><th colspan="2"> Links </th> </tr>\n                      <tr><td>(f)irst change</td> </tr>\n                      <tr><td>(n)ext change</td> </tr>\n                      <tr><td>(t)op</td> </tr>\n                  </table></td> </tr>\n    </table>'


class HtmlDiff(object):
    "For producing HTML side by side comparison with change highlights.\n\n    This class can be used to create an HTML table (or a complete HTML file\n    containing the table) showing a side by side, line by line comparison\n    of text with inter-line and intra-line change highlights.  The table can\n    be generated in either full or contextual difference mode.\n\n    The following methods are provided for HTML generation:\n\n    make_table -- generates HTML for a single side by side table\n    make_file -- generates complete HTML file with a single side by side table\n\n    See tools/scripts/diff.py for an example usage of this class.\n    "
    _file_template = _file_template
    _styles = _styles
    _table_template = _table_template
    _legend = _legend
    _default_prefix = 0

    def __init__(
        self, tabsize=8, wrapcolumn=None, linejunk=None, charjunk=IS_CHARACTER_JUNK
    ):
        "HtmlDiff instance initializer\n\n        Arguments:\n        tabsize -- tab stop spacing, defaults to 8.\n        wrapcolumn -- column number where lines are broken and wrapped,\n            defaults to None where lines are not wrapped.\n        linejunk,charjunk -- keyword arguments passed into ndiff() (used by\n            HtmlDiff() to generate the side by side HTML differences).  See\n            ndiff() documentation for argument default values and descriptions.\n        "
        self._tabsize = tabsize
        self._wrapcolumn = wrapcolumn
        self._linejunk = linejunk
        self._charjunk = charjunk

    def make_file(
        self,
        fromlines,
        tolines,
        fromdesc="",
        todesc="",
        context=False,
        numlines=5,
        *,
        charset="utf-8",
    ):
        'Returns HTML file of side by side comparison with change highlights\n\n        Arguments:\n        fromlines -- list of "from" lines\n        tolines -- list of "to" lines\n        fromdesc -- "from" file column header string\n        todesc -- "to" file column header string\n        context -- set to True for contextual differences (defaults to False\n            which shows full differences).\n        numlines -- number of context lines.  When context is set True,\n            controls number of lines displayed before and after the change.\n            When context is False, controls the number of lines to place\n            the "next" link anchors before the next change (so click of\n            "next" link jumps to just before the change).\n        charset -- charset of the HTML document\n        '
        return (
            (
                self._file_template
                % dict(
                    styles=self._styles,
                    legend=self._legend,
                    table=self.make_table(
                        fromlines,
                        tolines,
                        fromdesc,
                        todesc,
                        context=context,
                        numlines=numlines,
                    ),
                    charset=charset,
                )
            )
            .encode(charset, "xmlcharrefreplace")
            .decode(charset)
        )

    def _tab_newline_replace(self, fromlines, tolines):
        "Returns from/to line lists with tabs expanded and newlines removed.\n\n        Instead of tab characters being replaced by the number of spaces\n        needed to fill in to the next tab stop, this function will fill\n        the space with tab characters.  This is done so that the difference\n        algorithms can identify changes in a file when tabs are replaced by\n        spaces and vice versa.  At the end of the HTML generation, the tab\n        characters will be replaced with a nonbreakable space.\n        "

        def expand_tabs(line):
            line = line.replace(" ", "\x00")
            line = line.expandtabs(self._tabsize)
            line = line.replace(" ", "\t")
            return line.replace("\x00", " ").rstrip("\n")

        fromlines = [expand_tabs(line) for line in fromlines]
        tolines = [expand_tabs(line) for line in tolines]
        return (fromlines, tolines)

    def _split_line(self, data_list, line_num, text):
        "Builds list of text lines by splitting text lines at wrap point\n\n        This function will determine if the input text line needs to be\n        wrapped (split) into separate lines.  If so, the first wrap point\n        will be determined and the first line appended to the output\n        text line list.  This function is used recursively to handle\n        the second part of the split line to further split it.\n        "
        if not line_num:
            data_list.append((line_num, text))
            return
        size = len(text)
        max = self._wrapcolumn
        if (size <= max) or ((size - (text.count("\x00") * 3)) <= max):
            data_list.append((line_num, text))
            return
        i = 0
        n = 0
        mark = ""
        while (n < max) and (i < size):
            if text[i] == "\x00":
                i += 1
                mark = text[i]
                i += 1
            elif text[i] == "\x01":
                i += 1
                mark = ""
            else:
                i += 1
                n += 1
        line1 = text[:i]
        line2 = text[i:]
        if mark:
            line1 = line1 + "\x01"
            line2 = ("\x00" + mark) + line2
        data_list.append((line_num, line1))
        self._split_line(data_list, ">", line2)

    def _line_wrapper(self, diffs):
        "Returns iterator that splits (wraps) mdiff text lines"
        for (fromdata, todata, flag) in diffs:
            if flag is None:
                (yield (fromdata, todata, flag))
                continue
            ((fromline, fromtext), (toline, totext)) = (fromdata, todata)
            (fromlist, tolist) = ([], [])
            self._split_line(fromlist, fromline, fromtext)
            self._split_line(tolist, toline, totext)
            while fromlist or tolist:
                if fromlist:
                    fromdata = fromlist.pop(0)
                else:
                    fromdata = ("", " ")
                if tolist:
                    todata = tolist.pop(0)
                else:
                    todata = ("", " ")
                (yield (fromdata, todata, flag))

    def _collect_lines(self, diffs):
        "Collects mdiff output into separate lists\n\n        Before storing the mdiff from/to data into a list, it is converted\n        into a single line of text with HTML markup.\n        "
        (fromlist, tolist, flaglist) = ([], [], [])
        for (fromdata, todata, flag) in diffs:
            try:
                fromlist.append(self._format_line(0, flag, *fromdata))
                tolist.append(self._format_line(1, flag, *todata))
            except TypeError:
                fromlist.append(None)
                tolist.append(None)
            flaglist.append(flag)
        return (fromlist, tolist, flaglist)

    def _format_line(self, side, flag, linenum, text):
        'Returns HTML markup of "from" / "to" text lines\n\n        side -- 0 or 1 indicating "from" or "to" text\n        flag -- indicates if difference on line\n        linenum -- line number (used for line number column)\n        text -- line text to be marked up\n        '
        try:
            linenum = "%d" % linenum
            id = ' id="%s%s"' % (self._prefix[side], linenum)
        except TypeError:
            id = ""
        text = text.replace("&", "&amp;").replace(">", "&gt;").replace("<", "&lt;")
        text = text.replace(" ", "&nbsp;").rstrip()
        return '<td class="diff_header"%s>%s</td><td nowrap="nowrap">%s</td>' % (
            id,
            linenum,
            text,
        )

    def _make_prefix(self):
        "Create unique anchor prefixes"
        fromprefix = "from%d_" % HtmlDiff._default_prefix
        toprefix = "to%d_" % HtmlDiff._default_prefix
        HtmlDiff._default_prefix += 1
        self._prefix = [fromprefix, toprefix]

    def _convert_flags(self, fromlist, tolist, flaglist, context, numlines):
        'Makes list of "next" links'
        toprefix = self._prefix[1]
        next_id = [""] * len(flaglist)
        next_href = [""] * len(flaglist)
        (num_chg, in_change) = (0, False)
        last = 0
        for (i, flag) in enumerate(flaglist):
            if flag:
                if not in_change:
                    in_change = True
                    last = i
                    i = max([0, (i - numlines)])
                    next_id[i] = ' id="difflib_chg_%s_%d"' % (toprefix, num_chg)
                    num_chg += 1
                    next_href[last] = '<a href="#difflib_chg_%s_%d">n</a>' % (
                        toprefix,
                        num_chg,
                    )
            else:
                in_change = False
        if not flaglist:
            flaglist = [False]
            next_id = [""]
            next_href = [""]
            last = 0
            if context:
                fromlist = ["<td></td><td>&nbsp;No Differences Found&nbsp;</td>"]
                tolist = fromlist
            else:
                fromlist = tolist = ["<td></td><td>&nbsp;Empty File&nbsp;</td>"]
        if not flaglist[0]:
            next_href[0] = '<a href="#difflib_chg_%s_0">f</a>' % toprefix
        next_href[last] = '<a href="#difflib_chg_%s_top">t</a>' % toprefix
        return (fromlist, tolist, flaglist, next_href, next_id)

    def make_table(
        self, fromlines, tolines, fromdesc="", todesc="", context=False, numlines=5
    ):
        'Returns HTML table of side by side comparison with change highlights\n\n        Arguments:\n        fromlines -- list of "from" lines\n        tolines -- list of "to" lines\n        fromdesc -- "from" file column header string\n        todesc -- "to" file column header string\n        context -- set to True for contextual differences (defaults to False\n            which shows full differences).\n        numlines -- number of context lines.  When context is set True,\n            controls number of lines displayed before and after the change.\n            When context is False, controls the number of lines to place\n            the "next" link anchors before the next change (so click of\n            "next" link jumps to just before the change).\n        '
        self._make_prefix()
        (fromlines, tolines) = self._tab_newline_replace(fromlines, tolines)
        if context:
            context_lines = numlines
        else:
            context_lines = None
        diffs = _mdiff(
            fromlines,
            tolines,
            context_lines,
            linejunk=self._linejunk,
            charjunk=self._charjunk,
        )
        if self._wrapcolumn:
            diffs = self._line_wrapper(diffs)
        (fromlist, tolist, flaglist) = self._collect_lines(diffs)
        (fromlist, tolist, flaglist, next_href, next_id) = self._convert_flags(
            fromlist, tolist, flaglist, context, numlines
        )
        s = []
        fmt = (
            '            <tr><td class="diff_next"%s>%s</td>%s'
            + '<td class="diff_next">%s</td>%s</tr>\n'
        )
        for i in range(len(flaglist)):
            if flaglist[i] is None:
                if i > 0:
                    s.append("        </tbody>        \n        <tbody>\n")
            else:
                s.append(
                    (
                        fmt
                        % (
                            next_id[i],
                            next_href[i],
                            fromlist[i],
                            next_href[i],
                            tolist[i],
                        )
                    )
                )
        if fromdesc or todesc:
            header_row = "<thead><tr>%s%s%s%s</tr></thead>" % (
                '<th class="diff_next"><br /></th>',
                ('<th colspan="2" class="diff_header">%s</th>' % fromdesc),
                '<th class="diff_next"><br /></th>',
                ('<th colspan="2" class="diff_header">%s</th>' % todesc),
            )
        else:
            header_row = ""
        table = self._table_template % dict(
            data_rows="".join(s), header_row=header_row, prefix=self._prefix[1]
        )
        return (
            table.replace("\x00+", '<span class="diff_add">')
            .replace("\x00-", '<span class="diff_sub">')
            .replace("\x00^", '<span class="diff_chg">')
            .replace("\x01", "</span>")
            .replace("\t", "&nbsp;")
        )


del re


def restore(delta, which):
    "\n    Generate one of the two sequences that generated a delta.\n\n    Given a `delta` produced by `Differ.compare()` or `ndiff()`, extract\n    lines originating from file 1 or 2 (parameter `which`), stripping off line\n    prefixes.\n\n    Examples:\n\n    >>> diff = ndiff('one\\ntwo\\nthree\\n'.splitlines(keepends=True),\n    ...              'ore\\ntree\\nemu\\n'.splitlines(keepends=True))\n    >>> diff = list(diff)\n    >>> print(''.join(restore(diff, 1)), end=\"\")\n    one\n    two\n    three\n    >>> print(''.join(restore(diff, 2)), end=\"\")\n    ore\n    tree\n    emu\n    "
    try:
        tag = {1: "- ", 2: "+ "}[int(which)]
    except KeyError:
        raise ValueError(
            ("unknown delta choice (must be 1 or 2): %r" % which)
        ) from None
    prefixes = ("  ", tag)
    for line in delta:
        if line[:2] in prefixes:
            (yield line[2:])


def _test():
    import doctest, difflib

    return doctest.testmod(difflib)


if __name__ == "__main__":
    _test()
