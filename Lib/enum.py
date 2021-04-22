import sys
from types import MappingProxyType, DynamicClassAttribute
from builtins import property as _bltin_property, bin as _bltin_bin

__all__ = [
    "EnumType",
    "EnumMeta",
    "Enum",
    "IntEnum",
    "StrEnum",
    "Flag",
    "IntFlag",
    "auto",
    "unique",
    "property",
    "FlagBoundary",
    "STRICT",
    "CONFORM",
    "EJECT",
    "KEEP",
    "global_flag_repr",
    "global_enum_repr",
    "global_enum",
]
Enum = Flag = EJECT = None


def _is_descriptor(obj):
    "\n    Returns True if obj is a descriptor, False otherwise.\n    "
    return (
        hasattr(obj, "__get__") or hasattr(obj, "__set__") or hasattr(obj, "__delete__")
    )


def _is_dunder(name):
    "\n    Returns True if a __dunder__ name, False otherwise.\n    "
    return (
        (len(name) > 4)
        and (name[:2] == name[(-2):] == "__")
        and (name[2] != "_")
        and (name[(-3)] != "_")
    )


def _is_sunder(name):
    "\n    Returns True if a _sunder_ name, False otherwise.\n    "
    return (
        (len(name) > 2)
        and (name[0] == name[(-1)] == "_")
        and (name[1:2] != "_")
        and (name[(-2):(-1)] != "_")
    )


def _is_private(cls_name, name):
    pattern = "_%s__" % (cls_name,)
    pat_len = len(pattern)
    if (
        (len(name) > pat_len)
        and name.startswith(pattern)
        and (name[pat_len : (pat_len + 1)] != ["_"])
        and ((name[(-1)] != "_") or (name[(-2)] != "_"))
    ):
        return True
    else:
        return False


def _is_single_bit(num):
    "\n    True if only one bit set in num (should be an int)\n    "
    if num == 0:
        return False
    num &= num - 1
    return num == 0


def _make_class_unpicklable(obj):
    "\n    Make the given obj un-picklable.\n\n    obj should be either a dictionary, on an Enum\n    "

    def _break_on_call_reduce(self, proto):
        raise TypeError(("%r cannot be pickled" % self))

    if isinstance(obj, dict):
        obj["__reduce_ex__"] = _break_on_call_reduce
        obj["__module__"] = "<unknown>"
    else:
        setattr(obj, "__reduce_ex__", _break_on_call_reduce)
        setattr(obj, "__module__", "<unknown>")


def _iter_bits_lsb(num):
    while num:
        b = num & ((~num) + 1)
        (yield b)
        num ^= b


def bin(num, max_bits=None):
    "\n    Like built-in bin(), except negative values are represented in\n    twos-compliment, and the leading bit always indicates sign\n    (0=positive, 1=negative).\n\n    >>> bin(10)\n    '0b0 1010'\n    >>> bin(~10)   # ~10 is -11\n    '0b1 0101'\n    "
    ceiling = 2 ** num.bit_length()
    if num >= 0:
        s = _bltin_bin((num + ceiling)).replace("1", "0", 1)
    else:
        s = _bltin_bin(((~num) ^ ((ceiling - 1) + ceiling)))
    sign = s[:3]
    digits = s[3:]
    if max_bits is not None:
        if len(digits) < max_bits:
            digits = ((sign[(-1)] * max_bits) + digits)[(-max_bits):]
    return "%s %s" % (sign, digits)


_auto_null = object()


class auto:
    "\n    Instances are replaced with an appropriate value in Enum class suites.\n    "
    value = _auto_null


class property(DynamicClassAttribute):
    "\n    This is a descriptor, used to define attributes that act differently\n    when accessed through an enum member and through an enum class.\n    Instance access is the same as property(), but access to an attribute\n    through the enum class will instead look in the class' _member_map_ for\n    a corresponding enum member.\n    "

    def __get__(self, instance, ownerclass=None):
        if instance is None:
            try:
                return ownerclass._member_map_[self.name]
            except KeyError:
                raise AttributeError(
                    ("%s: no class attribute %r" % (ownerclass.__name__, self.name))
                )
        elif self.fget is None:
            if self.name in ownerclass._member_map_:
                import warnings

                warnings.warn(
                    "accessing one member from another is not supported,  and will be disabled in 3.12",
                    DeprecationWarning,
                    stacklevel=2,
                )
                return ownerclass._member_map_[self.name]
            raise AttributeError(
                ("%s: no instance attribute %r" % (ownerclass.__name__, self.name))
            )
        else:
            return self.fget(instance)

    def __set__(self, instance, value):
        if self.fset is None:
            raise AttributeError(
                ("%s: cannot set instance attribute %r" % (self.clsname, self.name))
            )
        else:
            return self.fset(instance, value)

    def __delete__(self, instance):
        if self.fdel is None:
            raise AttributeError(
                ("%s: cannot delete instance attribute %r" % (self.clsname, self.name))
            )
        else:
            return self.fdel(instance)

    def __set_name__(self, ownerclass, name):
        self.name = name
        self.clsname = ownerclass.__name__


