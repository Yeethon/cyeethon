import sys

sys.setrecursionlimit((1 << 30))
f = lambda f: f(f)
if __name__ == "__main__":
    f(f)
