"A bottom-up tree matching algorithm implementation meant to speed\nup 2to3's matching process. After the tree patterns are reduced to\ntheir rarest linear path, a linear Aho-Corasick automaton is\ncreated. The linear automaton traverses the linear paths from the\nleaves to the root of the AST and returns a set of nodes for further\nmatching. This reduces significantly the number of candidate nodes."
__author__ = "George Boutsioukis <gboutsioukis@gmail.com>"
import logging
import itertools
from collections import defaultdict
from . import pytree
from .btm_utils import reduce_tree


class BMNode(object):
    "Class for a node of the Aho-Corasick automaton used in matching"
    count = itertools.count()

    def __init__(self):
        self.transition_table = {}
        self.fixers = []
        self.id = next(BMNode.count)
        self.content = ""


class BottomMatcher(object):
    "The main matcher class. After instantiating the patterns should\n    be added using the add_fixer method"

    def __init__(self):
        self.match = set()
        self.root = BMNode()
        self.nodes = [self.root]
        self.fixers = []
        self.logger = logging.getLogger("RefactoringTool")

    def add_fixer(self, fixer):
        "Reduces a fixer's pattern tree to a linear path and adds it\n        to the matcher(a common Aho-Corasick automaton). The fixer is\n        appended on the matching states and called when they are\n        reached"
        self.fixers.append(fixer)
        tree = reduce_tree(fixer.pattern_tree)
        linear = tree.get_linear_subpattern()
        match_nodes = self.add(linear, start=self.root)
        for match_node in match_nodes:
            match_node.fixers.append(fixer)

    def add(self, pattern, start):
        "Recursively adds a linear pattern to the AC automaton"
        if not pattern:
            return [start]
        if isinstance(pattern[0], tuple):
            match_nodes = []
            for alternative in pattern[0]:
                end_nodes = self.add(alternative, start=start)
                for end in end_nodes:
                    match_nodes.extend(self.add(pattern[1:], end))
            return match_nodes
        else:
            if pattern[0] not in start.transition_table:
                next_node = BMNode()
                start.transition_table[pattern[0]] = next_node
            else:
                next_node = start.transition_table[pattern[0]]
            if pattern[1:]:
                end_nodes = self.add(pattern[1:], start=next_node)
            else:
                end_nodes = [next_node]
            return end_nodes

    def run(self, leaves):
        "The main interface with the bottom matcher. The tree is\n        traversed from the bottom using the constructed\n        automaton. Nodes are only checked once as the tree is\n        retraversed. When the automaton fails, we give it one more\n        shot(in case the above tree matches as a whole with the\n        rejected leaf), then we break for the next leaf. There is the\n        special case of multiple arguments(see code comments) where we\n        recheck the nodes\n\n        Args:\n           The leaves of the AST tree to be matched\n\n        Returns:\n           A dictionary of node matches with fixers as the keys\n        "
        current_ac_node = self.root
        results = defaultdict(list)
        for leaf in leaves:
            current_ast_node = leaf
            while current_ast_node:
                current_ast_node.was_checked = True
                for child in current_ast_node.children:
                    if isinstance(child, pytree.Leaf) and (child.value == ";"):
                        current_ast_node.was_checked = False
                        break
                if current_ast_node.type == 1:
                    node_token = current_ast_node.value
                else:
                    node_token = current_ast_node.type
                if node_token in current_ac_node.transition_table:
                    current_ac_node = current_ac_node.transition_table[node_token]
                    for fixer in current_ac_node.fixers:
                        results[fixer].append(current_ast_node)
                else:
                    current_ac_node = self.root
                    if (
                        current_ast_node.parent is not None
                    ) and current_ast_node.parent.was_checked:
                        break
                    if node_token in current_ac_node.transition_table:
                        current_ac_node = current_ac_node.transition_table[node_token]
                        for fixer in current_ac_node.fixers:
                            results[fixer].append(current_ast_node)
                current_ast_node = current_ast_node.parent
        return results

    def print_ac(self):
        "Prints a graphviz diagram of the BM automaton(for debugging)"
        print("digraph g{")

        def print_node(node):
            for subnode_key in node.transition_table.keys():
                subnode = node.transition_table[subnode_key]
                print(
                    (
                        "%d -> %d [label=%s] //%s"
                        % (
                            node.id,
                            subnode.id,
                            type_repr(subnode_key),
                            str(subnode.fixers),
                        )
                    )
                )
                if subnode_key == 1:
                    print(subnode.content)
                print_node(subnode)

        print_node(self.root)
        print("}")


_type_reprs = {}


def type_repr(type_num):
    global _type_reprs
    if not _type_reprs:
        from .pygram import python_symbols

        for (name, val) in python_symbols.__dict__.items():
            if type(val) == int:
                _type_reprs[val] = name
    return _type_reprs.setdefault(type_num, type_num)
