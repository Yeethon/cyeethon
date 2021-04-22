import sys
import patchcheck


def main(argv=sys.argv):
    patchcheck.normalize_docs_whitespace(argv[1:])


if __name__ == "__main__":
    sys.exit(main())
