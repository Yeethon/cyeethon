"distutils.fancy_getopt\n\nWrapper around the standard getopt module that provides the following\nadditional features:\n  * short and long options are tied together\n  * options have help strings, so fancy_getopt could potentially\n    create a complete usage summary\n  * options set attributes of a passed-in object\n"
import sys, string, re
import getopt
from distutils.errors import *

longopt_pat = "[a-zA-Z](?:[a-zA-Z0-9-]*)"
longopt_re = re.compile(("^%s$" % longopt_pat))
neg_alias_re = re.compile(("^(%s)=!(%s)$" % (longopt_pat, longopt_pat)))
longopt_xlate = str.maketrans("-", "_")


class FancyGetopt:
    'Wrapper around the standard \'getopt()\' module that provides some\n    handy extra functionality:\n      * short and long options are tied together\n      * options have help strings, and help text can be assembled\n        from them\n      * options set attributes of a passed-in object\n      * boolean options can have "negative aliases" -- eg. if\n        --quiet is the "negative alias" of --verbose, then "--quiet"\n        on the command line sets \'verbose\' to false\n    '

    def __init__(self, option_table=None):
        self.option_table = option_table
        self.option_index = {}
        if self.option_table:
            self._build_index()
        self.alias = {}
        self.negative_alias = {}
        self.short_opts = []
        self.long_opts = []
        self.short2long = {}
        self.attr_name = {}
        self.takes_arg = {}
        self.option_order = []

    def _build_index(self):
        self.option_index.clear()
        for option in self.option_table:
            self.option_index[option[0]] = option

    def set_option_table(self, option_table):
        self.option_table = option_table
        self._build_index()

    def add_option(self, long_option, short_option=None, help_string=None):
        if long_option in self.option_index:
            raise DistutilsGetoptError(
                ("option conflict: already an option '%s'" % long_option)
            )
        else:
            option = (long_option, short_option, help_string)
            self.option_table.append(option)
            self.option_index[long_option] = option

    def has_option(self, long_option):
        "Return true if the option table for this parser has an\n        option with long name 'long_option'."
        return long_option in self.option_index

    def get_attr_name(self, long_option):
        "Translate long option name 'long_option' to the form it\n        has as an attribute of some object: ie., translate hyphens\n        to underscores."
        return long_option.translate(longopt_xlate)

    def _check_alias_dict(self, aliases, what):
        assert isinstance(aliases, dict)
        for (alias, opt) in aliases.items():
            if alias not in self.option_index:
                raise DistutilsGetoptError(
                    ("invalid %s '%s': option '%s' not defined" % (what, alias, alias))
                )
            if opt not in self.option_index:
                raise DistutilsGetoptError(
                    (
                        "invalid %s '%s': aliased option '%s' not defined"
                        % (what, alias, opt)
                    )
                )

    def set_aliases(self, alias):
        "Set the aliases for this option parser."
        self._check_alias_dict(alias, "alias")
        self.alias = alias

    def set_negative_aliases(self, negative_alias):
        "Set the negative aliases for this option parser.\n        'negative_alias' should be a dictionary mapping option names to\n        option names, both the key and value must already be defined\n        in the option table."
        self._check_alias_dict(negative_alias, "negative alias")
        self.negative_alias = negative_alias

    def _grok_option_table(self):
        "Populate the various data structures that keep tabs on the\n        option table.  Called by 'getopt()' before it can do anything\n        worthwhile.\n        "
        self.long_opts = []
        self.short_opts = []
        self.short2long.clear()
        self.repeat = {}
        for option in self.option_table:
            if len(option) == 3:
                (long, short, help) = option
                repeat = 0
            elif len(option) == 4:
                (long, short, help, repeat) = option
            else:
                raise ValueError(("invalid option tuple: %r" % (option,)))
            if (not isinstance(long, str)) or (len(long) < 2):
                raise DistutilsGetoptError(
                    ("invalid long option '%s': must be a string of length >= 2" % long)
                )
            if not ((short is None) or (isinstance(short, str) and (len(short) == 1))):
                raise DistutilsGetoptError(
                    (
                        "invalid short option '%s': must a single character or None"
                        % short
                    )
                )
            self.repeat[long] = repeat
            self.long_opts.append(long)
            if long[(-1)] == "=":
                if short:
                    short = short + ":"
                long = long[0:(-1)]
                self.takes_arg[long] = 1
            else:
                alias_to = self.negative_alias.get(long)
                if alias_to is not None:
                    if self.takes_arg[alias_to]:
                        raise DistutilsGetoptError(
                            (
                                "invalid negative alias '%s': aliased option '%s' takes a value"
                                % (long, alias_to)
                            )
                        )
                    self.long_opts[(-1)] = long
                self.takes_arg[long] = 0
            alias_to = self.alias.get(long)
            if alias_to is not None:
                if self.takes_arg[long] != self.takes_arg[alias_to]:
                    raise DistutilsGetoptError(
                        (
                            "invalid alias '%s': inconsistent with aliased option '%s' (one of them takes a value, the other doesn't"
                            % (long, alias_to)
                        )
                    )
            if not longopt_re.match(long):
                raise DistutilsGetoptError(
                    (
                        "invalid long option name '%s' (must be letters, numbers, hyphens only"
                        % long
                    )
                )
            self.attr_name[long] = self.get_attr_name(long)
            if short:
                self.short_opts.append(short)
                self.short2long[short[0]] = long

    def getopt(self, args=None, object=None):
        "Parse command-line options in args. Store as attributes on object.\n\n        If 'args' is None or not supplied, uses 'sys.argv[1:]'.  If\n        'object' is None or not supplied, creates a new OptionDummy\n        object, stores option values there, and returns a tuple (args,\n        object).  If 'object' is supplied, it is modified in place and\n        'getopt()' just returns 'args'; in both cases, the returned\n        'args' is a modified copy of the passed-in 'args' list, which\n        is left untouched.\n        "
        if args is None:
            args = sys.argv[1:]
        if object is None:
            object = OptionDummy()
            created_object = True
        else:
            created_object = False
        self._grok_option_table()
        short_opts = " ".join(self.short_opts)
        try:
            (opts, args) = getopt.getopt(args, short_opts, self.long_opts)
        except getopt.error as msg:
            raise DistutilsArgError(msg)
        for (opt, val) in opts:
            if (len(opt) == 2) and (opt[0] == "-"):
                opt = self.short2long[opt[1]]
            else:
                assert (len(opt) > 2) and (opt[:2] == "--")
                opt = opt[2:]
            alias = self.alias.get(opt)
            if alias:
                opt = alias
            if not self.takes_arg[opt]:
                assert val == "", "boolean option can't have value"
                alias = self.negative_alias.get(opt)
                if alias:
                    opt = alias
                    val = 0
                else:
                    val = 1
            attr = self.attr_name[opt]
            if val and (self.repeat.get(attr) is not None):
                val = getattr(object, attr, 0) + 1
            setattr(object, attr, val)
            self.option_order.append((opt, val))
        if created_object:
            return (args, object)
        else:
            return args

    def get_option_order(self):
        "Returns the list of (option, value) tuples processed by the\n        previous run of 'getopt()'.  Raises RuntimeError if\n        'getopt()' hasn't been called yet.\n        "
        if self.option_order is None:
            raise RuntimeError("'getopt()' hasn't been called yet")
        else:
            return self.option_order

    def generate_help(self, header=None):
        "Generate help text (a list of strings, one per suggested line of\n        output) from the option table for this FancyGetopt object.\n        "
        max_opt = 0
        for option in self.option_table:
            long = option[0]
            short = option[1]
            l = len(long)
            if long[(-1)] == "=":
                l = l - 1
            if short is not None:
                l = l + 5
            if l > max_opt:
                max_opt = l
        opt_width = ((max_opt + 2) + 2) + 2
        line_width = 78
        text_width = line_width - opt_width
        big_indent = " " * opt_width
        if header:
            lines = [header]
        else:
            lines = ["Option summary:"]
        for option in self.option_table:
            (long, short, help) = option[:3]
            text = wrap_text(help, text_width)
            if long[(-1)] == "=":
                long = long[0:(-1)]
            if short is None:
                if text:
                    lines.append(("  --%-*s  %s" % (max_opt, long, text[0])))
                else:
                    lines.append(("  --%-*s  " % (max_opt, long)))
            else:
                opt_names = "%s (-%s)" % (long, short)
                if text:
                    lines.append(("  --%-*s  %s" % (max_opt, opt_names, text[0])))
                else:
                    lines.append(("  --%-*s" % opt_names))
            for l in text[1:]:
                lines.append((big_indent + l))
        return lines

    def print_help(self, header=None, file=None):
        if file is None:
            file = sys.stdout
        for line in self.generate_help(header):
            file.write((line + "\n"))


