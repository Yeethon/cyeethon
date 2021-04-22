"      turtle-example-suite:\n\n        tdemo_bytedesign.py\n\nAn example adapted from the example-suite\nof PythonCard's turtle graphics.\n\nIt's based on an article in BYTE magazine\nProblem Solving with Logo: Using Turtle\nGraphics to Redraw a Design\nNovember 1982, p. 118 - 134\n\n-------------------------------------------\n\nDue to the statement\n\nt.delay(0)\n\nin line 152, which sets the animation delay\nto 0, this animation runs in \"line per line\"\nmode as fast as possible.\n"
from turtle import Turtle, mainloop
from time import perf_counter as clock


class Designer(Turtle):
    def design(self, homePos, scale):
        self.up()
        for i in range(5):
            self.forward((64.65 * scale))
            self.down()
            self.wheel(self.position(), scale)
            self.up()
            self.backward((64.65 * scale))
            self.right(72)
        self.up()
        self.goto(homePos)
        self.right(36)
        self.forward((24.5 * scale))
        self.right(198)
        self.down()
        self.centerpiece((46 * scale), 143.4, scale)
        self.getscreen().tracer(True)

    def wheel(self, initpos, scale):
        self.right(54)
        for i in range(4):
            self.pentpiece(initpos, scale)
        self.down()
        self.left(36)
        for i in range(5):
            self.tripiece(initpos, scale)
        self.left(36)
        for i in range(5):
            self.down()
            self.right(72)
            self.forward((28 * scale))
            self.up()
            self.backward((28 * scale))
        self.left(54)
        self.getscreen().update()

    def tripiece(self, initpos, scale):
        oldh = self.heading()
        self.down()
        self.backward((2.5 * scale))
        self.tripolyr((31.5 * scale), scale)
        self.up()
        self.goto(initpos)
        self.setheading(oldh)
        self.down()
        self.backward((2.5 * scale))
        self.tripolyl((31.5 * scale), scale)
        self.up()
        self.goto(initpos)
        self.setheading(oldh)
        self.left(72)
        self.getscreen().update()

    def pentpiece(self, initpos, scale):
        oldh = self.heading()
        self.up()
        self.forward((29 * scale))
        self.down()
        for i in range(5):
            self.forward((18 * scale))
            self.right(72)
        self.pentr((18 * scale), 75, scale)
        self.up()
        self.goto(initpos)
        self.setheading(oldh)
        self.forward((29 * scale))
        self.down()
        for i in range(5):
            self.forward((18 * scale))
            self.right(72)
        self.pentl((18 * scale), 75, scale)
        self.up()
        self.goto(initpos)
        self.setheading(oldh)
        self.left(72)
        self.getscreen().update()

    def pentl(self, side, ang, scale):
        if side < (2 * scale):
            return
        self.forward(side)
        self.left(ang)
        self.pentl((side - (0.38 * scale)), ang, scale)

    def pentr(self, side, ang, scale):
        if side < (2 * scale):
            return
        self.forward(side)
        self.right(ang)
        self.pentr((side - (0.38 * scale)), ang, scale)

    def tripolyr(self, side, scale):
        if side < (4 * scale):
            return
        self.forward(side)
        self.right(111)
        self.forward((side / 1.78))
        self.right(111)
        self.forward((side / 1.3))
        self.right(146)
        self.tripolyr((side * 0.75), scale)

    def tripolyl(self, side, scale):
        if side < (4 * scale):
            return
        self.forward(side)
        self.left(111)
        self.forward((side / 1.78))
        self.left(111)
        self.forward((side / 1.3))
        self.left(146)
        self.tripolyl((side * 0.75), scale)

    def centerpiece(self, s, a, scale):
        self.forward(s)
        self.left(a)
        if s < (7.5 * scale):
            return
        self.centerpiece((s - (1.2 * scale)), a, scale)


def main():
    t = Designer()
    t.speed(0)
    t.hideturtle()
    t.getscreen().delay(0)
    t.getscreen().tracer(0)
    at = clock()
    t.design(t.position(), 2)
    et = clock()
    return "runtime: %.2f sec." % (et - at)


if __name__ == "__main__":
    msg = main()
    print(msg)
    mainloop()
