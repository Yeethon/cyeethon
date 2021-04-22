from pygments.lexer import RegexLexer, bygroups, include
from pygments.token import Comment, Generic, Keyword, Name, Operator, Punctuation, Text
from sphinx.highlighting import lexers


class PEGLexer(RegexLexer):
    "Pygments Lexer for PEG grammar (.gram) files\n\n    This lexer strips the following elements from the grammar:\n\n        - Meta-tags\n        - Variable assignments\n        - Actions\n        - Lookaheads\n        - Rule types\n        - Rule options\n        - Rules named `invalid_*` or `incorrect_*`\n    "
    name = "PEG"
    aliases = ["peg"]
    filenames = ["*.gram"]
    _name = "([^\\W\\d]\\w*)"
    _text_ws = "(\\s*)"
    tokens = {
        "ws": [("\\n", Text), ("\\s+", Text), ("#.*$", Comment.Singleline)],
        "lookaheads": [
            ("(&&)(?=\\w+\\s?)", bygroups(None)),
            ("(&&)(?='.+'\\s?)", bygroups(None)),
            ('(&&)(?=".+"\\s?)', bygroups(None)),
            ("(&&)(?=\\(.+\\)\\s?)", bygroups(None)),
            ("(?<=\\|\\s)(&\\w+\\s?)", bygroups(None)),
            ("(?<=\\|\\s)(&'.+'\\s?)", bygroups(None)),
            ('(?<=\\|\\s)(&".+"\\s?)', bygroups(None)),
            ("(?<=\\|\\s)(&\\(.+\\)\\s?)", bygroups(None)),
        ],
        "metas": [
            ("(@\\w+ '''(.|\\n)+?''')", bygroups(None)),
            ("^(@.*)$", bygroups(None)),
        ],
        "actions": [("{(.|\\n)+?}", bygroups(None))],
        "strings": [
            ("'\\w+?'", Keyword),
            ('"\\w+?"', Keyword),
            ("'\\W+?'", Text),
            ('"\\W+?"', Text),
        ],
        "variables": [
            (((_name + _text_ws) + "(=)"), bygroups(None, None, None)),
            (
                ((((_name + _text_ws) + "(\\[[\\w\\d_\\*]+?\\])") + _text_ws) + "(=)"),
                bygroups(None, None, None, None, None),
            ),
        ],
        "invalids": [
            ("^(\\s+\\|\\s+invalid_\\w+\\s*\\n)", bygroups(None)),
            ("^(\\s+\\|\\s+incorrect_\\w+\\s*\\n)", bygroups(None)),
            ("^(#.*invalid syntax.*(?:.|\\n)*)", bygroups(None)),
        ],
        "root": [
            include("invalids"),
            include("ws"),
            include("lookaheads"),
            include("metas"),
            include("actions"),
            include("strings"),
            include("variables"),
            ("\\b(?!(NULL|EXTRA))([A-Z_]+)\\b\\s*(?!\\()", Text),
            (
                (
                    (
                        (((("^\\s*" + _name) + "\\s*") + "(\\[.*\\])?") + "\\s*")
                        + "(\\(.+\\))?"
                    )
                    + "\\s*(:)"
                ),
                bygroups(Name.Function, None, None, Punctuation),
            ),
            (_name, Name.Function),
            ("[\\||\\.|\\+|\\*|\\?]", Operator),
            ("{|}|\\(|\\)|\\[|\\]", Punctuation),
            (".", Text),
        ],
    }


def setup(app):
    lexers["peg"] = PEGLexer()
    return {"version": "1.0", "parallel_read_safe": True}
