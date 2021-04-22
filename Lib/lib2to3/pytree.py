"\nPython parse tree definitions.\n\nThis is a very concrete parse tree; we need to keep every token and\neven the comments and whitespace between tokens.\n\nThere's also a pattern matching implementation here.\n"
__author__ = "Guido van Rossum <guido@python.org>"
import sys
from io import StringIO

HUGE = 2147483647
_type_reprs = {}


def type_repr(type_num):
    global _type_reprs
    if not _type_reprs:
        from .pygram import python_symbols

        for (name, val) in python_symbols.__dict__.items():
            if type(val) == int:
                _type_reprs[val] = name
    return _type_reprs.setdefault(type_num, type_num)


class Base(object):
    "\n    Abstract base class for Node and Leaf.\n\n    This provides some default functionality and boilerplate using the\n    template pattern.\n\n    A node may be a subnode of at most one parent.\n    "
    type = None
    parent = None
    children = ()
    was_changed = False
    was_checked = False

    def __new__(cls, *args, **kwds):
        "Constructor that prevents Base from being instantiated."
        assert cls is not Base, "Cannot instantiate Base"
        return object.__new__(cls)

    def __eq__(self, other):
        "\n        Compare two nodes for equality.\n\n        This calls the method _eq().\n        "
        if self.__class__ is not other.__class__:
            return NotImplemented
        return self._eq(other)

    __hash__ = None

    def _eq(self, other):
        "\n        Compare two nodes for equality.\n\n        This is called by __eq__ and __ne__.  It is only called if the two nodes\n        have the same type.  This must be implemented by the concrete subclass.\n        Nodes should be considered equal if they have the same structure,\n        ignoring the prefix string and other context information.\n        "
        raise NotImplementedError

    def clone(self):
        "\n        Return a cloned (deep) copy of self.\n\n        This must be implemented by the concrete subclass.\n        "
        raise NotImplementedError

    def post_order(self):
        "\n        Return a post-order iterator for the tree.\n\n        This must be implemented by the concrete subclass.\n        "
        raise NotImplementedError

    def pre_order(self):
        "\n        Return a pre-order iterator for the tree.\n\n        This must be implemented by the concrete subclass.\n        "
        raise NotImplementedError

    def replace(self, new):
        "Replace this node with a new one in the parent."
        assert self.parent is not None, str(self)
        assert new is not None
        if not isinstance(new, list):
            new = [new]
        l_children = []
        found = False
        for ch in self.parent.children:
            if ch is self:
                assert not found, (self.parent.children, self, new)
                if new is not None:
                    l_children.extend(new)
                found = True
            else:
                l_children.append(ch)
        assert found, (self.children, self, new)
        self.parent.changed()
        self.parent.children = l_children
        for x in new:
            x.parent = self.parent
        self.parent = None

    def get_lineno(self):
        "Return the line number which generated the invocant node."
        node = self
        while not isinstance(node, Leaf):
            if not node.children:
                return
            node = node.children[0]
        return node.lineno

    def changed(self):
        if self.parent:
            self.parent.changed()
        self.was_changed = True

    def remove(self):
        "\n        Remove the node from the tree. Returns the position of the node in its\n        parent's children before it was removed.\n        "
        if self.parent:
            for (i, node) in enumerate(self.parent.children):
                if node is self:
                    self.parent.changed()
                    del self.parent.children[i]
                    self.parent = None
                    return i

    @property
    def next_sibling(self):
        "\n        The node immediately following the invocant in their parent's children\n        list. If the invocant does not have a next sibling, it is None\n        "
        if self.parent is None:
            return None
        for (i, child) in enumerate(self.parent.children):
            if child is self:
                try:
                    return self.parent.children[(i + 1)]
                except IndexError:
                    return None

    @property
    def prev_sibling(self):
        "\n        The node immediately preceding the invocant in their parent's children\n        list. If the invocant does not have a previous sibling, it is None.\n        "
        if self.parent is None:
            return None
        for (i, child) in enumerate(self.parent.children):
            if child is self:
                if i == 0:
                    return None
                return self.parent.children[(i - 1)]

    def leaves(self):
        for child in self.children:
            (yield from child.leaves())

    def depth(self):
        if self.parent is None:
            return 0
        return 1 + self.parent.depth()

    def get_suffix(self):
        "\n        Return the string immediately following the invocant node. This is\n        effectively equivalent to node.next_sibling.prefix\n        "
        next_sib = self.next_sibling
        if next_sib is None:
            return ""
        return next_sib.prefix

    if sys.version_info < (3, 0):

        def __str__(self):
            return str(self).encode("ascii")


