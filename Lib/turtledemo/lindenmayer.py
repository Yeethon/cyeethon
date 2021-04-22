"       turtle-example-suite:\n\n        xtx_lindenmayer_indian.py\n\nEach morning women in Tamil Nadu, in southern\nIndia, place designs, created by using rice\nflour and known as kolam on the thresholds of\ntheir homes.\n\nThese can be described by Lindenmayer systems,\nwhich can easily be implemented with turtle\ngraphics and Python.\n\nTwo examples are shown here:\n(1) the snake kolam\n(2) anklets of Krishna\n\nTaken from Marcia Ascher: Mathematics\nElsewhere, An Exploration of Ideas Across\nCultures\n\n"
from turtle import *


def replace(seq, replacementRules, n):
    for i in range(n):
        newseq = ""
        for element in seq:
            newseq = newseq + replacementRules.get(element, element)
        seq = newseq
    return seq


def draw(commands, rules):
    for b in commands:
        try:
            rules[b]()
        except TypeError:
            try:
                draw(rules[b], rules)
            except:
                pass


def main():
    def r():
        right(45)

    def l():
        left(45)

    def f():
        forward(7.5)

    snake_rules = {"-": r, "+": l, "f": f, "b": "f+f+f--f--f+f+f"}
    snake_replacementRules = {"b": "b+f+b--f--b+f+b"}
    snake_start = "b--f--b--f"
    drawing = replace(snake_start, snake_replacementRules, 3)
    reset()
    speed(3)
    tracer(1, 0)
    ht()
    up()
    backward(195)
    down()
    draw(drawing, snake_rules)
    from time import sleep

    sleep(3)

    def A():
        color("red")
        circle(10, 90)

    def B():
        from math import sqrt

        color("black")
        l = 5 / sqrt(2)
        forward(l)
        circle(l, 270)
        forward(l)

    def F():
        color("green")
        forward(10)

    krishna_rules = {"a": A, "b": B, "f": F}
    krishna_replacementRules = {"a": "afbfa", "b": "afbfbfbfa"}
    krishna_start = "fbfbfbfb"
    reset()
    speed(0)
    tracer(3, 0)
    ht()
    left(45)
    drawing = replace(krishna_start, krishna_replacementRules, 3)
    draw(drawing, krishna_rules)
    tracer(1)
    return "Done!"


if __name__ == "__main__":
    msg = main()
    print(msg)
    mainloop()
