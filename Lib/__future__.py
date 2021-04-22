'Record of phased-in incompatible language changes.\n\nEach line is of the form:\n\n    FeatureName = "_Feature(" OptionalRelease "," MandatoryRelease ","\n                              CompilerFlag ")"\n\nwhere, normally, OptionalRelease < MandatoryRelease, and both are 5-tuples\nof the same form as sys.version_info:\n\n    (PY_MAJOR_VERSION, # the 2 in 2.1.0a3; an int\n     PY_MINOR_VERSION, # the 1; an int\n     PY_MICRO_VERSION, # the 0; an int\n     PY_RELEASE_LEVEL, # "alpha", "beta", "candidate" or "final"; string\n     PY_RELEASE_SERIAL # the 3; an int\n    )\n\nOptionalRelease records the first release in which\n\n    from __future__ import FeatureName\n\nwas accepted.\n\nIn the case of MandatoryReleases that have not yet occurred,\nMandatoryRelease predicts the release in which the feature will become part\nof the language.\n\nElse MandatoryRelease records when the feature became part of the language;\nin releases at or after that, modules no longer need\n\n    from __future__ import FeatureName\n\nto use the feature in question, but may continue to use such imports.\n\nMandatoryRelease may also be None, meaning that a planned feature got\ndropped.\n\nInstances of class _Feature have two corresponding methods,\n.getOptionalRelease() and .getMandatoryRelease().\n\nCompilerFlag is the (bitfield) flag that should be passed in the fourth\nargument to the builtin function compile() to enable the feature in\ndynamically compiled code.  This flag is stored in the .compiler_flag\nattribute on _Future instances.  These values must match the appropriate\n#defines of CO_xxx flags in Include/cpython/compile.h.\n\nNo feature line is ever to be deleted from this file.\n'
all_feature_names = [
    "nested_scopes",
    "generators",
    "division",
    "absolute_import",
    "with_statement",
    "print_function",
    "unicode_literals",
    "barry_as_FLUFL",
    "generator_stop",
    "annotations",
]
__all__ = ["all_feature_names"] + all_feature_names
CO_NESTED = 16
CO_GENERATOR_ALLOWED = 0
CO_FUTURE_DIVISION = 131072
CO_FUTURE_ABSOLUTE_IMPORT = 262144
CO_FUTURE_WITH_STATEMENT = 524288
CO_FUTURE_PRINT_FUNCTION = 1048576
CO_FUTURE_UNICODE_LITERALS = 2097152
CO_FUTURE_BARRY_AS_BDFL = 4194304
CO_FUTURE_GENERATOR_STOP = 8388608
CO_FUTURE_ANNOTATIONS = 16777216


class _Feature:
    def __init__(self, optionalRelease, mandatoryRelease, compiler_flag):
        self.optional = optionalRelease
        self.mandatory = mandatoryRelease
        self.compiler_flag = compiler_flag

    def getOptionalRelease(self):
        "Return first release in which this feature was recognized.\n\n        This is a 5-tuple, of the same form as sys.version_info.\n        "
        return self.optional

    def getMandatoryRelease(self):
        "Return release in which this feature will become mandatory.\n\n        This is a 5-tuple, of the same form as sys.version_info, or, if\n        the feature was dropped, is None.\n        "
        return self.mandatory

    def __repr__(self):
        return "_Feature" + repr((self.optional, self.mandatory, self.compiler_flag))


nested_scopes = _Feature((2, 1, 0, "beta", 1), (2, 2, 0, "alpha", 0), CO_NESTED)
generators = _Feature(
    (2, 2, 0, "alpha", 1), (2, 3, 0, "final", 0), CO_GENERATOR_ALLOWED
)
division = _Feature((2, 2, 0, "alpha", 2), (3, 0, 0, "alpha", 0), CO_FUTURE_DIVISION)
absolute_import = _Feature(
    (2, 5, 0, "alpha", 1), (3, 0, 0, "alpha", 0), CO_FUTURE_ABSOLUTE_IMPORT
)
with_statement = _Feature(
    (2, 5, 0, "alpha", 1), (2, 6, 0, "alpha", 0), CO_FUTURE_WITH_STATEMENT
)
print_function = _Feature(
    (2, 6, 0, "alpha", 2), (3, 0, 0, "alpha", 0), CO_FUTURE_PRINT_FUNCTION
)
unicode_literals = _Feature(
    (2, 6, 0, "alpha", 2), (3, 0, 0, "alpha", 0), CO_FUTURE_UNICODE_LITERALS
)
barry_as_FLUFL = _Feature(
    (3, 1, 0, "alpha", 2), (4, 0, 0, "alpha", 0), CO_FUTURE_BARRY_AS_BDFL
)
generator_stop = _Feature(
    (3, 5, 0, "beta", 1), (3, 7, 0, "alpha", 0), CO_FUTURE_GENERATOR_STOP
)
annotations = _Feature(
    (3, 7, 0, "beta", 1), (3, 10, 0, "alpha", 0), CO_FUTURE_ANNOTATIONS
)