class _proto_member:
    "\n    intermediate step for enum members between class execution and final creation\n    "

    def __init__(self, value):
        self.value = value

    def __set_name__(self, enum_class, member_name):
        "\n        convert each quasi-member into an instance of the new enum class\n        "
        delattr(enum_class, member_name)
        value = self.value
        if not isinstance(value, tuple):
            args = (value,)
        else:
            args = value
        if enum_class._member_type_ is tuple:
            args = (args,)
        if not enum_class._use_args_:
            enum_member = enum_class._new_member_(enum_class)
            if not hasattr(enum_member, "_value_"):
                enum_member._value_ = value
        else:
            enum_member = enum_class._new_member_(enum_class, *args)
            if not hasattr(enum_member, "_value_"):
                if enum_class._member_type_ is object:
                    enum_member._value_ = value
                else:
                    try:
                        enum_member._value_ = enum_class._member_type_(*args)
                    except Exception as exc:
                        raise TypeError(
                            "_value_ not set in __new__, unable to create it"
                        ) from None
        value = enum_member._value_
        enum_member._name_ = member_name
        enum_member.__objclass__ = enum_class
        enum_member.__init__(*args)
        enum_member._sort_order_ = len(enum_class._member_names_)
        for (name, canonical_member) in enum_class._member_map_.items():
            if canonical_member._value_ == enum_member._value_:
                enum_member = canonical_member
                break
        else:
            if (Flag is None) or (not issubclass(enum_class, Flag)):
                enum_class._member_names_.append(member_name)
            elif (
                (Flag is not None)
                and issubclass(enum_class, Flag)
                and _is_single_bit(value)
            ):
                enum_class._member_names_.append(member_name)
        need_override = False
        descriptor = None
        for base in enum_class.__mro__[1:]:
            descriptor = base.__dict__.get(member_name)
            if descriptor is not None:
                if isinstance(descriptor, (property, DynamicClassAttribute)):
                    break
                else:
                    need_override = True
        if descriptor and (not need_override):
            pass
        else:
            redirect = property()
            redirect.__set_name__(enum_class, member_name)
            if descriptor and need_override:
                redirect.fget = descriptor.fget
                redirect.fset = descriptor.fset
                redirect.fdel = descriptor.fdel
            setattr(enum_class, member_name, redirect)
        enum_class._member_map_[member_name] = enum_member
        try:
            enum_class._value2member_map_.setdefault(value, enum_member)
        except TypeError:
            pass


class _EnumDict(dict):
    "\n    Track enum member order and ensure member names are not reused.\n\n    EnumType will use the names found in self._member_names as the\n    enumeration member names.\n    "

    def __init__(self):
        super().__init__()
        self._member_names = []
        self._last_values = []
        self._ignore = []
        self._auto_called = False

    def __setitem__(self, key, value):
        "\n        Changes anything not dundered or not a descriptor.\n\n        If an enum member name is used twice, an error is raised; duplicate\n        values are not checked for.\n\n        Single underscore (sunder) names are reserved.\n        "
        if _is_private(self._cls_name, key):
            pass
        elif _is_sunder(key):
            if key not in (
                "_order_",
                "_generate_next_value_",
                "_missing_",
                "_ignore_",
                "_iter_member_",
                "_iter_member_by_value_",
                "_iter_member_by_def_",
            ):
                raise ValueError(
                    (
                        "_sunder_ names, such as %r, are reserved for future Enum use"
                        % (key,)
                    )
                )
            if key == "_generate_next_value_":
                if self._auto_called:
                    raise TypeError(
                        "_generate_next_value_ must be defined before members"
                    )
                _gnv = value.__func__ if isinstance(value, staticmethod) else value
                setattr(self, "_generate_next_value", _gnv)
            elif key == "_ignore_":
                if isinstance(value, str):
                    value = value.replace(",", " ").split()
                else:
                    value = list(value)
                self._ignore = value
                already = set(value) & set(self._member_names)
                if already:
                    raise ValueError(
                        ("_ignore_ cannot specify already set names: %r" % (already,))
                    )
        elif _is_dunder(key):
            if key == "__order__":
                key = "_order_"
        elif key in self._member_names:
            raise TypeError(("%r already defined as: %r" % (key, self[key])))
        elif key in self._ignore:
            pass
        elif not _is_descriptor(value):
            if key in self:
                raise TypeError(("%r already defined as: %r" % (key, self[key])))
            if isinstance(value, auto):
                if value.value == _auto_null:
                    value.value = self._generate_next_value(
                        key, 1, len(self._member_names), self._last_values[:]
                    )
                    self._auto_called = True
                value = value.value
            self._member_names.append(key)
            self._last_values.append(value)
        super().__setitem__(key, value)

    def update(self, members, **more_members):
        try:
            for name in members.keys():
                self[name] = members[name]
        except AttributeError:
            for (name, value) in members:
                self[name] = value
        for (name, value) in more_members.items():
            self[name] = value