class Node(Base):
    "Concrete implementation for interior nodes."

    def __init__(self, type, children, context=None, prefix=None, fixers_applied=None):
        "\n        Initializer.\n\n        Takes a type constant (a symbol number >= 256), a sequence of\n        child nodes, and an optional context keyword argument.\n\n        As a side effect, the parent pointers of the children are updated.\n        "
        assert type >= 256, type
        self.type = type
        self.children = list(children)
        for ch in self.children:
            assert ch.parent is None, repr(ch)
            ch.parent = self
        if prefix is not None:
            self.prefix = prefix
        if fixers_applied:
            self.fixers_applied = fixers_applied[:]
        else:
            self.fixers_applied = None

    def __repr__(self):
        "Return a canonical string representation."
        return "%s(%s, %r)" % (
            self.__class__.__name__,
            type_repr(self.type),
            self.children,
        )

    def __unicode__(self):
        "\n        Return a pretty string representation.\n\n        This reproduces the input source exactly.\n        "
        return "".join(map(str, self.children))

    if sys.version_info > (3, 0):
        __str__ = __unicode__

    def _eq(self, other):
        "Compare two nodes for equality."
        return (self.type, self.children) == (other.type, other.children)

    def clone(self):
        "Return a cloned (deep) copy of self."
        return Node(
            self.type,
            [ch.clone() for ch in self.children],
            fixers_applied=self.fixers_applied,
        )

    def post_order(self):
        "Return a post-order iterator for the tree."
        for child in self.children:
            (yield from child.post_order())
        (yield self)

    def pre_order(self):
        "Return a pre-order iterator for the tree."
        (yield self)
        for child in self.children:
            (yield from child.pre_order())

    @property
    def prefix(self):
        "\n        The whitespace and comments preceding this node in the input.\n        "
        if not self.children:
            return ""
        return self.children[0].prefix

    @prefix.setter
    def prefix(self, prefix):
        if self.children:
            self.children[0].prefix = prefix

    def set_child(self, i, child):
        "\n        Equivalent to 'node.children[i] = child'. This method also sets the\n        child's parent attribute appropriately.\n        "
        child.parent = self
        self.children[i].parent = None
        self.children[i] = child
        self.changed()

    def insert_child(self, i, child):
        "\n        Equivalent to 'node.children.insert(i, child)'. This method also sets\n        the child's parent attribute appropriately.\n        "
        child.parent = self
        self.children.insert(i, child)
        self.changed()

    def append_child(self, child):
        "\n        Equivalent to 'node.children.append(child)'. This method also sets the\n        child's parent attribute appropriately.\n        "
        child.parent = self
        self.children.append(child)
        self.changed()


class Leaf(Base):
    "Concrete implementation for leaf nodes."
    _prefix = ""
    lineno = 0
    column = 0

    def __init__(self, type, value, context=None, prefix=None, fixers_applied=[]):
        "\n        Initializer.\n\n        Takes a type constant (a token number < 256), a string value, and an\n        optional context keyword argument.\n        "
        assert 0 <= type < 256, type
        if context is not None:
            (self._prefix, (self.lineno, self.column)) = context
        self.type = type
        self.value = value
        if prefix is not None:
            self._prefix = prefix
        self.fixers_applied = fixers_applied[:]

    def __repr__(self):
        "Return a canonical string representation."
        return "%s(%r, %r)" % (self.__class__.__name__, self.type, self.value)

    def __unicode__(self):
        "\n        Return a pretty string representation.\n\n        This reproduces the input source exactly.\n        "
        return self.prefix + str(self.value)

    if sys.version_info > (3, 0):
        __str__ = __unicode__

    def _eq(self, other):
        "Compare two nodes for equality."
        return (self.type, self.value) == (other.type, other.value)

    def clone(self):
        "Return a cloned (deep) copy of self."
        return Leaf(
            self.type,
            self.value,
            (self.prefix, (self.lineno, self.column)),
            fixers_applied=self.fixers_applied,
        )

    def leaves(self):
        (yield self)

    def post_order(self):
        "Return a post-order iterator for the tree."
        (yield self)

    def pre_order(self):
        "Return a pre-order iterator for the tree."
        (yield self)

    @property
    def prefix(self):
        "\n        The whitespace and comments preceding this token in the input.\n        "
        return self._prefix

    @prefix.setter
    def prefix(self, prefix):
        self.changed()
        self._prefix = prefix


