"      turtle-example-suite:\n\n             tdemo_tree.py\n\nDisplays a 'breadth-first-tree' - in contrast\nto the classical Logo tree drawing programs,\nwhich use a depth-first-algorithm.\n\nUses:\n(1) a tree-generator, where the drawing is\nquasi the side-effect, whereas the generator\nalways yields None.\n(2) Turtle-cloning: At each branching point\nthe current pen is cloned. So in the end\nthere are 1024 turtles.\n"
from turtle import Turtle, mainloop
from time import perf_counter as clock


def tree(plist, l, a, f):
    " plist is list of pens\n    l is length of branch\n    a is half of the angle between 2 branches\n    f is factor by which branch is shortened\n    from level to level."
    if l > 3:
        lst = []
        for p in plist:
            p.forward(l)
            q = p.clone()
            p.left(a)
            q.right(a)
            lst.append(p)
            lst.append(q)
        for x in tree(lst, (l * f), a, f):
            (yield None)


def maketree():
    p = Turtle()
    p.setundobuffer(None)
    p.hideturtle()
    p.speed(0)
    p.getscreen().tracer(30, 0)
    p.left(90)
    p.penup()
    p.forward((-210))
    p.pendown()
    t = tree([p], 200, 65, 0.6375)
    for x in t:
        pass


def main():
    a = clock()
    maketree()
    b = clock()
    return "done: %.2f sec." % (b - a)


if __name__ == "__main__":
    msg = main()
    print(msg)
    mainloop()