class EnumType(type):
    "\n    Metaclass for Enum\n    "

    @classmethod
    def __prepare__(metacls, cls, bases, **kwds):
        metacls._check_for_existing_members(cls, bases)
        enum_dict = _EnumDict()
        enum_dict._cls_name = cls
        (member_type, first_enum) = metacls._get_mixins_(cls, bases)
        if first_enum is not None:
            enum_dict["_generate_next_value_"] = getattr(
                first_enum, "_generate_next_value_", None
            )
        return enum_dict

    def __new__(
        metacls, cls, bases, classdict, *, boundary=None, _simple=False, **kwds
    ):
        if _simple:
            return super().__new__(metacls, cls, bases, classdict, **kwds)
        classdict.setdefault("_ignore_", []).append("_ignore_")
        ignore = classdict["_ignore_"]
        for key in ignore:
            classdict.pop(key, None)
        member_names = classdict._member_names
        invalid_names = set(member_names) & {"mro", ""}
        if invalid_names:
            raise ValueError(
                "Invalid enum member name: {0}".format(",".join(invalid_names))
            )
        _order_ = classdict.pop("_order_", None)
        classdict = dict(classdict.items())
        (member_type, first_enum) = metacls._get_mixins_(cls, bases)
        (__new__, save_new, use_args) = metacls._find_new_(
            classdict, member_type, first_enum
        )
        classdict["_new_member_"] = __new__
        classdict["_use_args_"] = use_args
        flag_mask = 0
        for name in member_names:
            value = classdict[name]
            if isinstance(value, int):
                flag_mask |= value
            classdict[name] = _proto_member(value)
        classdict["_member_names_"] = []
        classdict["_member_map_"] = {}
        classdict["_value2member_map_"] = {}
        classdict["_member_type_"] = member_type
        classdict["_boundary_"] = boundary or getattr(first_enum, "_boundary_", None)
        classdict["_flag_mask_"] = flag_mask
        classdict["_all_bits_"] = (2 ** flag_mask.bit_length()) - 1
        classdict["_inverted_"] = None
        if "__reduce_ex__" not in classdict:
            if member_type is not object:
                methods = (
                    "__getnewargs_ex__",
                    "__getnewargs__",
                    "__reduce_ex__",
                    "__reduce__",
                )
                if not any(((m in member_type.__dict__) for m in methods)):
                    _make_class_unpicklable(classdict)
        if "__doc__" not in classdict:
            classdict["__doc__"] = "An enumeration."
        try:
            exc = None
            enum_class = super().__new__(metacls, cls, bases, classdict, **kwds)
        except RuntimeError as e:
            exc = e.__cause__ or e
        if exc is not None:
            raise exc
        for name in ("__repr__", "__str__", "__format__", "__reduce_ex__"):
            if name in classdict:
                continue
            class_method = getattr(enum_class, name)
            obj_method = getattr(member_type, name, None)
            enum_method = getattr(first_enum, name, None)
            if (obj_method is not None) and (obj_method is class_method):
                setattr(enum_class, name, enum_method)
        if Enum is not None:
            if save_new:
                enum_class.__new_member__ = __new__
            enum_class.__new__ = Enum.__new__
        if _order_ is not None:
            if isinstance(_order_, str):
                _order_ = _order_.replace(",", " ").split()
        if ((Flag is None) and (cls != "Flag")) or (
            (Flag is not None) and (not issubclass(enum_class, Flag))
        ):
            delattr(enum_class, "_boundary_")
            delattr(enum_class, "_flag_mask_")
            delattr(enum_class, "_all_bits_")
            delattr(enum_class, "_inverted_")
        elif (Flag is not None) and issubclass(enum_class, Flag):
            single_bit_total = 0
            multi_bit_total = 0
            for flag in enum_class._member_map_.values():
                flag_value = flag._value_
                if _is_single_bit(flag_value):
                    single_bit_total |= flag_value
                else:
                    multi_bit_total |= flag_value
            if enum_class._boundary_ is not KEEP:
                missed = list(_iter_bits_lsb((multi_bit_total & (~single_bit_total))))
                if missed:
                    raise TypeError(
                        (
                            "invalid Flag %r -- missing values: %s"
                            % (cls, ", ".join((str(i) for i in missed)))
                        )
                    )
            enum_class._flag_mask_ = single_bit_total
            member_list = [m._value_ for m in enum_class]
            if member_list != sorted(member_list):
                enum_class._iter_member_ = enum_class._iter_member_by_def_
            if _order_:
                _order_ = [
                    o
                    for o in _order_
                    if (
                        (o not in enum_class._member_map_)
                        or _is_single_bit(enum_class[o]._value_)
                    )
                ]
        if _order_:
            _order_ = [
                o
                for o in _order_
                if (
                    (o not in enum_class._member_map_)
                    or (
                        (o in enum_class._member_map_)
                        and (o in enum_class._member_names_)
                    )
                )
            ]
            if _order_ != enum_class._member_names_:
                raise TypeError(
                    (
                        "member order does not match _order_:\n%r\n%r"
                        % (enum_class._member_names_, _order_)
                    )
                )
        return enum_class

    def __bool__(self):
        "\n        classes/types should always be True.\n        "
        return True

    def __call__(
        cls,
        value,
        names=None,
        *,
        module=None,
        qualname=None,
        type=None,
        start=1,
        boundary=None
    ):
        "\n        Either returns an existing member, or creates a new enum class.\n\n        This method is used both when an enum class is given a value to match\n        to an enumeration member (i.e. Color(3)) and for the functional API\n        (i.e. Color = Enum('Color', names='RED GREEN BLUE')).\n\n        When used for the functional API:\n\n        `value` will be the name of the new class.\n\n        `names` should be either a string of white-space/comma delimited names\n        (values will start at `start`), or an iterator/mapping of name, value pairs.\n\n        `module` should be set to the module this class is being created in;\n        if it is not set, an attempt to find that module will be made, but if\n        it fails the class will not be picklable.\n\n        `qualname` should be set to the actual location this class can be found\n        at in its module; by default it is set to the global scope.  If this is\n        not correct, unpickling will fail in some circumstances.\n\n        `type`, if set, will be mixed in as the first base class.\n        "
        if names is None:
            return cls.__new__(cls, value)
        return cls._create_(
            value,
            names,
            module=module,
            qualname=qualname,
            type=type,
            start=start,
            boundary=boundary,
        )

    def __contains__(cls, member):
        if not isinstance(member, Enum):
            raise TypeError(
                (
                    "unsupported operand type(s) for 'in': '%s' and '%s'"
                    % (type(member).__qualname__, cls.__class__.__qualname__)
                )
            )
        return isinstance(member, cls) and (member._name_ in cls._member_map_)

    def __delattr__(cls, attr):
        if attr in cls._member_map_:
            raise AttributeError(
                ("%s: cannot delete Enum member %r." % (cls.__name__, attr))
            )
        super().__delattr__(attr)

    def __dir__(self):
        return [
            "__class__",
            "__doc__",
            "__members__",
            "__module__",
        ] + self._member_names_

    def __getattr__(cls, name):
        "\n        Return the enum member matching `name`\n\n        We use __getattr__ instead of descriptors or inserting into the enum\n        class' __dict__ in order to support `name` and `value` being both\n        properties for enum members (which live in the class' __dict__) and\n        enum members themselves.\n        "
        if _is_dunder(name):
            raise AttributeError(name)
        try:
            return cls._member_map_[name]
        except KeyError:
            raise AttributeError(name) from None

    def __getitem__(cls, name):
        return cls._member_map_[name]

    def __iter__(cls):
        "\n        Returns members in definition order.\n        "
        return (cls._member_map_[name] for name in cls._member_names_)

    def __len__(cls):
        return len(cls._member_names_)

    @_bltin_property
    def __members__(cls):
        "\n        Returns a mapping of member name->value.\n\n        This mapping lists all enum members, including aliases. Note that this\n        is a read-only view of the internal mapping.\n        "
        return MappingProxyType(cls._member_map_)

    def __repr__(cls):
        return "<enum %r>" % cls.__name__

    def __reversed__(cls):
        "\n        Returns members in reverse definition order.\n        "
        return (cls._member_map_[name] for name in reversed(cls._member_names_))

    def __setattr__(cls, name, value):
        "\n        Block attempts to reassign Enum members.\n\n        A simple assignment to the class namespace only changes one of the\n        several possible ways to get an Enum member from the Enum class,\n        resulting in an inconsistent Enumeration.\n        "
        member_map = cls.__dict__.get("_member_map_", {})
        if name in member_map:
            raise AttributeError(("Cannot reassign member %r." % (name,)))
        super().__setattr__(name, value)

    def _create_(
        cls,
        class_name,
        names,
        *,
        module=None,
        qualname=None,
        type=None,
        start=1,
        boundary=None
    ):
        "\n        Convenience method to create a new Enum class.\n\n        `names` can be:\n\n        * A string containing member names, separated either with spaces or\n          commas.  Values are incremented by 1 from `start`.\n        * An iterable of member names.  Values are incremented by 1 from `start`.\n        * An iterable of (member name, value) pairs.\n        * A mapping of member name -> value pairs.\n        "
        metacls = cls.__class__
        bases = (cls,) if (type is None) else (type, cls)
        (_, first_enum) = cls._get_mixins_(cls, bases)
        classdict = metacls.__prepare__(class_name, bases)
        if isinstance(names, str):
            names = names.replace(",", " ").split()
        if isinstance(names, (tuple, list)) and names and isinstance(names[0], str):
            (original_names, names) = (names, [])
            last_values = []
            for (count, name) in enumerate(original_names):
                value = first_enum._generate_next_value_(
                    name, start, count, last_values[:]
                )
                last_values.append(value)
                names.append((name, value))
        for item in names:
            if isinstance(item, str):
                (member_name, member_value) = (item, names[item])
            else:
                (member_name, member_value) = item
            classdict[member_name] = member_value
        if module is None:
            try:
                module = sys._getframe(2).f_globals["__name__"]
            except (AttributeError, ValueError, KeyError):
                pass
        if module is None:
            _make_class_unpicklable(classdict)
        else:
            classdict["__module__"] = module
        if qualname is not None:
            classdict["__qualname__"] = qualname
        return metacls.__new__(metacls, class_name, bases, classdict, boundary=boundary)

    def _convert_(cls, name, module, filter, source=None, *, boundary=None):
        "\n        Create a new Enum subclass that replaces a collection of global constants\n        "
        module_globals = sys.modules[module].__dict__
        if source:
            source = source.__dict__
        else:
            source = module_globals
        members = [(name, value) for (name, value) in source.items() if filter(name)]
        try:
            members.sort(key=(lambda t: (t[1], t[0])))
        except TypeError:
            members.sort(key=(lambda t: t[0]))
        body = {t[0]: t[1] for t in members}
        body["__module__"] = module
        tmp_cls = type(name, (object,), body)
        cls = _simple_enum(etype=cls, boundary=(boundary or KEEP))(tmp_cls)
        cls.__reduce_ex__ = _reduce_ex_by_name
        global_enum(cls)
        module_globals[name] = cls
        return cls

    @staticmethod
    def _check_for_existing_members(class_name, bases):
        for chain in bases:
            for base in chain.__mro__:
                if issubclass(base, Enum) and base._member_names_:
                    raise TypeError(
                        (
                            "%s: cannot extend enumeration %r"
                            % (class_name, base.__name__)
                        )
                    )

    @staticmethod
    def _get_mixins_(class_name, bases):
        "\n        Returns the type for creating enum members, and the first inherited\n        enum class.\n\n        bases: the tuple of bases that was given to __new__\n        "
        if not bases:
            return (object, Enum)

        def _find_data_type(bases):
            data_types = []
            for chain in bases:
                candidate = None
                for base in chain.__mro__:
                    if base is object:
                        continue
                    elif issubclass(base, Enum):
                        if base._member_type_ is not object:
                            data_types.append(base._member_type_)
                            break
                    elif "__new__" in base.__dict__:
                        if issubclass(base, Enum):
                            continue
                        data_types.append((candidate or base))
                        break
                    else:
                        candidate = base
            if len(data_types) > 1:
                raise TypeError(
                    ("%r: too many data types: %r" % (class_name, data_types))
                )
            elif data_types:
                return data_types[0]
            else:
                return None

        first_enum = bases[(-1)]
        if not issubclass(first_enum, Enum):
            raise TypeError(
                "new enumerations should be created as `EnumName([mixin_type, ...] [data_type,] enum_type)`"
            )
        member_type = _find_data_type(bases) or object
        if first_enum._member_names_:
            raise TypeError("Cannot extend enumerations")
        return (member_type, first_enum)

    @staticmethod
    def _find_new_(classdict, member_type, first_enum):
        "\n        Returns the __new__ to be used for creating the enum members.\n\n        classdict: the class dictionary given to __new__\n        member_type: the data type whose __new__ will be used by default\n        first_enum: enumeration to check for an overriding __new__\n        "
        __new__ = classdict.get("__new__", None)
        save_new = (first_enum is not None) and (__new__ is not None)
        if __new__ is None:
            for method in ("__new_member__", "__new__"):
                for possible in (member_type, first_enum):
                    target = getattr(possible, method, None)
                    if target not in {None, None.__new__, object.__new__, Enum.__new__}:
                        __new__ = target
                        break
                if __new__ is not None:
                    break
            else:
                __new__ = object.__new__
        if (first_enum is None) or (__new__ in (Enum.__new__, object.__new__)):
            use_args = False
        else:
            use_args = True
        return (__new__, save_new, use_args)


