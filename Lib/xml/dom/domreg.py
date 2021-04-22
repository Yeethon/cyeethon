"Registration facilities for DOM. This module should not be used\ndirectly. Instead, the functions getDOMImplementation and\nregisterDOMImplementation should be imported from xml.dom."
import sys

well_known_implementations = {
    "minidom": "xml.dom.minidom",
    "4DOM": "xml.dom.DOMImplementation",
}
registered = {}


def registerDOMImplementation(name, factory):
    "registerDOMImplementation(name, factory)\n\n    Register the factory function with the name. The factory function\n    should return an object which implements the DOMImplementation\n    interface. The factory function can either return the same object,\n    or a new one (e.g. if that implementation supports some\n    customization)."
    registered[name] = factory


def _good_enough(dom, features):
    "_good_enough(dom, features) -> Return 1 if the dom offers the features"
    for (f, v) in features:
        if not dom.hasFeature(f, v):
            return 0
    return 1


def getDOMImplementation(name=None, features=()):
    "getDOMImplementation(name = None, features = ()) -> DOM implementation.\n\n    Return a suitable DOM implementation. The name is either\n    well-known, the module name of a DOM implementation, or None. If\n    it is not None, imports the corresponding module and returns\n    DOMImplementation object if the import succeeds.\n\n    If name is not given, consider the available implementations to\n    find one with the required feature set. If no implementation can\n    be found, raise an ImportError. The features list must be a sequence\n    of (feature, version) pairs which are passed to hasFeature."
    import os

    creator = None
    mod = well_known_implementations.get(name)
    if mod:
        mod = __import__(mod, {}, {}, ["getDOMImplementation"])
        return mod.getDOMImplementation()
    elif name:
        return registered[name]()
    elif (not sys.flags.ignore_environment) and ("PYTHON_DOM" in os.environ):
        return getDOMImplementation(name=os.environ["PYTHON_DOM"])
    if isinstance(features, str):
        features = _parse_feature_string(features)
    for creator in registered.values():
        dom = creator()
        if _good_enough(dom, features):
            return dom
    for creator in well_known_implementations.keys():
        try:
            dom = getDOMImplementation(name=creator)
        except Exception:
            continue
        if _good_enough(dom, features):
            return dom
    raise ImportError("no suitable DOM implementation found")


def _parse_feature_string(s):
    features = []
    parts = s.split()
    i = 0
    length = len(parts)
    while i < length:
        feature = parts[i]
        if feature[0] in "0123456789":
            raise ValueError(("bad feature name: %r" % (feature,)))
        i = i + 1
        version = None
        if i < length:
            v = parts[i]
            if v[0] in "0123456789":
                i = i + 1
                version = v
        features.append((feature, version))
    return tuple(features)
