import sys

try:
    import os
except:
    print(
        'Could not import the standard "os" module.\n  Please check your PYTHONPATH environment variable.'
    )
    sys.exit(1)
try:
    import symbol
except:
    print(
        'Could not import the standard "symbol" module.  If this is\n  a PC, you should add the dos_8x3 directory to your PYTHONPATH.'
    )
    sys.exit(1)
for dir in sys.path:
    file = os.path.join(dir, "os.py")
    if os.path.isfile(file):
        test = os.path.join(dir, "test")
        if os.path.isdir(test):
            sys.path = sys.path + [test]
import libregrtest

libregrtest.main()