EnumMeta = EnumType


class Enum(metaclass=EnumType):
    "\n    Generic enumeration.\n\n    Derive from this class to define new enumerations.\n    "

    def __new__(cls, value):
        if type(value) is cls:
            return value
        try:
            return cls._value2member_map_[value]
        except KeyError:
            pass
        except TypeError:
            for member in cls._member_map_.values():
                if member._value_ == value:
                    return member
        try:
            exc = None
            result = cls._missing_(value)
        except Exception as e:
            exc = e
            result = None
        try:
            if isinstance(result, cls):
                return result
            elif (
                (Flag is not None)
                and issubclass(cls, Flag)
                and (cls._boundary_ is EJECT)
                and isinstance(result, int)
            ):
                return result
            else:
                ve_exc = ValueError(
                    ("%r is not a valid %s" % (value, cls.__qualname__))
                )
                if (result is None) and (exc is None):
                    raise ve_exc
                elif exc is None:
                    exc = TypeError(
                        (
                            "error in %s._missing_: returned %r instead of None or a valid member"
                            % (cls.__name__, result)
                        )
                    )
                if not isinstance(exc, ValueError):
                    exc.__context__ = ve_exc
                raise exc
        finally:
            exc = None
            ve_exc = None

    def _generate_next_value_(name, start, count, last_values):
        "\n        Generate the next value when not given.\n\n        name: the name of the member\n        start: the initial start value or None\n        count: the number of existing members\n        last_value: the last value assigned or None\n        "
        for last_value in reversed(last_values):
            try:
                return last_value + 1
            except TypeError:
                pass
        else:
            return start

    @classmethod
    def _missing_(cls, value):
        return None

    def __repr__(self):
        return "%s.%s" % (self.__class__.__name__, self._name_)

    def __str__(self):
        return "%s" % (self._name_,)

    def __dir__(self):
        "\n        Returns all members and all public methods\n        "
        added_behavior = [
            m
            for cls in self.__class__.mro()
            for m in cls.__dict__
            if ((m[0] != "_") and (m not in self._member_map_))
        ] + [m for m in self.__dict__ if (m[0] != "_")]
        return ["__class__", "__doc__", "__module__"] + added_behavior

    def __format__(self, format_spec):
        "\n        Returns format using actual value type unless __str__ has been overridden.\n        "
        str_overridden = type(self).__str__ not in (Enum.__str__, Flag.__str__)
        if (self._member_type_ is object) or str_overridden:
            cls = str
            val = str(self)
        else:
            cls = self._member_type_
            val = self._value_
        return cls.__format__(val, format_spec)

    def __hash__(self):
        return hash(self._name_)

    def __reduce_ex__(self, proto):
        return (self.__class__, (self._value_,))

    @property
    def name(self):
        "The name of the Enum member."
        return self._name_

    @property
    def value(self):
        "The value of the Enum member."
        return self._value_


