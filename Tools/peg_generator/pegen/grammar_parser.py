import ast
from typing import Optional, Any
from pegen.parser import memoize, memoize_left_rec, logger, Parser
from ast import literal_eval
from pegen.grammar import (
    Alt,
    Cut,
    Forced,
    Gather,
    Group,
    Item,
    Lookahead,
    LookaheadOrCut,
    MetaTuple,
    MetaList,
    NameLeaf,
    NamedItem,
    NamedItemList,
    NegativeLookahead,
    Opt,
    Plain,
    PositiveLookahead,
    Repeat0,
    Repeat1,
    Rhs,
    Rule,
    RuleList,
    RuleName,
    Grammar,
    StringLeaf,
)


class GeneratedParser(Parser):
    @memoize
    def start(self) -> Optional[Grammar]:
        mark = self.mark()
        cut = False
        if (grammar := self.grammar()) and (endmarker := self.expect("ENDMARKER")):
            return grammar
        self.reset(mark)
        if cut:
            return None
        return None

    @memoize
    def grammar(self) -> Optional[Grammar]:
        mark = self.mark()
        cut = False
        if (metas := self.metas()) and (rules := self.rules()):
            return Grammar(rules, metas)
        self.reset(mark)
        if cut:
            return None
        cut = False
        if (rules := self.rules()) :
            return Grammar(rules, [])
        self.reset(mark)
        if cut:
            return None
        return None

    @memoize
    def metas(self) -> Optional[MetaList]:
        mark = self.mark()
        cut = False
        if (meta := self.meta()) and (metas := self.metas()):
            return [meta] + metas
        self.reset(mark)
        if cut:
            return None
        cut = False
        if (meta := self.meta()) :
            return [meta]
        self.reset(mark)
        if cut:
            return None
        return None

    @memoize
    def meta(self) -> Optional[MetaTuple]:
        mark = self.mark()
        cut = False
        if (
            (literal := self.expect("@"))
            and (name := self.name())
            and (newline := self.expect("NEWLINE"))
        ):
            return (name.string, None)
        self.reset(mark)
        if cut:
            return None
        cut = False
        if (
            (literal := self.expect("@"))
            and (a := self.name())
            and (b := self.name())
            and (newline := self.expect("NEWLINE"))
        ):
            return (a.string, b.string)
        self.reset(mark)
        if cut:
            return None
        cut = False
        if (
            (literal := self.expect("@"))
            and (name := self.name())
            and (string := self.string())
            and (newline := self.expect("NEWLINE"))
        ):
            return (name.string, literal_eval(string.string))
        self.reset(mark)
        if cut:
            return None
        return None

    @memoize
    def rules(self) -> Optional[RuleList]:
        mark = self.mark()
        cut = False
        if (rule := self.rule()) and (rules := self.rules()):
            return [rule] + rules
        self.reset(mark)
        if cut:
            return None
        cut = False
        if (rule := self.rule()) :
            return [rule]
        self.reset(mark)
        if cut:
            return None
        return None

    @memoize
    def rule(self) -> Optional[Rule]:
        mark = self.mark()
        cut = False
        if (
            (rulename := self.rulename())
            and ((opt := self.memoflag()),)
            and (literal := self.expect(":"))
            and (alts := self.alts())
            and (newline := self.expect("NEWLINE"))
            and (indent := self.expect("INDENT"))
            and (more_alts := self.more_alts())
            and (dedent := self.expect("DEDENT"))
        ):
            return Rule(
                rulename[0], rulename[1], Rhs((alts.alts + more_alts.alts)), memo=opt
            )
        self.reset(mark)
        if cut:
            return None
        cut = False
        if (
            (rulename := self.rulename())
            and ((opt := self.memoflag()),)
            and (literal := self.expect(":"))
            and (newline := self.expect("NEWLINE"))
            and (indent := self.expect("INDENT"))
            and (more_alts := self.more_alts())
            and (dedent := self.expect("DEDENT"))
        ):
            return Rule(rulename[0], rulename[1], more_alts, memo=opt)
        self.reset(mark)
        if cut:
            return None
        cut = False
        if (
            (rulename := self.rulename())
            and ((opt := self.memoflag()),)
            and (literal := self.expect(":"))
            and (alts := self.alts())
            and (newline := self.expect("NEWLINE"))
        ):
            return Rule(rulename[0], rulename[1], alts, memo=opt)
        self.reset(mark)
        if cut:
            return None
        return None

    @memoize
    def rulename(self) -> Optional[RuleName]:
        mark = self.mark()
        cut = False
        if (
            (name := self.name())
            and (literal := self.expect("["))
            and (type := self.name())
            and (literal_1 := self.expect("*"))
            and (literal_2 := self.expect("]"))
        ):
            return (name.string, (type.string + "*"))
        self.reset(mark)
        if cut:
            return None
        cut = False
        if (
            (name := self.name())
            and (literal := self.expect("["))
            and (type := self.name())
            and (literal_1 := self.expect("]"))
        ):
            return (name.string, type.string)
        self.reset(mark)
        if cut:
            return None
        cut = False
        if (name := self.name()) :
            return (name.string, None)
        self.reset(mark)
        if cut:
            return None
        return None

    @memoize
    def memoflag(self) -> Optional[str]:
        mark = self.mark()
        cut = False
        if (
            (literal := self.expect("("))
            and (literal_1 := self.expect("memo"))
            and (literal_2 := self.expect(")"))
        ):
            return "memo"
        self.reset(mark)
        if cut:
            return None
        return None

    @memoize
    def alts(self) -> Optional[Rhs]:
        mark = self.mark()
        cut = False
        if (
            (alt := self.alt())
            and (literal := self.expect("|"))
            and (alts := self.alts())
        ):
            return Rhs(([alt] + alts.alts))
        self.reset(mark)
        if cut:
            return None
        cut = False
        if (alt := self.alt()) :
            return Rhs([alt])
        self.reset(mark)
        if cut:
            return None
        return None

    @memoize
    def more_alts(self) -> Optional[Rhs]:
        mark = self.mark()
        cut = False
        if (
            (literal := self.expect("|"))
            and (alts := self.alts())
            and (newline := self.expect("NEWLINE"))
            and (more_alts := self.more_alts())
        ):
            return Rhs((alts.alts + more_alts.alts))
        self.reset(mark)
        if cut:
            return None
        cut = False
        if (
            (literal := self.expect("|"))
            and (alts := self.alts())
            and (newline := self.expect("NEWLINE"))
        ):
            return Rhs(alts.alts)
        self.reset(mark)
        if cut:
            return None
        return None

    @memoize
    def alt(self) -> Optional[Alt]:
        mark = self.mark()
        cut = False
        if (
            (items := self.items())
            and (literal := self.expect("$"))
            and (action := self.action())
        ):
            return Alt(
                (items + [NamedItem(None, NameLeaf("ENDMARKER"))]), action=action
            )
        self.reset(mark)
        if cut:
            return None
        cut = False
        if (items := self.items()) and (literal := self.expect("$")):
            return Alt((items + [NamedItem(None, NameLeaf("ENDMARKER"))]), action=None)
        self.reset(mark)
        if cut:
            return None
        cut = False
        if (items := self.items()) and (action := self.action()):
            return Alt(items, action=action)
        self.reset(mark)
        if cut:
            return None
        cut = False
        if (items := self.items()) :
            return Alt(items, action=None)
        self.reset(mark)
        if cut:
            return None
        return None

    @memoize
    def items(self) -> Optional[NamedItemList]:
        mark = self.mark()
        cut = False
        if (named_item := self.named_item()) and (items := self.items()):
            return [named_item] + items
        self.reset(mark)
        if cut:
            return None
        cut = False
        if (named_item := self.named_item()) :
            return [named_item]
        self.reset(mark)
        if cut:
            return None
        return None

    @memoize
    def named_item(self) -> Optional[NamedItem]:
        mark = self.mark()
        cut = False
        if (
            (name := self.name())
            and (literal := self.expect("["))
            and (type := self.name())
            and (literal_1 := self.expect("*"))
            and (literal_2 := self.expect("]"))
            and (literal_3 := self.expect("="))
            and (cut := True)
            and (item := self.item())
        ):
            return NamedItem(name.string, item, f"{type.string}*")
        self.reset(mark)
        if cut:
            return None
        cut = False
        if (
            (name := self.name())
            and (literal := self.expect("["))
            and (type := self.name())
            and (literal_1 := self.expect("]"))
            and (literal_2 := self.expect("="))
            and (cut := True)
            and (item := self.item())
        ):
            return NamedItem(name.string, item, type.string)
        self.reset(mark)
        if cut:
            return None
        cut = False
        if (
            (name := self.name())
            and (literal := self.expect("="))
            and (cut := True)
            and (item := self.item())
        ):
            return NamedItem(name.string, item)
        self.reset(mark)
        if cut:
            return None
        cut = False
        if (item := self.item()) :
            return NamedItem(None, item)
        self.reset(mark)
        if cut:
            return None
        cut = False
        if (it := self.forced_atom()) :
            return NamedItem(None, it)
        self.reset(mark)
        if cut:
            return None
        cut = False
        if (it := self.lookahead()) :
            return NamedItem(None, it)
        self.reset(mark)
        if cut:
            return None
        return None

    @memoize
    def forced_atom(self) -> Optional[NamedItem]:
        mark = self.mark()
        cut = False
        if (
            (literal := self.expect("&"))
            and (literal_1 := self.expect("&"))
            and (cut := True)
            and (atom := self.atom())
        ):
            return Forced(atom)
        self.reset(mark)
        if cut:
            return None
        return None

    @memoize
    def lookahead(self) -> Optional[LookaheadOrCut]:
        mark = self.mark()
        cut = False
        if (literal := self.expect("&")) and (cut := True) and (atom := self.atom()):
            return PositiveLookahead(atom)
        self.reset(mark)
        if cut:
            return None
        cut = False
        if (literal := self.expect("!")) and (cut := True) and (atom := self.atom()):
            return NegativeLookahead(atom)
        self.reset(mark)
        if cut:
            return None
        cut = False
        if (literal := self.expect("~")) :
            return Cut()
        self.reset(mark)
        if cut:
            return None
        return None

    @memoize
    def item(self) -> Optional[Item]:
        mark = self.mark()
        cut = False
        if (
            (literal := self.expect("["))
            and (cut := True)
            and (alts := self.alts())
            and (literal_1 := self.expect("]"))
        ):
            return Opt(alts)
        self.reset(mark)
        if cut:
            return None
        cut = False
        if (atom := self.atom()) and (literal := self.expect("?")):
            return Opt(atom)
        self.reset(mark)
        if cut:
            return None
        cut = False
        if (atom := self.atom()) and (literal := self.expect("*")):
            return Repeat0(atom)
        self.reset(mark)
        if cut:
            return None
        cut = False
        if (atom := self.atom()) and (literal := self.expect("+")):
            return Repeat1(atom)
        self.reset(mark)
        if cut:
            return None
        cut = False
        if (
            (sep := self.atom())
            and (literal := self.expect("."))
            and (node := self.atom())
            and (literal_1 := self.expect("+"))
        ):
            return Gather(sep, node)
        self.reset(mark)
        if cut:
            return None
        cut = False
        if (atom := self.atom()) :
            return atom
        self.reset(mark)
        if cut:
            return None
        return None

    @memoize
    def atom(self) -> Optional[Plain]:
        mark = self.mark()
        cut = False
        if (
            (literal := self.expect("("))
            and (cut := True)
            and (alts := self.alts())
            and (literal_1 := self.expect(")"))
        ):
            return Group(alts)
        self.reset(mark)
        if cut:
            return None
        cut = False
        if (name := self.name()) :
            return NameLeaf(name.string)
        self.reset(mark)
        if cut:
            return None
        cut = False
        if (string := self.string()) :
            return StringLeaf(string.string)
        self.reset(mark)
        if cut:
            return None
        return None

    @memoize
    def action(self) -> Optional[str]:
        mark = self.mark()
        cut = False
        if (
            (literal := self.expect("{"))
            and (cut := True)
            and (target_atoms := self.target_atoms())
            and (literal_1 := self.expect("}"))
        ):
            return target_atoms
        self.reset(mark)
        if cut:
            return None
        return None

    @memoize
    def target_atoms(self) -> Optional[str]:
        mark = self.mark()
        cut = False
        if (target_atom := self.target_atom()) and (
            target_atoms := self.target_atoms()
        ):
            return (target_atom + " ") + target_atoms
        self.reset(mark)
        if cut:
            return None
        cut = False
        if (target_atom := self.target_atom()) :
            return target_atom
        self.reset(mark)
        if cut:
            return None
        return None

    @memoize
    def target_atom(self) -> Optional[str]:
        mark = self.mark()
        cut = False
        if (
            (literal := self.expect("{"))
            and (cut := True)
            and (target_atoms := self.target_atoms())
            and (literal_1 := self.expect("}"))
        ):
            return ("{" + target_atoms) + "}"
        self.reset(mark)
        if cut:
            return None
        cut = False
        if (name := self.name()) :
            return name.string
        self.reset(mark)
        if cut:
            return None
        cut = False
        if (number := self.number()) :
            return number.string
        self.reset(mark)
        if cut:
            return None
        cut = False
        if (string := self.string()) :
            return string.string
        self.reset(mark)
        if cut:
            return None
        cut = False
        if (literal := self.expect("?")) :
            return "?"
        self.reset(mark)
        if cut:
            return None
        cut = False
        if (literal := self.expect(":")) :
            return ":"
        self.reset(mark)
        if cut:
            return None
        cut = False
        if self.negative_lookahead(self.expect, "}") and (op := self.op()):
            return op.string
        self.reset(mark)
        if cut:
            return None
        return None


if __name__ == "__main__":
    from pegen.parser import simple_parser_main

    simple_parser_main(GeneratedParser)
