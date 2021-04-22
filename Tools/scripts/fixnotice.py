"(Ostensibly) fix copyright notices in files.\n\nActually, this script will simply replace a block of text in a file from one\nstring to another.  It will only do this once though, i.e. not globally\nthroughout the file.  It writes a backup file and then does an os.rename()\ndance for atomicity.\n\nUsage: fixnotices.py [options] [filenames]\nOptions:\n    -h / --help\n        Print this message and exit\n\n    --oldnotice=file\n        Use the notice in the file as the old (to be replaced) string, instead\n        of the hard coded value in the script.\n\n    --newnotice=file\n        Use the notice in the file as the new (replacement) string, instead of\n        the hard coded value in the script.\n\n    --dry-run\n        Don't actually make the changes, but print out the list of files that\n        would change.  When used with -v, a status will be printed for every\n        file.\n\n    -v / --verbose\n        Print a message for every file looked at, indicating whether the file\n        is changed or not.\n"
OLD_NOTICE = '/***********************************************************\nCopyright (c) 2000, BeOpen.com.\nCopyright (c) 1995-2000, Corporation for National Research Initiatives.\nCopyright (c) 1990-1995, Stichting Mathematisch Centrum.\nAll rights reserved.\n\nSee the file "Misc/COPYRIGHT" for information on usage and\nredistribution of this file, and for a DISCLAIMER OF ALL WARRANTIES.\n******************************************************************/\n'
import os
import sys
import getopt

NEW_NOTICE = ""
DRYRUN = 0
VERBOSE = 0


def usage(code, msg=""):
    print((__doc__ % globals()))
    if msg:
        print(msg)
    sys.exit(code)


def main():
    global DRYRUN, OLD_NOTICE, NEW_NOTICE, VERBOSE
    try:
        (opts, args) = getopt.getopt(
            sys.argv[1:],
            "hv",
            ["help", "oldnotice=", "newnotice=", "dry-run", "verbose"],
        )
    except getopt.error as msg:
        usage(1, msg)
    for (opt, arg) in opts:
        if opt in ("-h", "--help"):
            usage(0)
        elif opt in ("-v", "--verbose"):
            VERBOSE = 1
        elif opt == "--dry-run":
            DRYRUN = 1
        elif opt == "--oldnotice":
            with open(arg) as fp:
                OLD_NOTICE = fp.read()
        elif opt == "--newnotice":
            with open(arg) as fp:
                NEW_NOTICE = fp.read()
    for arg in args:
        process(arg)


def process(file):
    with open(file) as f:
        data = f.read()
    i = data.find(OLD_NOTICE)
    if i < 0:
        if VERBOSE:
            print("no change:", file)
        return
    elif DRYRUN or VERBOSE:
        print("   change:", file)
    if DRYRUN:
        return
    data = (data[:i] + NEW_NOTICE) + data[(i + len(OLD_NOTICE)) :]
    new = file + ".new"
    backup = file + ".bak"
    with open(new, "w") as f:
        f.write(data)
    os.rename(file, backup)
    os.rename(new, file)


if __name__ == "__main__":
    main()