class IntEnum(int, Enum):
    "\n    Enum where members are also (and must be) ints\n    "


class StrEnum(str, Enum):
    "\n    Enum where members are also (and must be) strings\n    "

    def __new__(cls, *values):
        if len(values) > 3:
            raise TypeError(("too many arguments for str(): %r" % (values,)))
        if len(values) == 1:
            if not isinstance(values[0], str):
                raise TypeError(("%r is not a string" % (values[0],)))
        if len(values) >= 2:
            if not isinstance(values[1], str):
                raise TypeError(("encoding must be a string, not %r" % (values[1],)))
        if len(values) == 3:
            if not isinstance(values[2], str):
                raise TypeError(("errors must be a string, not %r" % values[2]))
        value = str(*values)
        member = str.__new__(cls, value)
        member._value_ = value
        return member

    __str__ = str.__str__

    def _generate_next_value_(name, start, count, last_values):
        "\n        Return the lower-cased version of the member name.\n        "
        return name.lower()


def _reduce_ex_by_name(self, proto):
    return self.name


class FlagBoundary(StrEnum):
    '\n    control how out of range values are handled\n    "strict" -> error is raised  [default for Flag]\n    "conform" -> extra bits are discarded\n    "eject" -> lose flag status [default for IntFlag]\n    "keep" -> keep flag status and all bits\n    '
    STRICT = auto()
    CONFORM = auto()
    EJECT = auto()
    KEEP = auto()


(STRICT, CONFORM, EJECT, KEEP) = FlagBoundary


