import sys
import re
import os
from stat import *
import getopt

err = sys.stderr.write
dbg = err
rep = sys.stdout.write


def usage():
    progname = sys.argv[0]
    err((("Usage: " + progname) + " [-c] [-r] [-s file] ... file-or-directory ...\n"))
    err("\n")
    err("-c           : substitute inside comments\n")
    err("-r           : reverse direction for following -s options\n")
    err("-s substfile : add a file of substitutions\n")
    err("\n")
    err("Each non-empty non-comment line in a substitution file must\n")
    err("contain exactly two words: an identifier and its replacement.\n")
    err("Comments start with a # character and end at end of line.\n")
    err("If an identifier is preceded with a *, it is not substituted\n")
    err("inside a comment even when -c is specified.\n")


def main():
    try:
        (opts, args) = getopt.getopt(sys.argv[1:], "crs:")
    except getopt.error as msg:
        err((("Options error: " + str(msg)) + "\n"))
        usage()
        sys.exit(2)
    bad = 0
    if not args:
        usage()
        sys.exit(2)
    for (opt, arg) in opts:
        if opt == "-c":
            setdocomments()
        if opt == "-r":
            setreverse()
        if opt == "-s":
            addsubst(arg)
    for arg in args:
        if os.path.isdir(arg):
            if recursedown(arg):
                bad = 1
        elif os.path.islink(arg):
            err((arg + ": will not process symbolic links\n"))
            bad = 1
        elif fix(arg):
            bad = 1
    sys.exit(bad)


Wanted = "^[a-zA-Z0-9_]+\\.[ch]$"


def wanted(name):
    return re.match(Wanted, name)


def recursedown(dirname):
    dbg(("recursedown(%r)\n" % (dirname,)))
    bad = 0
    try:
        names = os.listdir(dirname)
    except OSError as msg:
        err((((dirname + ": cannot list directory: ") + str(msg)) + "\n"))
        return 1
    names.sort()
    subdirs = []
    for name in names:
        if name in (os.curdir, os.pardir):
            continue
        fullname = os.path.join(dirname, name)
        if os.path.islink(fullname):
            pass
        elif os.path.isdir(fullname):
            subdirs.append(fullname)
        elif wanted(name):
            if fix(fullname):
                bad = 1
    for fullname in subdirs:
        if recursedown(fullname):
            bad = 1
    return bad


def fix(filename):
    if filename == "-":
        f = sys.stdin
        g = sys.stdout
    else:
        try:
            f = open(filename, "r")
        except IOError as msg:
            err((((filename + ": cannot open: ") + str(msg)) + "\n"))
            return 1
        (head, tail) = os.path.split(filename)
        tempname = os.path.join(head, ("@" + tail))
        g = None
    lineno = 0
    initfixline()
    while 1:
        line = f.readline()
        if not line:
            break
        lineno = lineno + 1
        while line[(-2):] == "\\\n":
            nextline = f.readline()
            if not nextline:
                break
            line = line + nextline
            lineno = lineno + 1
        newline = fixline(line)
        if newline != line:
            if g is None:
                try:
                    g = open(tempname, "w")
                except IOError as msg:
                    f.close()
                    err((((tempname + ": cannot create: ") + str(msg)) + "\n"))
                    return 1
                f.seek(0)
                lineno = 0
                initfixline()
                rep((filename + ":\n"))
                continue
            rep((repr(lineno) + "\n"))
            rep(("< " + line))
            rep(("> " + newline))
        if g is not None:
            g.write(newline)
    if filename == "-":
        return 0
    f.close()
    if not g:
        return 0
    g.close()
    try:
        statbuf = os.stat(filename)
        os.chmod(tempname, (statbuf[ST_MODE] & 4095))
    except OSError as msg:
        err((((tempname + ": warning: chmod failed (") + str(msg)) + ")\n"))
    try:
        os.rename(filename, (filename + "~"))
    except OSError as msg:
        err((((filename + ": warning: backup failed (") + str(msg)) + ")\n"))
    try:
        os.rename(tempname, filename)
    except OSError as msg:
        err((((filename + ": rename failed (") + str(msg)) + ")\n"))
        return 1
    return 0


