"finddiv - a grep-like tool that looks for division operators.\n\nUsage: finddiv [-l] file_or_directory ...\n\nFor directory arguments, all files in the directory whose name ends in\n.py are processed, and subdirectories are processed recursively.\n\nThis actually tokenizes the files to avoid false hits in comments or\nstrings literals.\n\nBy default, this prints all lines containing a / or /= operator, in\ngrep -n style.  With the -l option specified, it prints the filename\nof files that contain at least one / or /= operator.\n"
import os
import sys
import getopt
import tokenize


def main():
    try:
        (opts, args) = getopt.getopt(sys.argv[1:], "lh")
    except getopt.error as msg:
        usage(msg)
        return 2
    if not args:
        usage("at least one file argument is required")
        return 2
    listnames = 0
    for (o, a) in opts:
        if o == "-h":
            print(__doc__)
            return
        if o == "-l":
            listnames = 1
    exit = None
    for filename in args:
        x = process(filename, listnames)
        exit = exit or x
    return exit


def usage(msg):
    sys.stderr.write(("%s: %s\n" % (sys.argv[0], msg)))
    sys.stderr.write(("Usage: %s [-l] file ...\n" % sys.argv[0]))
    sys.stderr.write(("Try `%s -h' for more information.\n" % sys.argv[0]))


def process(filename, listnames):
    if os.path.isdir(filename):
        return processdir(filename, listnames)
    try:
        fp = open(filename)
    except IOError as msg:
        sys.stderr.write(("Can't open: %s\n" % msg))
        return 1
    with fp:
        g = tokenize.generate_tokens(fp.readline)
        lastrow = None
        for (type, token, (row, col), end, line) in g:
            if token in ("/", "/="):
                if listnames:
                    print(filename)
                    break
                if row != lastrow:
                    lastrow = row
                    print(("%s:%d:%s" % (filename, row, line)), end=" ")


def processdir(dir, listnames):
    try:
        names = os.listdir(dir)
    except OSError as msg:
        sys.stderr.write(("Can't list directory: %s\n" % dir))
        return 1
    files = []
    for name in names:
        fn = os.path.join(dir, name)
        if os.path.normcase(fn).endswith(".py") or os.path.isdir(fn):
            files.append(fn)
    files.sort(key=os.path.normcase)
    exit = None
    for fn in files:
        x = process(fn, listnames)
        exit = exit or x
    return exit


if __name__ == "__main__":
    sys.exit(main())