class Flag(Enum, boundary=STRICT):
    "\n    Support for flags\n    "

    def _generate_next_value_(name, start, count, last_values):
        "\n        Generate the next value when not given.\n\n        name: the name of the member\n        start: the initial start value or None\n        count: the number of existing members\n        last_value: the last value assigned or None\n        "
        if not count:
            return start if (start is not None) else 1
        last_value = max(last_values)
        try:
            high_bit = _high_bit(last_value)
        except Exception:
            raise TypeError(("Invalid Flag value: %r" % last_value)) from None
        return 2 ** (high_bit + 1)

    @classmethod
    def _iter_member_by_value_(cls, value):
        "\n        Extract all members from the value in definition (i.e. increasing value) order.\n        "
        for val in _iter_bits_lsb((value & cls._flag_mask_)):
            (yield cls._value2member_map_.get(val))

    _iter_member_ = _iter_member_by_value_

    @classmethod
    def _iter_member_by_def_(cls, value):
        "\n        Extract all members from the value in definition order.\n        "
        (
            yield from sorted(
                cls._iter_member_by_value_(value), key=(lambda m: m._sort_order_)
            )
        )

    @classmethod
    def _missing_(cls, value):
        "\n        Create a composite member containing all canonical members present in `value`.\n\n        If non-member values are present, result depends on `_boundary_` setting.\n        "
        if not isinstance(value, int):
            raise ValueError(("%r is not a valid %s" % (value, cls.__qualname__)))
        flag_mask = cls._flag_mask_
        all_bits = cls._all_bits_
        neg_value = None
        if (not ((~all_bits) <= value <= all_bits)) or (value & (all_bits ^ flag_mask)):
            if cls._boundary_ is STRICT:
                max_bits = max(value.bit_length(), flag_mask.bit_length())
                raise ValueError(
                    (
                        "%s: invalid value: %r\n    given %s\n  allowed %s"
                        % (
                            cls.__name__,
                            value,
                            bin(value, max_bits),
                            bin(flag_mask, max_bits),
                        )
                    )
                )
            elif cls._boundary_ is CONFORM:
                value = value & flag_mask
            elif cls._boundary_ is EJECT:
                return value
            elif cls._boundary_ is KEEP:
                if value < 0:
                    value = max((all_bits + 1), (2 ** value.bit_length())) + value
            else:
                raise ValueError(("unknown flag boundary: %r" % (cls._boundary_,)))
        if value < 0:
            neg_value = value
            value = (all_bits + 1) + value
        unknown = value & (~flag_mask)
        member_value = value & flag_mask
        if unknown and (cls._boundary_ is not KEEP):
            raise ValueError(
                (
                    "%s(%r) -->  unknown values %r [%s]"
                    % (cls.__name__, value, unknown, bin(unknown))
                )
            )
        __new__ = getattr(cls, "__new_member__", None)
        if (cls._member_type_ is object) and (not __new__):
            pseudo_member = object.__new__(cls)
        else:
            pseudo_member = (__new__ or cls._member_type_.__new__)(cls, value)
        if not hasattr(pseudo_member, "_value_"):
            pseudo_member._value_ = value
        if member_value:
            pseudo_member._name_ = "|".join(
                [m._name_ for m in cls._iter_member_(member_value)]
            )
            if unknown:
                pseudo_member._name_ += "|0x%x" % unknown
        else:
            pseudo_member._name_ = None
        if not unknown:
            pseudo_member = cls._value2member_map_.setdefault(value, pseudo_member)
            if neg_value is not None:
                cls._value2member_map_[neg_value] = pseudo_member
        return pseudo_member

    def __contains__(self, other):
        "\n        Returns True if self has at least the same flags set as other.\n        "
        if not isinstance(other, self.__class__):
            raise TypeError(
                (
                    "unsupported operand type(s) for 'in': '%s' and '%s'"
                    % (type(other).__qualname__, self.__class__.__qualname__)
                )
            )
        if (other._value_ == 0) or (self._value_ == 0):
            return False
        return (other._value_ & self._value_) == other._value_

    def __iter__(self):
        "\n        Returns flags in definition order.\n        "
        (yield from self._iter_member_(self._value_))

    def __len__(self):
        return self._value_.bit_count()

    def __repr__(self):
        cls_name = self.__class__.__name__
        if self._name_ is None:
            return "0x%x" % (self._value_,)
        if _is_single_bit(self._value_):
            return "%s.%s" % (cls_name, self._name_)
        if self._boundary_ is not FlagBoundary.KEEP:
            return ("%s." % cls_name) + ("|%s." % cls_name).join(self.name.split("|"))
        else:
            name = []
            for n in self._name_.split("|"):
                if n.startswith("0"):
                    name.append(n)
                else:
                    name.append(("%s.%s" % (cls_name, n)))
            return "|".join(name)

    def __str__(self):
        cls = self.__class__
        if self._name_ is None:
            return "%s(%x)" % (cls.__name__, self._value_)
        else:
            return self._name_

    def __bool__(self):
        return bool(self._value_)

    def __or__(self, other):
        if not isinstance(other, self.__class__):
            return NotImplemented
        return self.__class__((self._value_ | other._value_))

    def __and__(self, other):
        if not isinstance(other, self.__class__):
            return NotImplemented
        return self.__class__((self._value_ & other._value_))

    def __xor__(self, other):
        if not isinstance(other, self.__class__):
            return NotImplemented
        return self.__class__((self._value_ ^ other._value_))

    def __invert__(self):
        if self._inverted_ is None:
            if self._boundary_ is KEEP:
                self._inverted_ = self.__class__((~self._value_))
            else:
                self._inverted_ = self.__class__((self._flag_mask_ ^ self._value_))
            self._inverted_._inverted_ = self
        return self._inverted_


class IntFlag(int, Flag, boundary=EJECT):
    "\n    Support for integer-based Flags\n    "

    def __or__(self, other):
        if isinstance(other, self.__class__):
            other = other._value_
        elif isinstance(other, int):
            other = other
        else:
            return NotImplemented
        value = self._value_
        return self.__class__((value | other))

    def __and__(self, other):
        if isinstance(other, self.__class__):
            other = other._value_
        elif isinstance(other, int):
            other = other
        else:
            return NotImplemented
        value = self._value_
        return self.__class__((value & other))

    def __xor__(self, other):
        if isinstance(other, self.__class__):
            other = other._value_
        elif isinstance(other, int):
            other = other
        else:
            return NotImplemented
        value = self._value_
        return self.__class__((value ^ other))

    __ror__ = __or__
    __rand__ = __and__
    __rxor__ = __xor__
    __invert__ = Flag.__invert__


def _high_bit(value):
    "\n    returns index of highest bit, or -1 if value is zero or negative\n    "
    return value.bit_length() - 1


def unique(enumeration):
    "\n    Class decorator for enumerations ensuring unique member values.\n    "
    duplicates = []
    for (name, member) in enumeration.__members__.items():
        if name != member.name:
            duplicates.append((name, member.name))
    if duplicates:
        alias_details = ", ".join(
            [("%s -> %s" % (alias, name)) for (alias, name) in duplicates]
        )
        raise ValueError(
            ("duplicate values found in %r: %s" % (enumeration, alias_details))
        )
    return enumeration


