"Fixer for intern().\n\nintern(s) -> sys.intern(s)"
from .. import fixer_base
from ..fixer_util import ImportAndCall, touch_import


class FixIntern(fixer_base.BaseFix):
    BM_compatible = True
    order = "pre"
    PATTERN = "\n    power< 'intern'\n           trailer< lpar='('\n                    ( not(arglist | argument<any '=' any>) obj=any\n                      | obj=arglist<(not argument<any '=' any>) any ','> )\n                    rpar=')' >\n           after=any*\n    >\n    "

    def transform(self, node, results):
        if results:
            obj = results["obj"]
            if obj:
                if (obj.type == self.syms.argument) and (
                    obj.children[0].value in {"**", "*"}
                ):
                    return
        names = ("sys", "intern")
        new = ImportAndCall(node, results, names)
        touch_import(None, "sys", node)
        return new
