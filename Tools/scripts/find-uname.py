"\nFor each argument on the command line, look for it in the set of all Unicode\nnames.  Arguments are treated as case-insensitive regular expressions, e.g.:\n\n    % find-uname 'small letter a$' 'horizontal line'\n    *** small letter a$ matches ***\n    LATIN SMALL LETTER A (97)\n    COMBINING LATIN SMALL LETTER A (867)\n    CYRILLIC SMALL LETTER A (1072)\n    PARENTHESIZED LATIN SMALL LETTER A (9372)\n    CIRCLED LATIN SMALL LETTER A (9424)\n    FULLWIDTH LATIN SMALL LETTER A (65345)\n    *** horizontal line matches ***\n    HORIZONTAL LINE EXTENSION (9135)\n"
import unicodedata
import sys
import re


def main(args):
    unicode_names = []
    for ix in range((sys.maxunicode + 1)):
        try:
            unicode_names.append((ix, unicodedata.name(chr(ix))))
        except ValueError:
            pass
    for arg in args:
        pat = re.compile(arg, re.I)
        matches = [(y, x) for (x, y) in unicode_names if (pat.search(y) is not None)]
        if matches:
            print("***", arg, "matches", "***")
            for match in matches:
                print(("%s (%d)" % match))


if __name__ == "__main__":
    main(sys.argv[1:])
