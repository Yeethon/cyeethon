'ndiff [-q] file1 file2\n    or\nndiff (-r1 | -r2) < ndiff_output > file1_or_file2\n\nPrint a human-friendly file difference report to stdout.  Both inter-\nand intra-line differences are noted.  In the second form, recreate file1\n(-r1) or file2 (-r2) on stdout, from an ndiff report on stdin.\n\nIn the first form, if -q ("quiet") is not specified, the first two lines\nof output are\n\n-: file1\n+: file2\n\nEach remaining line begins with a two-letter code:\n\n    "- "    line unique to file1\n    "+ "    line unique to file2\n    "  "    line common to both files\n    "? "    line not present in either input file\n\nLines beginning with "? " attempt to guide the eye to intraline\ndifferences, and were not present in either input file.  These lines can be\nconfusing if the source files contain tab characters.\n\nThe first file can be recovered by retaining only lines that begin with\n"  " or "- ", and deleting those 2-character prefixes; use ndiff with -r1.\n\nThe second file can be recovered similarly, but by retaining only "  " and\n"+ " lines; use ndiff with -r2; or, on Unix, the second file can be\nrecovered by piping the output through\n\n    sed -n \'/^[+ ] /s/^..//p\'\n'
__version__ = (1, 7, 0)
import difflib, sys


def fail(msg):
    out = sys.stderr.write
    out((msg + "\n\n"))
    out(__doc__)
    return 0


def fopen(fname):
    try:
        return open(fname)
    except IOError as detail:
        return fail(((("couldn't open " + fname) + ": ") + str(detail)))


def fcompare(f1name, f2name):
    f1 = fopen(f1name)
    f2 = fopen(f2name)
    if (not f1) or (not f2):
        return 0
    a = f1.readlines()
    f1.close()
    b = f2.readlines()
    f2.close()
    for line in difflib.ndiff(a, b):
        print(line, end=" ")
    return 1


def main(args):
    import getopt

    try:
        (opts, args) = getopt.getopt(args, "qr:")
    except getopt.error as detail:
        return fail(str(detail))
    noisy = 1
    qseen = rseen = 0
    for (opt, val) in opts:
        if opt == "-q":
            qseen = 1
            noisy = 0
        elif opt == "-r":
            rseen = 1
            whichfile = val
    if qseen and rseen:
        return fail("can't specify both -q and -r")
    if rseen:
        if args:
            return fail("no args allowed with -r option")
        if whichfile in ("1", "2"):
            restore(whichfile)
            return 1
        return fail("-r value must be 1 or 2")
    if len(args) != 2:
        return fail("need 2 filename args")
    (f1name, f2name) = args
    if noisy:
        print("-:", f1name)
        print("+:", f2name)
    return fcompare(f1name, f2name)


def restore(which):
    restored = difflib.restore(sys.stdin.readlines(), which)
    sys.stdout.writelines(restored)


if __name__ == "__main__":
    args = sys.argv[1:]
    if "-profile" in args:
        import profile, pstats

        args.remove("-profile")
        statf = "ndiff.pro"
        profile.run("main(args)", statf)
        stats = pstats.Stats(statf)
        stats.strip_dirs().sort_stats("time").print_stats()
    else:
        main(args)
