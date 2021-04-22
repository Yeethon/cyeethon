' Utility for parsing HTML entity definitions available from:\n\n      http://www.w3.org/ as e.g.\n      http://www.w3.org/TR/REC-html40/HTMLlat1.ent\n\n    Input is read from stdin, output is written to stdout in form of a\n    Python snippet defining a dictionary "entitydefs" mapping literal\n    entity name to character or numeric entity.\n\n    Marc-Andre Lemburg, mal@lemburg.com, 1999.\n    Use as you like. NO WARRANTIES.\n\n'
import re, sys

entityRE = re.compile('<!ENTITY +(\\w+) +CDATA +"([^"]+)" +-- +((?:.|\\n)+?) *-->')


def parse(text, pos=0, endpos=None):
    pos = 0
    if endpos is None:
        endpos = len(text)
    d = {}
    while 1:
        m = entityRE.search(text, pos, endpos)
        if not m:
            break
        (name, charcode, comment) = m.groups()
        d[name] = (charcode, comment)
        pos = m.end()
    return d


def writefile(f, defs):
    f.write("entitydefs = {\n")
    items = sorted(defs.items())
    for (name, (charcode, comment)) in items:
        if charcode[:2] == "&#":
            code = int(charcode[2:(-1)])
            if code < 256:
                charcode = "'\\%o'" % code
            else:
                charcode = repr(charcode)
        else:
            charcode = repr(charcode)
        comment = " ".join(comment.split())
        f.write(("    '%s':\t%s,  \t# %s\n" % (name, charcode, comment)))
    f.write("\n}\n")


if __name__ == "__main__":
    if len(sys.argv) > 1:
        with open(sys.argv[1]) as infile:
            text = infile.read()
    else:
        text = sys.stdin.read()
    defs = parse(text)
    if len(sys.argv) > 2:
        with open(sys.argv[2], "w") as outfile:
            writefile(outfile, defs)
    else:
        writefile(sys.stdout, defs)
