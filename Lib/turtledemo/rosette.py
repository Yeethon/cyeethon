"      turtle-example-suite:\n\n          tdemo_wikipedia3.py\n\nThis example is\ninspired by the Wikipedia article on turtle\ngraphics. (See example wikipedia1 for URLs)\n\nFirst we create (ne-1) (i.e. 35 in this\nexample) copies of our first turtle p.\nThen we let them perform their steps in\nparallel.\n\nFollowed by a complete undo().\n"
from turtle import Screen, Turtle, mainloop
from time import perf_counter as clock, sleep


def mn_eck(p, ne, sz):
    turtlelist = [p]
    for i in range(1, ne):
        q = p.clone()
        q.rt((360.0 / ne))
        turtlelist.append(q)
        p = q
    for i in range(ne):
        c = abs(((ne / 2.0) - i)) / (ne * 0.7)
        for t in turtlelist:
            t.rt((360.0 / ne))
            t.pencolor((1 - c), 0, c)
            t.fd(sz)


def main():
    s = Screen()
    s.bgcolor("black")
    p = Turtle()
    p.speed(0)
    p.hideturtle()
    p.pencolor("red")
    p.pensize(3)
    s.tracer(36, 0)
    at = clock()
    mn_eck(p, 36, 19)
    et = clock()
    z1 = et - at
    sleep(1)
    at = clock()
    while any((t.undobufferentries() for t in s.turtles())):
        for t in s.turtles():
            t.undo()
    et = clock()
    return "runtime: %.3f sec" % ((z1 + et) - at)


if __name__ == "__main__":
    msg = main()
    print(msg)
    mainloop()
