'Word completion for GNU readline.\n\nThe completer completes keywords, built-ins and globals in a selectable\nnamespace (which defaults to __main__); when completing NAME.NAME..., it\nevaluates (!) the expression up to the last dot and completes its attributes.\n\nIt\'s very cool to do "import sys" type "sys.", hit the completion key (twice),\nand see the list of names defined by the sys module!\n\nTip: to use the tab key as the completion key, call\n\n    readline.parse_and_bind("tab: complete")\n\nNotes:\n\n- Exceptions raised by the completer function are *ignored* (and generally cause\n  the completion to fail).  This is a feature -- since readline sets the tty\n  device in raw (or cbreak) mode, printing a traceback wouldn\'t work well\n  without some complicated hoopla to save, reset and restore the tty state.\n\n- The evaluation of the NAME.NAME... form may cause arbitrary application\n  defined code to be executed if an object with a __getattr__ hook is found.\n  Since it is the responsibility of the application (or the user) to enable this\n  feature, I consider this an acceptable risk.  More complicated expressions\n  (e.g. function calls or indexing operations) are *not* evaluated.\n\n- When the original stdin is not a tty device, GNU readline is never\n  used, and this module (and the readline module) are silently inactive.\n\n'
import atexit
import builtins
import inspect
import __main__

__all__ = ["Completer"]


class Completer:
    def __init__(self, namespace=None):
        "Create a new completer for the command line.\n\n        Completer([namespace]) -> completer instance.\n\n        If unspecified, the default namespace where completions are performed\n        is __main__ (technically, __main__.__dict__). Namespaces should be\n        given as dictionaries.\n\n        Completer instances should be used as the completion mechanism of\n        readline via the set_completer() call:\n\n        readline.set_completer(Completer(my_namespace).complete)\n        "
        if namespace and (not isinstance(namespace, dict)):
            raise TypeError("namespace must be a dictionary")
        if namespace is None:
            self.use_main_ns = 1
        else:
            self.use_main_ns = 0
            self.namespace = namespace

    def complete(self, text, state):
        "Return the next possible completion for 'text'.\n\n        This is called successively with state == 0, 1, 2, ... until it\n        returns None.  The completion should begin with 'text'.\n\n        "
        if self.use_main_ns:
            self.namespace = __main__.__dict__
        if not text.strip():
            if state == 0:
                if _readline_available:
                    readline.insert_text("\t")
                    readline.redisplay()
                    return ""
                else:
                    return "\t"
            else:
                return None
        if state == 0:
            if "." in text:
                self.matches = self.attr_matches(text)
            else:
                self.matches = self.global_matches(text)
        try:
            return self.matches[state]
        except IndexError:
            return None

    def _callable_postfix(self, val, word):
        if callable(val):
            word += "("
            try:
                if not inspect.signature(val).parameters:
                    word += ")"
            except ValueError:
                pass
        return word

    def global_matches(self, text):
        "Compute matches when text is a simple name.\n\n        Return a list of all keywords, built-in functions and names currently\n        defined in self.namespace that match.\n\n        "
        import keyword

        matches = []
        seen = {"__builtins__"}
        n = len(text)
        for word in keyword.kwlist:
            if word[:n] == text:
                seen.add(word)
                if word in {"finally", "try"}:
                    word = word + ":"
                elif word not in {
                    "False",
                    "None",
                    "True",
                    "break",
                    "continue",
                    "pass",
                    "else",
                }:
                    word = word + " "
                matches.append(word)
        for nspace in [self.namespace, builtins.__dict__]:
            for (word, val) in nspace.items():
                if (word[:n] == text) and (word not in seen):
                    seen.add(word)
                    matches.append(self._callable_postfix(val, word))
        return matches

    def attr_matches(self, text):
        "Compute matches when text contains a dot.\n\n        Assuming the text is of the form NAME.NAME....[NAME], and is\n        evaluable in self.namespace, it will be evaluated and its attributes\n        (as revealed by dir()) are used as possible completions.  (For class\n        instances, class members are also considered.)\n\n        WARNING: this can still invoke arbitrary C code, if an object\n        with a __getattr__ hook is evaluated.\n\n        "
        import re

        m = re.match("(\\w+(\\.\\w+)*)\\.(\\w*)", text)
        if not m:
            return []
        (expr, attr) = m.group(1, 3)
        try:
            thisobject = eval(expr, self.namespace)
        except Exception:
            return []
        words = set(dir(thisobject))
        words.discard("__builtins__")
        if hasattr(thisobject, "__class__"):
            words.add("__class__")
            words.update(get_class_members(thisobject.__class__))
        matches = []
        n = len(attr)
        if attr == "":
            noprefix = "_"
        elif attr == "_":
            noprefix = "__"
        else:
            noprefix = None
        while True:
            for word in words:
                if (word[:n] == attr) and (
                    not (noprefix and (word[: (n + 1)] == noprefix))
                ):
                    match = "%s.%s" % (expr, word)
                    try:
                        val = getattr(thisobject, word)
                    except Exception:
                        pass
                    else:
                        match = self._callable_postfix(val, match)
                    matches.append(match)
            if matches or (not noprefix):
                break
            if noprefix == "_":
                noprefix = "__"
            else:
                noprefix = None
        matches.sort()
        return matches


def get_class_members(klass):
    ret = dir(klass)
    if hasattr(klass, "__bases__"):
        for base in klass.__bases__:
            ret = ret + get_class_members(base)
    return ret


try:
    import readline
except ImportError:
    _readline_available = False
else:
    readline.set_completer(Completer().complete)
    atexit.register((lambda: readline.set_completer(None)))
    _readline_available = True