def fancy_getopt(options, negative_opt, object, args):
    parser = FancyGetopt(options)
    parser.set_negative_aliases(negative_opt)
    return parser.getopt(args, object)


WS_TRANS = {ord(_wschar): " " for _wschar in string.whitespace}


def wrap_text(text, width):
    "wrap_text(text : string, width : int) -> [string]\n\n    Split 'text' into multiple lines of no more than 'width' characters\n    each, and return the list of strings that results.\n    "
    if text is None:
        return []
    if len(text) <= width:
        return [text]
    text = text.expandtabs()
    text = text.translate(WS_TRANS)
    chunks = re.split("( +|-+)", text)
    chunks = [ch for ch in chunks if ch]
    lines = []
    while chunks:
        cur_line = []
        cur_len = 0
        while chunks:
            l = len(chunks[0])
            if (cur_len + l) <= width:
                cur_line.append(chunks[0])
                del chunks[0]
                cur_len = cur_len + l
            else:
                if cur_line and (cur_line[(-1)][0] == " "):
                    del cur_line[(-1)]
                break
        if chunks:
            if cur_len == 0:
                cur_line.append(chunks[0][0:width])
                chunks[0] = chunks[0][width:]
            if chunks[0][0] == " ":
                del chunks[0]
        lines.append("".join(cur_line))
    return lines


def translate_longopt(opt):
    'Convert a long option name to a valid Python identifier by\n    changing "-" to "_".\n    '
    return opt.translate(longopt_xlate)


class OptionDummy:
    "Dummy class just used as a place to hold command-line option\n    values as instance attributes."

    def __init__(self, options=[]):
        "Create a new OptionDummy instance.  The attributes listed in\n        'options' will be initialized to None."
        for opt in options:
            setattr(self, opt, None)


if __name__ == "__main__":
    text = "Tra-la-la, supercalifragilisticexpialidocious.\nHow *do* you spell that odd word, anyways?\n(Someone ask Mary -- she'll know [or she'll\nsay, \"How should I know?\"].)"
    for w in (10, 20, 30, 40):
        print(("width: %d" % w))
        print("\n".join(wrap_text(text, w)))
        print()