Identifier = "(struct )?[a-zA-Z_][a-zA-Z0-9_]+"
String = '"([^\\n\\\\"]|\\\\.)*"'
Char = "'([^\\n\\\\']|\\\\.)*'"
CommentStart = "/\\*"
CommentEnd = "\\*/"
Hexnumber = "0[xX][0-9a-fA-F]*[uUlL]*"
Octnumber = "0[0-7]*[uUlL]*"
Decnumber = "[1-9][0-9]*[uUlL]*"
Intnumber = (((Hexnumber + "|") + Octnumber) + "|") + Decnumber
Exponent = "[eE][-+]?[0-9]+"
Pointfloat = ("([0-9]+\\.[0-9]*|\\.[0-9]+)(" + Exponent) + ")?"
Expfloat = "[0-9]+" + Exponent
Floatnumber = (Pointfloat + "|") + Expfloat
Number = (Floatnumber + "|") + Intnumber
OutsideComment = (Identifier, Number, String, Char, CommentStart)
OutsideCommentPattern = ("(" + "|".join(OutsideComment)) + ")"
OutsideCommentProgram = re.compile(OutsideCommentPattern)
InsideComment = (Identifier, Number, CommentEnd)
InsideCommentPattern = ("(" + "|".join(InsideComment)) + ")"
InsideCommentProgram = re.compile(InsideCommentPattern)


def initfixline():
    global Program
    Program = OutsideCommentProgram


def fixline(line):
    global Program
    i = 0
    while i < len(line):
        match = Program.search(line, i)
        if match is None:
            break
        i = match.start()
        found = match.group(0)
        if len(found) == 2:
            if found == "/*":
                Program = InsideCommentProgram
            elif found == "*/":
                Program = OutsideCommentProgram
        n = len(found)
        if found in Dict:
            subst = Dict[found]
            if Program is InsideCommentProgram:
                if not Docomments:
                    print("Found in comment:", found)
                    i = i + n
                    continue
                if found in NotInComment:
                    subst = found
            line = (line[:i] + subst) + line[(i + n) :]
            n = len(subst)
        i = i + n
    return line


Docomments = 0


def setdocomments():
    global Docomments
    Docomments = 1


Reverse = 0


def setreverse():
    global Reverse
    Reverse = not Reverse


Dict = {}
NotInComment = {}


def addsubst(substfile):
    try:
        fp = open(substfile, "r")
    except IOError as msg:
        err((((substfile + ": cannot read substfile: ") + str(msg)) + "\n"))
        sys.exit(1)
    with fp:
        lineno = 0
        while 1:
            line = fp.readline()
            if not line:
                break
            lineno = lineno + 1
            try:
                i = line.index("#")
            except ValueError:
                i = -1
            words = line[:i].split()
            if not words:
                continue
            if (len(words) == 3) and (words[0] == "struct"):
                words[:2] = [((words[0] + " ") + words[1])]
            elif len(words) != 2:
                err(
                    (
                        substfile
                        + ("%s:%r: warning: bad line: %r" % (substfile, lineno, line))
                    )
                )
                continue
            if Reverse:
                [value, key] = words
            else:
                [key, value] = words
            if value[0] == "*":
                value = value[1:]
            if key[0] == "*":
                key = key[1:]
                NotInComment[key] = value
            if key in Dict:
                err(
                    (
                        "%s:%r: warning: overriding: %r %r\n"
                        % (substfile, lineno, key, value)
                    )
                )
                err(("%s:%r: warning: previous: %r\n" % (substfile, lineno, Dict[key])))
            Dict[key] = value


if __name__ == "__main__":
    main()
