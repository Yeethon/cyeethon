"Fixer that changes map(F, ...) into list(map(F, ...)) unless there\nexists a 'from future_builtins import map' statement in the top-level\nnamespace.\n\nAs a special case, map(None, X) is changed into list(X).  (This is\nnecessary because the semantics are changed in this case -- the new\nmap(None, X) is equivalent to [(x,) for x in X].)\n\nWe avoid the transformation (except for the special case mentioned\nabove) if the map() call is directly contained in iter(<>), list(<>),\ntuple(<>), sorted(<>), ...join(<>), or for V in <>:.\n\nNOTE: This is still not correct if the original code was depending on\nmap(F, X, Y, ...) to go on until the longest argument is exhausted,\nsubstituting None for missing values -- like zip(), it now stops as\nsoon as the shortest argument is exhausted.\n"
from ..pgen2 import token
from .. import fixer_base
from ..fixer_util import Name, ArgList, Call, ListComp, in_special_context
from ..pygram import python_symbols as syms
from ..pytree import Node


class FixMap(fixer_base.ConditionalFix):
    BM_compatible = True
    PATTERN = "\n    map_none=power<\n        'map'\n        trailer< '(' arglist< 'None' ',' arg=any [','] > ')' >\n        [extra_trailers=trailer*]\n    >\n    |\n    map_lambda=power<\n        'map'\n        trailer<\n            '('\n            arglist<\n                lambdef< 'lambda'\n                         (fp=NAME | vfpdef< '(' fp=NAME ')'> ) ':' xp=any\n                >\n                ','\n                it=any\n            >\n            ')'\n        >\n        [extra_trailers=trailer*]\n    >\n    |\n    power<\n        'map' args=trailer< '(' [any] ')' >\n        [extra_trailers=trailer*]\n    >\n    "
    skip_on = "future_builtins.map"

    def transform(self, node, results):
        if self.should_skip(node):
            return
        trailers = []
        if "extra_trailers" in results:
            for t in results["extra_trailers"]:
                trailers.append(t.clone())
        if node.parent.type == syms.simple_stmt:
            self.warning(node, "You should use a for loop here")
            new = node.clone()
            new.prefix = ""
            new = Call(Name("list"), [new])
        elif "map_lambda" in results:
            new = ListComp(
                results["xp"].clone(), results["fp"].clone(), results["it"].clone()
            )
            new = Node(syms.power, ([new] + trailers), prefix="")
        else:
            if "map_none" in results:
                new = results["arg"].clone()
                new.prefix = ""
            else:
                if "args" in results:
                    args = results["args"]
                    if (
                        (args.type == syms.trailer)
                        and (args.children[1].type == syms.arglist)
                        and (args.children[1].children[0].type == token.NAME)
                        and (args.children[1].children[0].value == "None")
                    ):
                        self.warning(
                            node,
                            "cannot convert map(None, ...) with multiple arguments because map() now truncates to the shortest sequence",
                        )
                        return
                    new = Node(syms.power, [Name("map"), args.clone()])
                    new.prefix = ""
                if in_special_context(node):
                    return None
            new = Node(syms.power, ([Name("list"), ArgList([new])] + trailers))
            new.prefix = ""
        new.prefix = node.prefix
        return new