def _power_of_two(value):
    if value < 1:
        return False
    return value == (2 ** _high_bit(value))


def global_enum_repr(self):
    return "%s.%s" % (self.__class__.__module__, self._name_)


def global_flag_repr(self):
    module = self.__class__.__module__
    cls_name = self.__class__.__name__
    if self._name_ is None:
        return "%x" % (module, cls_name, self._value_)
    if _is_single_bit(self):
        return "%s.%s" % (module, self._name_)
    if self._boundary_ is not FlagBoundary.KEEP:
        return module + module.join(self.name.split("|"))
    else:
        name = []
        for n in self._name_.split("|"):
            if n.startswith("0"):
                name.append(n)
            else:
                name.append(("%s.%s" % (module, n)))
        return "|".join(name)


def global_enum(cls):
    "\n    decorator that makes the repr() of an enum member reference its module\n    instead of its class; also exports all members to the enum's module's\n    global namespace\n    "
    if issubclass(cls, Flag):
        cls.__repr__ = global_flag_repr
    else:
        cls.__repr__ = global_enum_repr
    sys.modules[cls.__module__].__dict__.update(cls.__members__)
    return cls


def _simple_enum(etype=Enum, *, boundary=None, use_args=None):
    "\n    Class decorator that converts a normal class into an :class:`Enum`.  No\n    safety checks are done, and some advanced behavior (such as\n    :func:`__init_subclass__`) is not available.  Enum creation can be faster\n    using :func:`simple_enum`.\n\n        >>> from enum import Enum, _simple_enum\n        >>> @_simple_enum(Enum)\n        ... class Color:\n        ...     RED = auto()\n        ...     GREEN = auto()\n        ...     BLUE = auto()\n        >>> Color\n        <enum 'Color'>\n    "

    def convert_class(cls):
        nonlocal use_args
        cls_name = cls.__name__
        if use_args is None:
            use_args = etype._use_args_
        __new__ = cls.__dict__.get("__new__")
        if __new__ is not None:
            new_member = __new__.__func__
        else:
            new_member = etype._member_type_.__new__
        attrs = {}
        body = {}
        if __new__ is not None:
            body["__new_member__"] = new_member
        body["_new_member_"] = new_member
        body["_use_args_"] = use_args
        body["_generate_next_value_"] = gnv = etype._generate_next_value_
        body["_member_names_"] = member_names = []
        body["_member_map_"] = member_map = {}
        body["_value2member_map_"] = value2member_map = {}
        body["_member_type_"] = member_type = etype._member_type_
        if issubclass(etype, Flag):
            body["_boundary_"] = boundary or etype._boundary_
            body["_flag_mask_"] = None
            body["_all_bits_"] = None
            body["_inverted_"] = None
        for (name, obj) in cls.__dict__.items():
            if name in ("__dict__", "__weakref__"):
                continue
            if (
                _is_dunder(name)
                or _is_private(cls_name, name)
                or _is_sunder(name)
                or _is_descriptor(obj)
            ):
                body[name] = obj
            else:
                attrs[name] = obj
        if cls.__dict__.get("__doc__") is None:
            body["__doc__"] = "An enumeration."
        enum_class = type(cls_name, (etype,), body, boundary=boundary, _simple=True)
        for name in ("__repr__", "__str__", "__format__", "__reduce_ex__"):
            if name in body:
                continue
            class_method = getattr(enum_class, name)
            obj_method = getattr(member_type, name, None)
            enum_method = getattr(etype, name, None)
            if (obj_method is not None) and (obj_method is class_method):
                setattr(enum_class, name, enum_method)
        gnv_last_values = []
        if issubclass(enum_class, Flag):
            single_bits = multi_bits = 0
            for (name, value) in attrs.items():
                if isinstance(value, auto) and (auto.value is _auto_null):
                    value = gnv(name, 1, len(member_names), gnv_last_values)
                if value in value2member_map:
                    redirect = property()
                    redirect.__set_name__(enum_class, name)
                    setattr(enum_class, name, redirect)
                    member_map[name] = value2member_map[value]
                else:
                    if use_args:
                        if not isinstance(value, tuple):
                            value = (value,)
                        member = new_member(enum_class, *value)
                        value = value[0]
                    else:
                        member = new_member(enum_class)
                    if __new__ is None:
                        member._value_ = value
                    member._name_ = name
                    member.__objclass__ = enum_class
                    member.__init__(value)
                    redirect = property()
                    redirect.__set_name__(enum_class, name)
                    setattr(enum_class, name, redirect)
                    member_map[name] = member
                    member._sort_order_ = len(member_names)
                    value2member_map[value] = member
                    if _is_single_bit(value):
                        member_names.append(name)
                        single_bits |= value
                    else:
                        multi_bits |= value
                    gnv_last_values.append(value)
            enum_class._flag_mask_ = single_bits
            enum_class._all_bits_ = (2 ** (single_bits | multi_bits).bit_length()) - 1
            member_list = [m._value_ for m in enum_class]
            if member_list != sorted(member_list):
                enum_class._iter_member_ = enum_class._iter_member_by_def_
        else:
            for (name, value) in attrs.items():
                if isinstance(value, auto):
                    if value.value is _auto_null:
                        value.value = gnv(name, 1, len(member_names), gnv_last_values)
                    value = value.value
                if value in value2member_map:
                    redirect = property()
                    redirect.__set_name__(enum_class, name)
                    setattr(enum_class, name, redirect)
                    member_map[name] = value2member_map[value]
                else:
                    if use_args:
                        if not isinstance(value, tuple):
                            value = (value,)
                        member = new_member(enum_class, *value)
                        value = value[0]
                    else:
                        member = new_member(enum_class)
                    if __new__ is None:
                        member._value_ = value
                    member._name_ = name
                    member.__objclass__ = enum_class
                    member.__init__(value)
                    member._sort_order_ = len(member_names)
                    redirect = property()
                    redirect.__set_name__(enum_class, name)
                    setattr(enum_class, name, redirect)
                    member_map[name] = member
                    value2member_map[value] = member
                    member_names.append(name)
                    gnv_last_values.append(value)
        if "__new__" in body:
            enum_class.__new_member__ = enum_class.__new__
        enum_class.__new__ = Enum.__new__
        return enum_class

    return convert_class


