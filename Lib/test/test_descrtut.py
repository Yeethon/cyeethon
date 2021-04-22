from test.support import sortdict
import pprint


class defaultdict(dict):
    def __init__(self, default=None):
        dict.__init__(self)
        self.default = default

    def __getitem__(self, key):
        try:
            return dict.__getitem__(self, key)
        except KeyError:
            return self.default

    def get(self, key, *args):
        if not args:
            args = (self.default,)
        return dict.get(self, key, *args)

    def merge(self, other):
        for key in other:
            if key not in self:
                self[key] = other[key]


test_1 = "\n\nHere's the new type at work:\n\n    >>> print(defaultdict)              # show our type\n    <class 'test.test_descrtut.defaultdict'>\n    >>> print(type(defaultdict))        # its metatype\n    <class 'type'>\n    >>> a = defaultdict(default=0.0)    # create an instance\n    >>> print(a)                        # show the instance\n    {}\n    >>> print(type(a))                  # show its type\n    <class 'test.test_descrtut.defaultdict'>\n    >>> print(a.__class__)              # show its class\n    <class 'test.test_descrtut.defaultdict'>\n    >>> print(type(a) is a.__class__)   # its type is its class\n    True\n    >>> a[1] = 3.25                     # modify the instance\n    >>> print(a)                        # show the new value\n    {1: 3.25}\n    >>> print(a[1])                     # show the new item\n    3.25\n    >>> print(a[0])                     # a non-existent item\n    0.0\n    >>> a.merge({1:100, 2:200})         # use a dict method\n    >>> print(sortdict(a))              # show the result\n    {1: 3.25, 2: 200}\n    >>>\n\nWe can also use the new type in contexts where classic only allows \"real\"\ndictionaries, such as the locals/globals dictionaries for the exec\nstatement or the built-in function eval():\n\n    >>> print(sorted(a.keys()))\n    [1, 2]\n    >>> a['print'] = print              # need the print function here\n    >>> exec(\"x = 3; print(x)\", a)\n    3\n    >>> print(sorted(a.keys(), key=lambda x: (str(type(x)), x)))\n    [1, 2, '__builtins__', 'print', 'x']\n    >>> print(a['x'])\n    3\n    >>>\n\nNow I'll show that defaultdict instances have dynamic instance variables,\njust like classic classes:\n\n    >>> a.default = -1\n    >>> print(a[\"noway\"])\n    -1\n    >>> a.default = -1000\n    >>> print(a[\"noway\"])\n    -1000\n    >>> 'default' in dir(a)\n    True\n    >>> a.x1 = 100\n    >>> a.x2 = 200\n    >>> print(a.x1)\n    100\n    >>> d = dir(a)\n    >>> 'default' in d and 'x1' in d and 'x2' in d\n    True\n    >>> print(sortdict(a.__dict__))\n    {'default': -1000, 'x1': 100, 'x2': 200}\n    >>>\n"


class defaultdict2(dict):
    __slots__ = ["default"]

    def __init__(self, default=None):
        dict.__init__(self)
        self.default = default

    def __getitem__(self, key):
        try:
            return dict.__getitem__(self, key)
        except KeyError:
            return self.default

    def get(self, key, *args):
        if not args:
            args = (self.default,)
        return dict.get(self, key, *args)

    def merge(self, other):
        for key in other:
            if key not in self:
                self[key] = other[key]


