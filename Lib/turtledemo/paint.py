"       turtle-example-suite:\n\n            tdemo_paint.py\n\nA simple  event-driven paint program\n\n- left mouse button moves turtle\n- middle mouse button changes color\n- right mouse button toggles between pen up\n(no line drawn when the turtle moves) and\npen down (line is drawn). If pen up follows\nat least two pen-down moves, the polygon that\nincludes the starting point is filled.\n -------------------------------------------\n Play around by clicking into the canvas\n using all three mouse buttons.\n -------------------------------------------\n          To exit press STOP button\n -------------------------------------------\n"
from turtle import *


def switchupdown(x=0, y=0):
    if pen()["pendown"]:
        end_fill()
        up()
    else:
        down()
        begin_fill()


def changecolor(x=0, y=0):
    global colors
    colors = colors[1:] + colors[:1]
    color(colors[0])


def main():
    global colors
    shape("circle")
    resizemode("user")
    shapesize(0.5)
    width(3)
    colors = ["red", "green", "blue", "yellow"]
    color(colors[0])
    switchupdown()
    onscreenclick(goto, 1)
    onscreenclick(changecolor, 2)
    onscreenclick(switchupdown, 3)
    return "EVENTLOOP"


if __name__ == "__main__":
    msg = main()
    print(msg)
    mainloop()
