from lib2to3.fixer_base import BaseFix
from lib2to3.fixer_util import Name


class FixParrot(BaseFix):
    "\n    Change functions named 'parrot' to 'cheese'.\n    "
    PATTERN = "funcdef < 'def' name='parrot' any* >"

    def transform(self, node, results):
        name = results["name"]
        name.replace(Name("cheese", name.prefix))