test_2 = "\n\nThe __slots__ declaration takes a list of instance variables, and reserves\nspace for exactly these in the instance. When __slots__ is used, other\ninstance variables cannot be assigned to:\n\n    >>> a = defaultdict2(default=0.0)\n    >>> a[1]\n    0.0\n    >>> a.default = -1\n    >>> a[1]\n    -1\n    >>> a.x1 = 1\n    Traceback (most recent call last):\n      File \"<stdin>\", line 1, in ?\n    AttributeError: 'defaultdict2' object has no attribute 'x1'\n    >>>\n\n"
test_3 = "\n\nIntrospecting instances of built-in types\n\nFor instance of built-in types, x.__class__ is now the same as type(x):\n\n    >>> type([])\n    <class 'list'>\n    >>> [].__class__\n    <class 'list'>\n    >>> list\n    <class 'list'>\n    >>> isinstance([], list)\n    True\n    >>> isinstance([], dict)\n    False\n    >>> isinstance([], object)\n    True\n    >>>\n\nYou can get the information from the list type:\n\n    >>> pprint.pprint(dir(list))    # like list.__dict__.keys(), but sorted\n    ['__add__',\n     '__class__',\n     '__class_getitem__',\n     '__contains__',\n     '__delattr__',\n     '__delitem__',\n     '__dir__',\n     '__doc__',\n     '__eq__',\n     '__format__',\n     '__ge__',\n     '__getattribute__',\n     '__getitem__',\n     '__gt__',\n     '__hash__',\n     '__iadd__',\n     '__imul__',\n     '__init__',\n     '__init_subclass__',\n     '__iter__',\n     '__le__',\n     '__len__',\n     '__lt__',\n     '__mul__',\n     '__ne__',\n     '__new__',\n     '__reduce__',\n     '__reduce_ex__',\n     '__repr__',\n     '__reversed__',\n     '__rmul__',\n     '__setattr__',\n     '__setitem__',\n     '__sizeof__',\n     '__str__',\n     '__subclasshook__',\n     'append',\n     'clear',\n     'copy',\n     'count',\n     'extend',\n     'index',\n     'insert',\n     'pop',\n     'remove',\n     'reverse',\n     'sort']\n\nThe new introspection API gives more information than the old one:  in\naddition to the regular methods, it also shows the methods that are\nnormally invoked through special notations, e.g. __iadd__ (+=), __len__\n(len), __ne__ (!=). You can invoke any method from this list directly:\n\n    >>> a = ['tic', 'tac']\n    >>> list.__len__(a)          # same as len(a)\n    2\n    >>> a.__len__()              # ditto\n    2\n    >>> list.append(a, 'toe')    # same as a.append('toe')\n    >>> a\n    ['tic', 'tac', 'toe']\n    >>>\n\nThis is just like it is for user-defined classes.\n"
test_4 = "\n\nStatic methods and class methods\n\nThe new introspection API makes it possible to add static methods and class\nmethods. Static methods are easy to describe: they behave pretty much like\nstatic methods in C++ or Java. Here's an example:\n\n    >>> class C:\n    ...\n    ...     @staticmethod\n    ...     def foo(x, y):\n    ...         print(\"staticmethod\", x, y)\n\n    >>> C.foo(1, 2)\n    staticmethod 1 2\n    >>> c = C()\n    >>> c.foo(1, 2)\n    staticmethod 1 2\n\nClass methods use a similar pattern to declare methods that receive an\nimplicit first argument that is the *class* for which they are invoked.\n\n    >>> class C:\n    ...     @classmethod\n    ...     def foo(cls, y):\n    ...         print(\"classmethod\", cls, y)\n\n    >>> C.foo(1)\n    classmethod <class 'test.test_descrtut.C'> 1\n    >>> c = C()\n    >>> c.foo(1)\n    classmethod <class 'test.test_descrtut.C'> 1\n\n    >>> class D(C):\n    ...     pass\n\n    >>> D.foo(1)\n    classmethod <class 'test.test_descrtut.D'> 1\n    >>> d = D()\n    >>> d.foo(1)\n    classmethod <class 'test.test_descrtut.D'> 1\n\nThis prints \"classmethod __main__.D 1\" both times; in other words, the\nclass passed as the first argument of foo() is the class involved in the\ncall, not the class involved in the definition of foo().\n\nBut notice this:\n\n    >>> class E(C):\n    ...     @classmethod\n    ...     def foo(cls, y): # override C.foo\n    ...         print(\"E.foo() called\")\n    ...         C.foo(y)\n\n    >>> E.foo(1)\n    E.foo() called\n    classmethod <class 'test.test_descrtut.C'> 1\n    >>> e = E()\n    >>> e.foo(1)\n    E.foo() called\n    classmethod <class 'test.test_descrtut.C'> 1\n\nIn this example, the call to C.foo() from E.foo() will see class C as its\nfirst argument, not class E. This is to be expected, since the call\nspecifies the class C. But it stresses the difference between these class\nmethods and methods defined in metaclasses (where an upcall to a metamethod\nwould pass the target class as an explicit first argument).\n"
test_5 = "\n\nAttributes defined by get/set methods\n\n\n    >>> class property(object):\n    ...\n    ...     def __init__(self, get, set=None):\n    ...         self.__get = get\n    ...         self.__set = set\n    ...\n    ...     def __get__(self, inst, type=None):\n    ...         return self.__get(inst)\n    ...\n    ...     def __set__(self, inst, value):\n    ...         if self.__set is None:\n    ...             raise AttributeError(\"this attribute is read-only\")\n    ...         return self.__set(inst, value)\n\nNow let's define a class with an attribute x defined by a pair of methods,\ngetx() and setx():\n\n    >>> class C(object):\n    ...\n    ...     def __init__(self):\n    ...         self.__x = 0\n    ...\n    ...     def getx(self):\n    ...         return self.__x\n    ...\n    ...     def setx(self, x):\n    ...         if x < 0: x = 0\n    ...         self.__x = x\n    ...\n    ...     x = property(getx, setx)\n\nHere's a small demonstration:\n\n    >>> a = C()\n    >>> a.x = 10\n    >>> print(a.x)\n    10\n    >>> a.x = -10\n    >>> print(a.x)\n    0\n    >>>\n\nHmm -- property is builtin now, so let's try it that way too.\n\n    >>> del property  # unmask the builtin\n    >>> property\n    <class 'property'>\n\n    >>> class C(object):\n    ...     def __init__(self):\n    ...         self.__x = 0\n    ...     def getx(self):\n    ...         return self.__x\n    ...     def setx(self, x):\n    ...         if x < 0: x = 0\n    ...         self.__x = x\n    ...     x = property(getx, setx)\n\n\n    >>> a = C()\n    >>> a.x = 10\n    >>> print(a.x)\n    10\n    >>> a.x = -10\n    >>> print(a.x)\n    0\n    >>>\n"
test_6 = '\n\nMethod resolution order\n\nThis example is implicit in the writeup.\n\n>>> class A:    # implicit new-style class\n...     def save(self):\n...         print("called A.save()")\n>>> class B(A):\n...     pass\n>>> class C(A):\n...     def save(self):\n...         print("called C.save()")\n>>> class D(B, C):\n...     pass\n\n>>> D().save()\ncalled C.save()\n\n>>> class A(object):  # explicit new-style class\n...     def save(self):\n...         print("called A.save()")\n>>> class B(A):\n...     pass\n>>> class C(A):\n...     def save(self):\n...         print("called C.save()")\n>>> class D(B, C):\n...     pass\n\n>>> D().save()\ncalled C.save()\n'


class A(object):
    def m(self):
        return "A"


class B(A):
    def m(self):
        return "B" + super(B, self).m()


class C(A):
    def m(self):
        return "C" + super(C, self).m()


class D(C, B):
    def m(self):
        return "D" + super(D, self).m()


test_7 = '\n\nCooperative methods and "super"\n\n>>> print(D().m()) # "DCBA"\nDCBA\n'
test_8 = '\n\nBackwards incompatibilities\n\n>>> class A:\n...     def foo(self):\n...         print("called A.foo()")\n\n>>> class B(A):\n...     pass\n\n>>> class C(A):\n...     def foo(self):\n...         B.foo(self)\n\n>>> C().foo()\ncalled A.foo()\n\n>>> class C(A):\n...     def foo(self):\n...         A.foo(self)\n>>> C().foo()\ncalled A.foo()\n'
__test__ = {
    "tut1": test_1,
    "tut2": test_2,
    "tut3": test_3,
    "tut4": test_4,
    "tut5": test_5,
    "tut6": test_6,
    "tut7": test_7,
    "tut8": test_8,
}


def test_main(verbose=None):
    from test import support, test_descrtut

    support.run_doctest(test_descrtut, verbose)


if __name__ == "__main__":
    test_main(1)
