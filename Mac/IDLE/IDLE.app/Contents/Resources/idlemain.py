"\nBootstrap script for IDLE as an application bundle.\n"
import sys, os

os.chdir(os.path.expanduser("~/Documents"))
pyex = os.environ["PYTHONEXECUTABLE"]
sys.executable = os.path.join(sys.prefix, "bin", ("python%d.%d" % sys.version_info[:2]))
p = pyex.partition(".app")
if p[2].startswith("/Contents/MacOS/Python"):
    sys.path = [
        value
        for value in sys.path
        if (value.partition(".app") != (p[0], p[1], "/Contents/Resources"))
    ]
del os.environ["PYTHONEXECUTABLE"]
for (idx, value) in enumerate(sys.argv):
    if value.startswith("-psn_"):
        del sys.argv[idx]
        break
from idlelib.pyshell import main

if __name__ == "__main__":
    main()
