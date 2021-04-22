"Parser for command line options.\n\nThis module helps scripts to parse the command line arguments in\nsys.argv.  It supports the same conventions as the Unix getopt()\nfunction (including the special meanings of arguments of the form `-'\nand `--').  Long options similar to those supported by GNU software\nmay be used as well via an optional third argument.  This module\nprovides two functions and an exception:\n\ngetopt() -- Parse command line options\ngnu_getopt() -- Like getopt(), but allow option and non-option arguments\nto be intermixed.\nGetoptError -- exception (class) raised with 'opt' attribute, which is the\noption involved with the exception.\n"
__all__ = ["GetoptError", "error", "getopt", "gnu_getopt"]
import os

try:
    from gettext import gettext as _
except ImportError:

    def _(s):
        return s


class GetoptError(Exception):
    opt = ""
    msg = ""

    def __init__(self, msg, opt=""):
        self.msg = msg
        self.opt = opt
        Exception.__init__(self, msg, opt)

    def __str__(self):
        return self.msg


error = GetoptError


def getopt(args, shortopts, longopts=[]):
    "getopt(args, options[, long_options]) -> opts, args\n\n    Parses command line options and parameter list.  args is the\n    argument list to be parsed, without the leading reference to the\n    running program.  Typically, this means \"sys.argv[1:]\".  shortopts\n    is the string of option letters that the script wants to\n    recognize, with options that require an argument followed by a\n    colon (i.e., the same format that Unix getopt() uses).  If\n    specified, longopts is a list of strings with the names of the\n    long options which should be supported.  The leading '--'\n    characters should not be included in the option name.  Options\n    which require an argument should be followed by an equal sign\n    ('=').\n\n    The return value consists of two elements: the first is a list of\n    (option, value) pairs; the second is the list of program arguments\n    left after the option list was stripped (this is a trailing slice\n    of the first argument).  Each option-and-value pair returned has\n    the option as its first element, prefixed with a hyphen (e.g.,\n    '-x'), and the option argument as its second element, or an empty\n    string if the option has no argument.  The options occur in the\n    list in the same order in which they were found, thus allowing\n    multiple occurrences.  Long and short options may be mixed.\n\n    "
    opts = []
    if type(longopts) == type(""):
        longopts = [longopts]
    else:
        longopts = list(longopts)
    while args and args[0].startswith("-") and (args[0] != "-"):
        if args[0] == "--":
            args = args[1:]
            break
        if args[0].startswith("--"):
            (opts, args) = do_longs(opts, args[0][2:], longopts, args[1:])
        else:
            (opts, args) = do_shorts(opts, args[0][1:], shortopts, args[1:])
    return (opts, args)


def gnu_getopt(args, shortopts, longopts=[]):
    "getopt(args, options[, long_options]) -> opts, args\n\n    This function works like getopt(), except that GNU style scanning\n    mode is used by default. This means that option and non-option\n    arguments may be intermixed. The getopt() function stops\n    processing options as soon as a non-option argument is\n    encountered.\n\n    If the first character of the option string is `+', or if the\n    environment variable POSIXLY_CORRECT is set, then option\n    processing stops as soon as a non-option argument is encountered.\n\n    "
    opts = []
    prog_args = []
    if isinstance(longopts, str):
        longopts = [longopts]
    else:
        longopts = list(longopts)
    if shortopts.startswith("+"):
        shortopts = shortopts[1:]
        all_options_first = True
    elif os.environ.get("POSIXLY_CORRECT"):
        all_options_first = True
    else:
        all_options_first = False
    while args:
        if args[0] == "--":
            prog_args += args[1:]
            break
        if args[0][:2] == "--":
            (opts, args) = do_longs(opts, args[0][2:], longopts, args[1:])
        elif (args[0][:1] == "-") and (args[0] != "-"):
            (opts, args) = do_shorts(opts, args[0][1:], shortopts, args[1:])
        elif all_options_first:
            prog_args += args
            break
        else:
            prog_args.append(args[0])
            args = args[1:]
    return (opts, prog_args)


def do_longs(opts, opt, longopts, args):
    try:
        i = opt.index("=")
    except ValueError:
        optarg = None
    else:
        (opt, optarg) = (opt[:i], opt[(i + 1) :])
    (has_arg, opt) = long_has_args(opt, longopts)
    if has_arg:
        if optarg is None:
            if not args:
                raise GetoptError((_("option --%s requires argument") % opt), opt)
            (optarg, args) = (args[0], args[1:])
    elif optarg is not None:
        raise GetoptError((_("option --%s must not have an argument") % opt), opt)
    opts.append((("--" + opt), (optarg or "")))
    return (opts, args)


def long_has_args(opt, longopts):
    possibilities = [o for o in longopts if o.startswith(opt)]
    if not possibilities:
        raise GetoptError((_("option --%s not recognized") % opt), opt)
    if opt in possibilities:
        return (False, opt)
    elif (opt + "=") in possibilities:
        return (True, opt)
    if len(possibilities) > 1:
        raise GetoptError((_("option --%s not a unique prefix") % opt), opt)
    assert len(possibilities) == 1
    unique_match = possibilities[0]
    has_arg = unique_match.endswith("=")
    if has_arg:
        unique_match = unique_match[:(-1)]
    return (has_arg, unique_match)


def do_shorts(opts, optstring, shortopts, args):
    while optstring != "":
        (opt, optstring) = (optstring[0], optstring[1:])
        if short_has_arg(opt, shortopts):
            if optstring == "":
                if not args:
                    raise GetoptError((_("option -%s requires argument") % opt), opt)
                (optstring, args) = (args[0], args[1:])
            (optarg, optstring) = (optstring, "")
        else:
            optarg = ""
        opts.append((("-" + opt), optarg))
    return (opts, args)


def short_has_arg(opt, shortopts):
    for i in range(len(shortopts)):
        if opt == shortopts[i] != ":":
            return shortopts.startswith(":", (i + 1))
    raise GetoptError((_("option -%s not recognized") % opt), opt)


if __name__ == "__main__":
    import sys

    print(getopt(sys.argv[1:], "a:b", ["alpha=", "beta"]))