def convert(gr, raw_node):
    "\n    Convert raw node information to a Node or Leaf instance.\n\n    This is passed to the parser driver which calls it whenever a reduction of a\n    grammar rule produces a new complete node, so that the tree is build\n    strictly bottom-up.\n    "
    (type, value, context, children) = raw_node
    if children or (type in gr.number2symbol):
        if len(children) == 1:
            return children[0]
        return Node(type, children, context=context)
    else:
        return Leaf(type, value, context=context)


class BasePattern(object):
    "\n    A pattern is a tree matching pattern.\n\n    It looks for a specific node type (token or symbol), and\n    optionally for a specific content.\n\n    This is an abstract base class.  There are three concrete\n    subclasses:\n\n    - LeafPattern matches a single leaf node;\n    - NodePattern matches a single node (usually non-leaf);\n    - WildcardPattern matches a sequence of nodes of variable length.\n    "
    type = None
    content = None
    name = None

    def __new__(cls, *args, **kwds):
        "Constructor that prevents BasePattern from being instantiated."
        assert cls is not BasePattern, "Cannot instantiate BasePattern"
        return object.__new__(cls)

    def __repr__(self):
        args = [type_repr(self.type), self.content, self.name]
        while args and (args[(-1)] is None):
            del args[(-1)]
        return "%s(%s)" % (self.__class__.__name__, ", ".join(map(repr, args)))

    def optimize(self):
        "\n        A subclass can define this as a hook for optimizations.\n\n        Returns either self or another node with the same effect.\n        "
        return self

    def match(self, node, results=None):
        "\n        Does this pattern exactly match a node?\n\n        Returns True if it matches, False if not.\n\n        If results is not None, it must be a dict which will be\n        updated with the nodes matching named subpatterns.\n\n        Default implementation for non-wildcard patterns.\n        "
        if (self.type is not None) and (node.type != self.type):
            return False
        if self.content is not None:
            r = None
            if results is not None:
                r = {}
            if not self._submatch(node, r):
                return False
            if r:
                results.update(r)
        if (results is not None) and self.name:
            results[self.name] = node
        return True

    def match_seq(self, nodes, results=None):
        "\n        Does this pattern exactly match a sequence of nodes?\n\n        Default implementation for non-wildcard patterns.\n        "
        if len(nodes) != 1:
            return False
        return self.match(nodes[0], results)

    def generate_matches(self, nodes):
        "\n        Generator yielding all matches for this pattern.\n\n        Default implementation for non-wildcard patterns.\n        "
        r = {}
        if nodes and self.match(nodes[0], r):
            (yield (1, r))


class LeafPattern(BasePattern):
    def __init__(self, type=None, content=None, name=None):
        "\n        Initializer.  Takes optional type, content, and name.\n\n        The type, if given must be a token type (< 256).  If not given,\n        this matches any *leaf* node; the content may still be required.\n\n        The content, if given, must be a string.\n\n        If a name is given, the matching node is stored in the results\n        dict under that key.\n        "
        if type is not None:
            assert 0 <= type < 256, type
        if content is not None:
            assert isinstance(content, str), repr(content)
        self.type = type
        self.content = content
        self.name = name

    def match(self, node, results=None):
        "Override match() to insist on a leaf node."
        if not isinstance(node, Leaf):
            return False
        return BasePattern.match(self, node, results)

    def _submatch(self, node, results=None):
        "\n        Match the pattern's content to the node's children.\n\n        This assumes the node type matches and self.content is not None.\n\n        Returns True if it matches, False if not.\n\n        If results is not None, it must be a dict which will be\n        updated with the nodes matching named subpatterns.\n\n        When returning False, the results dict may still be updated.\n        "
        return self.content == node.value


