"A collection of string constants.\n\nPublic module variables:\n\nwhitespace -- a string containing all ASCII whitespace\nascii_lowercase -- a string containing all ASCII lowercase letters\nascii_uppercase -- a string containing all ASCII uppercase letters\nascii_letters -- a string containing all ASCII letters\ndigits -- a string containing all ASCII decimal digits\nhexdigits -- a string containing all ASCII hexadecimal digits\noctdigits -- a string containing all ASCII octal digits\npunctuation -- a string containing all ASCII punctuation characters\nprintable -- a string containing all ASCII characters considered printable\n\n"
__all__ = [
    "ascii_letters",
    "ascii_lowercase",
    "ascii_uppercase",
    "capwords",
    "digits",
    "hexdigits",
    "octdigits",
    "printable",
    "punctuation",
    "whitespace",
    "Formatter",
    "Template",
]
import _string

whitespace = " \t\n\r\x0b\x0c"
ascii_lowercase = "abcdefghijklmnopqrstuvwxyz"
ascii_uppercase = "ABCDEFGHIJKLMNOPQRSTUVWXYZ"
ascii_letters = ascii_lowercase + ascii_uppercase
digits = "0123456789"
hexdigits = (digits + "abcdef") + "ABCDEF"
octdigits = "01234567"
punctuation = "!\"#$%&'()*+,-./:;<=>?@[\\]^_`{|}~"
printable = ((digits + ascii_letters) + punctuation) + whitespace


def capwords(s, sep=None):
    "capwords(s [,sep]) -> string\n\n    Split the argument into words using split, capitalize each\n    word using capitalize, and join the capitalized words using\n    join.  If the optional second argument sep is absent or None,\n    runs of whitespace characters are replaced by a single space\n    and leading and trailing whitespace are removed, otherwise\n    sep is used to split and join the words.\n\n    "
    return (sep or " ").join((x.capitalize() for x in s.split(sep)))


import re as _re
from collections import ChainMap as _ChainMap

_sentinel_dict = {}


class Template:
    "A string class for supporting $-substitutions."
    delimiter = "$"
    idpattern = "(?a:[_a-z][_a-z0-9]*)"
    braceidpattern = None
    flags = _re.IGNORECASE

    def __init_subclass__(cls):
        super().__init_subclass__()
        if "pattern" in cls.__dict__:
            pattern = cls.pattern
        else:
            delim = _re.escape(cls.delimiter)
            id = cls.idpattern
            bid = cls.braceidpattern or cls.idpattern
            pattern = f"""
            {delim}(?:
              (?P<escaped>{delim})  |   # Escape sequence of two delimiters
              (?P<named>{id})       |   # delimiter and a Python identifier
              {{(?P<braced>{bid})}} |   # delimiter and a braced identifier
              (?P<invalid>)             # Other ill-formed delimiter exprs
            )
            """
        cls.pattern = _re.compile(pattern, (cls.flags | _re.VERBOSE))

    def __init__(self, template):
        self.template = template

    def _invalid(self, mo):
        i = mo.start("invalid")
        lines = self.template[:i].splitlines(keepends=True)
        if not lines:
            colno = 1
            lineno = 1
        else:
            colno = i - len("".join(lines[:(-1)]))
            lineno = len(lines)
        raise ValueError(
            ("Invalid placeholder in string: line %d, col %d" % (lineno, colno))
        )

    def substitute(self, mapping=_sentinel_dict, /, **kws):
        if mapping is _sentinel_dict:
            mapping = kws
        elif kws:
            mapping = _ChainMap(kws, mapping)

        def convert(mo):
            named = mo.group("named") or mo.group("braced")
            if named is not None:
                return str(mapping[named])
            if mo.group("escaped") is not None:
                return self.delimiter
            if mo.group("invalid") is not None:
                self._invalid(mo)
            raise ValueError("Unrecognized named group in pattern", self.pattern)

        return self.pattern.sub(convert, self.template)

    def safe_substitute(self, mapping=_sentinel_dict, /, **kws):
        if mapping is _sentinel_dict:
            mapping = kws
        elif kws:
            mapping = _ChainMap(kws, mapping)

        def convert(mo):
            named = mo.group("named") or mo.group("braced")
            if named is not None:
                try:
                    return str(mapping[named])
                except KeyError:
                    return mo.group()
            if mo.group("escaped") is not None:
                return self.delimiter
            if mo.group("invalid") is not None:
                return mo.group()
            raise ValueError("Unrecognized named group in pattern", self.pattern)

        return self.pattern.sub(convert, self.template)


Template.__init_subclass__()


class Formatter:
    def format(self, format_string, /, *args, **kwargs):
        return self.vformat(format_string, args, kwargs)

    def vformat(self, format_string, args, kwargs):
        used_args = set()
        (result, _) = self._vformat(format_string, args, kwargs, used_args, 2)
        self.check_unused_args(used_args, args, kwargs)
        return result

    def _vformat(
        self, format_string, args, kwargs, used_args, recursion_depth, auto_arg_index=0
    ):
        if recursion_depth < 0:
            raise ValueError("Max string recursion exceeded")
        result = []
        for (literal_text, field_name, format_spec, conversion) in self.parse(
            format_string
        ):
            if literal_text:
                result.append(literal_text)
            if field_name is not None:
                if field_name == "":
                    if auto_arg_index is False:
                        raise ValueError(
                            "cannot switch from manual field specification to automatic field numbering"
                        )
                    field_name = str(auto_arg_index)
                    auto_arg_index += 1
                elif field_name.isdigit():
                    if auto_arg_index:
                        raise ValueError(
                            "cannot switch from manual field specification to automatic field numbering"
                        )
                    auto_arg_index = False
                (obj, arg_used) = self.get_field(field_name, args, kwargs)
                used_args.add(arg_used)
                obj = self.convert_field(obj, conversion)
                (format_spec, auto_arg_index) = self._vformat(
                    format_spec,
                    args,
                    kwargs,
                    used_args,
                    (recursion_depth - 1),
                    auto_arg_index=auto_arg_index,
                )
                result.append(self.format_field(obj, format_spec))
        return ("".join(result), auto_arg_index)

    def get_value(self, key, args, kwargs):
        if isinstance(key, int):
            return args[key]
        else:
            return kwargs[key]

    def check_unused_args(self, used_args, args, kwargs):
        pass

    def format_field(self, value, format_spec):
        return format(value, format_spec)

    def convert_field(self, value, conversion):
        if conversion is None:
            return value
        elif conversion == "s":
            return str(value)
        elif conversion == "r":
            return repr(value)
        elif conversion == "a":
            return ascii(value)
        raise ValueError("Unknown conversion specifier {0!s}".format(conversion))

    def parse(self, format_string):
        return _string.formatter_parser(format_string)

    def get_field(self, field_name, args, kwargs):
        (first, rest) = _string.formatter_field_name_split(field_name)
        obj = self.get_value(first, args, kwargs)
        for (is_attr, i) in rest:
            if is_attr:
                obj = getattr(obj, i)
            else:
                obj = obj[i]
        return (obj, first)
