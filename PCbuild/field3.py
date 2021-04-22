import sys

(major, minor, micro, level, serial) = sys.version_info
levelnum = {"alpha": 10, "beta": 11, "candidate": 12, "final": 15}[level]
string = sys.version.split()[0]
print((" * For %s," % string))
print((" * PY_MICRO_VERSION = %d" % micro))
print((" * PY_RELEASE_LEVEL = %r = %s" % (level, hex(levelnum))))
print((" * PY_RELEASE_SERIAL = %d" % serial))
print(" *")
field3 = ((micro * 1000) + (levelnum * 10)) + serial
print((" * and %d*1000 + %d*10 + %d = %d" % (micro, levelnum, serial, field3)))
print(" */")
print("#define FIELD3", field3)
