f"""
    struct {ANON_IDENTIFIER};
    struct {{ ... }}
    struct {IDENTIFIER} {{ ... }}

    union {ANON_IDENTIFIER};
    union {{ ... }}
    union {IDENTIFIER} {{ ... }}

    enum {ANON_IDENTIFIER};
    enum {{ ... }}
    enum {IDENTIFIER} {{ ... }}

    typedef {VARTYPE} {IDENTIFIER};
    typedef {IDENTIFIER};
    typedef {IDENTIFIER};
    typedef {IDENTIFIER};
"""


def parse(srclines):
    if isinstance(srclines, str):
        raise NotImplementedError


'\n        # for loop\n        (?:\n            \\s* \x08 for\n            \\s* [(]\n            (\n                [^;]* ;\n                [^;]* ;\n                .*?\n             )  # <header>\n            [)]\n            \\s*\n            (?:\n                (?:\n                    (\n                        {_ind(SIMPLE_STMT, 6)}\n                     )  # <stmt>\n                    ;\n                 )\n                |\n                ( {{ )  # <open>\n             )\n         )\n        |\n\n\n\n            (\n                (?:\n                    (?:\n                        (?:\n                            {_ind(SIMPLE_STMT, 6)}\n                         )?\n                        return \x08 \\s*\n                        {_ind(INITIALIZER, 5)}\n                     )\n                    |\n                    (?:\n                        (?:\n                            {IDENTIFIER} \\s*\n                            (?: . | -> ) \\s*\n                         )*\n                        {IDENTIFIER}\n                        \\s* = \\s*\n                        {_ind(INITIALIZER, 5)}\n                     )\n                    |\n                    (?:\n                        {_ind(SIMPLE_STMT, 5)}\n                     )\n                 )\n                |\n                # cast compound literal\n                (?:\n                    (?:\n                        [^\'"{{}};]*\n                        {_ind(STRING_LITERAL, 5)}\n                     )*\n                    [^\'"{{}};]*?\n                    [^\'"{{}};=]\n                    =\n                    \\s* [(] [^)]* [)]\n                    \\s* {{ [^;]* }}\n                 )\n             )  # <stmt>\n\n\n\n        # compound statement\n        (?:\n            (\n                (?:\n\n                    # "for" statements are handled separately above.\n                    (?: (?: else \\s+ )? if | switch | while ) \\s*\n                    {_ind(COMPOUND_HEAD, 5)}\n                 )\n                |\n                (?: else | do )\n                # We do not worry about compound statements for labels,\n                # "case", or "default".\n             )?  # <header>\n            \\s*\n            ( {{ )  # <open>\n         )\n\n\n\n            (\n                (?:\n                    [^\'"{{}};]*\n                    {_ind(STRING_LITERAL, 5)}\n                 )*\n                [^\'"{{}};]*\n                # Presumably we will not see "== {{".\n                [^\\s=\'"{{}};]\n             )?  # <header>\n\n\n\n            (\n                \x08\n                (?:\n                    # We don\'t worry about labels with a compound statement.\n                    (?:\n                        switch \\s* [(] [^{{]* [)]\n                     )\n                    |\n                    (?:\n                        case \x08 \\s* [^:]+ [:]\n                     )\n                    |\n                    (?:\n                        default \\s* [:]\n                     )\n                    |\n                    (?:\n                        do\n                     )\n                    |\n                    (?:\n                        while \\s* [(] [^{{]* [)]\n                     )\n                    |\n                    #(?:\n                    #    for \\s* [(] [^{{]* [)]\n                    # )\n                    #|\n                    (?:\n                        if \\s* [(]\n                        (?: [^{{]* [^)] \\s* {{ )* [^{{]*\n                        [)]\n                     )\n                    |\n                    (?:\n                        else\n                        (?:\n                            \\s*\n                            if \\s* [(]\n                            (?: [^{{]* [^)] \\s* {{ )* [^{{]*\n                            [)]\n                         )?\n                     )\n                 )\n             )?  # <header>\n'
