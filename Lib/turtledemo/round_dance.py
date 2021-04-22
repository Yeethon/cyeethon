"      turtle-example-suite:\n\n         tdemo_round_dance.py\n\n(Needs version 1.1 of the turtle module that\ncomes with Python 3.1)\n\nDancing turtles have a compound shape\nconsisting of a series of triangles of\ndecreasing size.\n\nTurtles march along a circle while rotating\npairwise in opposite direction, with one\nexception. Does that breaking of symmetry\nenhance the attractiveness of the example?\n\nPress any key to stop the animation.\n\nTechnically: demonstrates use of compound\nshapes, transformation of shapes as well as\ncloning turtles. The animation is\ncontrolled through update().\n"
from turtle import *


def stop():
    global running
    running = False


def main():
    global running
    clearscreen()
    bgcolor("gray10")
    tracer(False)
    shape("triangle")
    f = 0.793402
    phi = 9.064678
    s = 5
    c = 1
    sh = Shape("compound")
    for i in range(10):
        shapesize(s)
        p = get_shapepoly()
        s *= f
        c *= f
        tilt((-phi))
        sh.addcomponent(p, (c, 0.25, (1 - c)), "black")
    register_shape("multitri", sh)
    shapesize(1)
    shape("multitri")
    pu()
    setpos(0, (-200))
    dancers = []
    for i in range(180):
        fd(7)
        tilt((-4))
        lt(2)
        update()
        if (i % 12) == 0:
            dancers.append(clone())
    home()
    running = True
    onkeypress(stop)
    listen()
    cs = 1
    while running:
        ta = -4
        for dancer in dancers:
            dancer.fd(7)
            dancer.lt(2)
            dancer.tilt(ta)
            ta = (-4) if (ta > 0) else 2
        if cs < 180:
            right(4)
            shapesize(cs)
            cs *= 1.005
        update()
    return "DONE!"


if __name__ == "__main__":
    print(main())
    mainloop()