class NodePattern(BasePattern):
    wildcards = False

    def __init__(self, type=None, content=None, name=None):
        "\n        Initializer.  Takes optional type, content, and name.\n\n        The type, if given, must be a symbol type (>= 256).  If the\n        type is None this matches *any* single node (leaf or not),\n        except if content is not None, in which it only matches\n        non-leaf nodes that also match the content pattern.\n\n        The content, if not None, must be a sequence of Patterns that\n        must match the node's children exactly.  If the content is\n        given, the type must not be None.\n\n        If a name is given, the matching node is stored in the results\n        dict under that key.\n        "
        if type is not None:
            assert type >= 256, type
        if content is not None:
            assert not isinstance(content, str), repr(content)
            content = list(content)
            for (i, item) in enumerate(content):
                assert isinstance(item, BasePattern), (i, item)
                if isinstance(item, WildcardPattern):
                    self.wildcards = True
        self.type = type
        self.content = content
        self.name = name

    def _submatch(self, node, results=None):
        "\n        Match the pattern's content to the node's children.\n\n        This assumes the node type matches and self.content is not None.\n\n        Returns True if it matches, False if not.\n\n        If results is not None, it must be a dict which will be\n        updated with the nodes matching named subpatterns.\n\n        When returning False, the results dict may still be updated.\n        "
        if self.wildcards:
            for (c, r) in generate_matches(self.content, node.children):
                if c == len(node.children):
                    if results is not None:
                        results.update(r)
                    return True
            return False
        if len(self.content) != len(node.children):
            return False
        for (subpattern, child) in zip(self.content, node.children):
            if not subpattern.match(child, results):
                return False
        return True