def _test_simple_enum(checked_enum, simple_enum):
    "\n    A function that can be used to test an enum created with :func:`_simple_enum`\n    against the version created by subclassing :class:`Enum`::\n\n        >>> from enum import Enum, _simple_enum, _test_simple_enum\n        >>> @_simple_enum(Enum)\n        ... class Color:\n        ...     RED = auto()\n        ...     GREEN = auto()\n        ...     BLUE = auto()\n        >>> class CheckedColor(Enum):\n        ...     RED = auto()\n        ...     GREEN = auto()\n        ...     BLUE = auto()\n        >>> _test_simple_enum(CheckedColor, Color)\n\n    If differences are found, a :exc:`TypeError` is raised.\n    "
    failed = []
    if checked_enum.__dict__ != simple_enum.__dict__:
        checked_dict = checked_enum.__dict__
        checked_keys = list(checked_dict.keys())
        simple_dict = simple_enum.__dict__
        simple_keys = list(simple_dict.keys())
        member_names = set(
            (
                list(checked_enum._member_map_.keys())
                + list(simple_enum._member_map_.keys())
            )
        )
        for key in set((checked_keys + simple_keys)):
            if key in ("__module__", "_member_map_", "_value2member_map_"):
                continue
            elif key in member_names:
                continue
            elif key not in simple_keys:
                failed.append(("missing key: %r" % (key,)))
            elif key not in checked_keys:
                failed.append(("extra key:   %r" % (key,)))
            else:
                checked_value = checked_dict[key]
                simple_value = simple_dict[key]
                if callable(checked_value):
                    continue
                if key == "__doc__":
                    compressed_checked_value = checked_value.replace(" ", "").replace(
                        "\t", ""
                    )
                    compressed_simple_value = simple_value.replace(" ", "").replace(
                        "\t", ""
                    )
                    if compressed_checked_value != compressed_simple_value:
                        failed.append(
                            (
                                "%r:\n         %s\n         %s"
                                % (
                                    key,
                                    ("checked -> %r" % (checked_value,)),
                                    ("simple  -> %r" % (simple_value,)),
                                )
                            )
                        )
                elif checked_value != simple_value:
                    failed.append(
                        (
                            "%r:\n         %s\n         %s"
                            % (
                                key,
                                ("checked -> %r" % (checked_value,)),
                                ("simple  -> %r" % (simple_value,)),
                            )
                        )
                    )
        failed.sort()
        for name in member_names:
            failed_member = []
            if name not in simple_keys:
                failed.append(("missing member from simple enum: %r" % name))
            elif name not in checked_keys:
                failed.append(("extra member in simple enum: %r" % name))
            else:
                checked_member_dict = checked_enum[name].__dict__
                checked_member_keys = list(checked_member_dict.keys())
                simple_member_dict = simple_enum[name].__dict__
                simple_member_keys = list(simple_member_dict.keys())
                for key in set((checked_member_keys + simple_member_keys)):
                    if key in ("__module__", "__objclass__"):
                        continue
                    elif key not in simple_member_keys:
                        failed_member.append(
                            (
                                "missing key %r not in the simple enum member %r"
                                % (key, name)
                            )
                        )
                    elif key not in checked_member_keys:
                        failed_member.append(
                            ("extra key %r in simple enum member %r" % (key, name))
                        )
                    else:
                        checked_value = checked_member_dict[key]
                        simple_value = simple_member_dict[key]
                        if checked_value != simple_value:
                            failed_member.append(
                                (
                                    "%r:\n         %s\n         %s"
                                    % (
                                        key,
                                        ("checked member -> %r" % (checked_value,)),
                                        ("simple member  -> %r" % (simple_value,)),
                                    )
                                )
                            )
            if failed_member:
                failed.append(
                    (
                        "%r member mismatch:\n      %s"
                        % (name, "\n      ".join(failed_member))
                    )
                )
        for method in (
            "__str__",
            "__repr__",
            "__reduce_ex__",
            "__format__",
            "__getnewargs_ex__",
            "__getnewargs__",
            "__reduce_ex__",
            "__reduce__",
        ):
            if (method in simple_keys) and (method in checked_keys):
                continue
            elif (method not in simple_keys) and (method not in checked_keys):
                checked_method = getattr(checked_enum, method, None)
                simple_method = getattr(simple_enum, method, None)
                if hasattr(checked_method, "__func__"):
                    checked_method = checked_method.__func__
                    simple_method = simple_method.__func__
                if checked_method != simple_method:
                    failed.append(
                        (
                            "%r:  %-30s %s"
                            % (
                                method,
                                ("checked -> %r" % (checked_method,)),
                                ("simple -> %r" % (simple_method,)),
                            )
                        )
                    )
            else:
                pass
    if failed:
        raise TypeError(("enum mismatch:\n   %s" % "\n   ".join(failed)))


def _old_convert_(etype, name, module, filter, source=None, *, boundary=None):
    "\n    Create a new Enum subclass that replaces a collection of global constants\n    "
    module_globals = sys.modules[module].__dict__
    if source:
        source = source.__dict__
    else:
        source = module_globals
    members = [(name, value) for (name, value) in source.items() if filter(name)]
    try:
        members.sort(key=(lambda t: (t[1], t[0])))
    except TypeError:
        members.sort(key=(lambda t: t[0]))
    cls = etype(name, members, module=module, boundary=(boundary or KEEP))
    cls.__reduce_ex__ = _reduce_ex_by_name
    cls.__repr__ = global_enum_repr
    return cls
