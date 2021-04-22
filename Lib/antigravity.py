import webbrowser
import hashlib

webbrowser.open("https://xkcd.com/353/")


def geohash(latitude, longitude, datedow):
    "Compute geohash() using the Munroe algorithm.\n\n    >>> geohash(37.421542, -122.085589, b'2005-05-26-10458.68')\n    37.857713 -122.544543\n\n    "
    h = hashlib.md5(datedow, usedforsecurity=False).hexdigest()
    (p, q) = [("%f" % float.fromhex(("0." + x))) for x in (h[:16], h[16:32])]
    print(("%d%s %d%s" % (latitude, p[1:], longitude, q[1:])))
