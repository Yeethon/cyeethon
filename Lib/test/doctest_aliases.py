class TwoNames:
    "f() and g() are two names for the same method"

    def f(self):
        "\n        >>> print(TwoNames().f())\n        f\n        "
        return "f"

    g = f