class WildcardPattern(BasePattern):
    "\n    A wildcard pattern can match zero or more nodes.\n\n    This has all the flexibility needed to implement patterns like:\n\n    .*      .+      .?      .{m,n}\n    (a b c | d e | f)\n    (...)*  (...)+  (...)?  (...){m,n}\n\n    except it always uses non-greedy matching.\n    "

    def __init__(self, content=None, min=0, max=HUGE, name=None):
        "\n        Initializer.\n\n        Args:\n            content: optional sequence of subsequences of patterns;\n                     if absent, matches one node;\n                     if present, each subsequence is an alternative [*]\n            min: optional minimum number of times to match, default 0\n            max: optional maximum number of times to match, default HUGE\n            name: optional name assigned to this match\n\n        [*] Thus, if content is [[a, b, c], [d, e], [f, g, h]] this is\n            equivalent to (a b c | d e | f g h); if content is None,\n            this is equivalent to '.' in regular expression terms.\n            The min and max parameters work as follows:\n                min=0, max=maxint: .*\n                min=1, max=maxint: .+\n                min=0, max=1: .?\n                min=1, max=1: .\n            If content is not None, replace the dot with the parenthesized\n            list of alternatives, e.g. (a b c | d e | f g h)*\n        "
        assert 0 <= min <= max <= HUGE, (min, max)
        if content is not None:
            content = tuple(map(tuple, content))
            assert len(content), repr(content)
            for alt in content:
                assert len(alt), repr(alt)
        self.content = content
        self.min = min
        self.max = max
        self.name = name

    def optimize(self):
        "Optimize certain stacked wildcard patterns."
        subpattern = None
        if (
            (self.content is not None)
            and (len(self.content) == 1)
            and (len(self.content[0]) == 1)
        ):
            subpattern = self.content[0][0]
        if (self.min == 1) and (self.max == 1):
            if self.content is None:
                return NodePattern(name=self.name)
            if (subpattern is not None) and (self.name == subpattern.name):
                return subpattern.optimize()
        if (
            (self.min <= 1)
            and isinstance(subpattern, WildcardPattern)
            and (subpattern.min <= 1)
            and (self.name == subpattern.name)
        ):
            return WildcardPattern(
                subpattern.content,
                (self.min * subpattern.min),
                (self.max * subpattern.max),
                subpattern.name,
            )
        return self

    def match(self, node, results=None):
        "Does this pattern exactly match a node?"
        return self.match_seq([node], results)

    def match_seq(self, nodes, results=None):
        "Does this pattern exactly match a sequence of nodes?"
        for (c, r) in self.generate_matches(nodes):
            if c == len(nodes):
                if results is not None:
                    results.update(r)
                    if self.name:
                        results[self.name] = list(nodes)
                return True
        return False

    def generate_matches(self, nodes):
        "\n        Generator yielding matches for a sequence of nodes.\n\n        Args:\n            nodes: sequence of nodes\n\n        Yields:\n            (count, results) tuples where:\n            count: the match comprises nodes[:count];\n            results: dict containing named submatches.\n        "
        if self.content is None:
            for count in range(self.min, (1 + min(len(nodes), self.max))):
                r = {}
                if self.name:
                    r[self.name] = nodes[:count]
                (yield (count, r))
        elif self.name == "bare_name":
            (yield self._bare_name_matches(nodes))
        else:
            if hasattr(sys, "getrefcount"):
                save_stderr = sys.stderr
                sys.stderr = StringIO()
            try:
                for (count, r) in self._recursive_matches(nodes, 0):
                    if self.name:
                        r[self.name] = nodes[:count]
                    (yield (count, r))
            except RuntimeError:
                for (count, r) in self._iterative_matches(nodes):
                    if self.name:
                        r[self.name] = nodes[:count]
                    (yield (count, r))
            finally:
                if hasattr(sys, "getrefcount"):
                    sys.stderr = save_stderr

    def _iterative_matches(self, nodes):
        "Helper to iteratively yield the matches."
        nodelen = len(nodes)
        if 0 >= self.min:
            (yield (0, {}))
        results = []
        for alt in self.content:
            for (c, r) in generate_matches(alt, nodes):
                (yield (c, r))
                results.append((c, r))
        while results:
            new_results = []
            for (c0, r0) in results:
                if (c0 < nodelen) and (c0 <= self.max):
                    for alt in self.content:
                        for (c1, r1) in generate_matches(alt, nodes[c0:]):
                            if c1 > 0:
                                r = {}
                                r.update(r0)
                                r.update(r1)
                                (yield ((c0 + c1), r))
                                new_results.append(((c0 + c1), r))
            results = new_results

    def _bare_name_matches(self, nodes):
        "Special optimized matcher for bare_name."
        count = 0
        r = {}
        done = False
        max = len(nodes)
        while (not done) and (count < max):
            done = True
            for leaf in self.content:
                if leaf[0].match(nodes[count], r):
                    count += 1
                    done = False
                    break
        r[self.name] = nodes[:count]
        return (count, r)

    def _recursive_matches(self, nodes, count):
        "Helper to recursively yield the matches."
        assert self.content is not None
        if count >= self.min:
            (yield (0, {}))
        if count < self.max:
            for alt in self.content:
                for (c0, r0) in generate_matches(alt, nodes):
                    for (c1, r1) in self._recursive_matches(nodes[c0:], (count + 1)):
                        r = {}
                        r.update(r0)
                        r.update(r1)
                        (yield ((c0 + c1), r))


class NegatedPattern(BasePattern):
    def __init__(self, content=None):
        "\n        Initializer.\n\n        The argument is either a pattern or None.  If it is None, this\n        only matches an empty sequence (effectively '$' in regex\n        lingo).  If it is not None, this matches whenever the argument\n        pattern doesn't have any matches.\n        "
        if content is not None:
            assert isinstance(content, BasePattern), repr(content)
        self.content = content

    def match(self, node):
        return False

    def match_seq(self, nodes):
        return len(nodes) == 0

    def generate_matches(self, nodes):
        if self.content is None:
            if len(nodes) == 0:
                (yield (0, {}))
        else:
            for (c, r) in self.content.generate_matches(nodes):
                return
            (yield (0, {}))


def generate_matches(patterns, nodes):
    "\n    Generator yielding matches for a sequence of patterns and nodes.\n\n    Args:\n        patterns: a sequence of patterns\n        nodes: a sequence of nodes\n\n    Yields:\n        (count, results) tuples where:\n        count: the entire sequence of patterns matches nodes[:count];\n        results: dict containing named submatches.\n        "
    if not patterns:
        (yield (0, {}))
    else:
        (p, rest) = (patterns[0], patterns[1:])
        for (c0, r0) in p.generate_matches(nodes):
            if not rest:
                (yield (c0, r0))
            else:
                for (c1, r1) in generate_matches(rest, nodes[c0:]):
                    r = {}
                    r.update(r0)
                    r.update(r1)
                    (yield ((c0 + c1), r))
