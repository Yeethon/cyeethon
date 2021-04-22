_NOT_SET = object()


class Slot:
    "A descriptor that provides a slot.\n\n    This is useful for types that can't have slots via __slots__,\n    e.g. tuple subclasses.\n    "
    __slots__ = ("initial", "default", "readonly", "instances", "name")

    def __init__(self, initial=_NOT_SET, *, default=_NOT_SET, readonly=False):
        self.initial = initial
        self.default = default
        self.readonly = readonly
        self.instances = {}
        self.name = None

    def __set_name__(self, cls, name):
        if self.name is not None:
            raise TypeError("already used")
        self.name = name
        try:
            slotnames = cls.__slot_names__
        except AttributeError:
            slotnames = cls.__slot_names__ = []
        slotnames.append(name)
        self._ensure___del__(cls, slotnames)

    def __get__(self, obj, cls):
        if obj is None:
            return self
        try:
            value = self.instances[id(obj)]
        except KeyError:
            if self.initial is _NOT_SET:
                value = self.default
            else:
                value = self.initial
            self.instances[id(obj)] = value
        if value is _NOT_SET:
            raise AttributeError(self.name)
        return value

    def __set__(self, obj, value):
        if self.readonly:
            raise AttributeError(f"{self.name} is readonly")
        self.instances[id(obj)] = value

    def __delete__(self, obj):
        if self.readonly:
            raise AttributeError(f"{self.name} is readonly")
        self.instances[id(obj)] = self.default

    def _ensure___del__(self, cls, slotnames):
        try:
            old___del__ = cls.__del__
        except AttributeError:
            old___del__ = lambda s: None
        else:
            if getattr(old___del__, "_slotted", False):
                return

        def __del__(_self):
            for name in slotnames:
                delattr(_self, name)
            old___del__(_self)

        __del__._slotted = True
        cls.__del__ = __del__

    def set(self, obj, value):
        "Update the cached value for an object.\n\n        This works even if the descriptor is read-only.  This is\n        particularly useful when initializing the object (e.g. in\n        its __new__ or __init__).\n        "
        self.instances[id(obj)] = value


class classonly:
    'A non-data descriptor that makes a value only visible on the class.\n\n    This is like the "classmethod" builtin, but does not show up on\n    instances of the class.  It may be used as a decorator.\n    '

    def __init__(self, value):
        self.value = value
        self.getter = classmethod(value).__get__
        self.name = None

    def __set_name__(self, cls, name):
        if self.name is not None:
            raise TypeError("already used")
        self.name = name

    def __get__(self, obj, cls):
        if obj is not None:
            raise AttributeError(self.name)
        return self.getter(None, cls)
