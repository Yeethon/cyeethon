"\nFile generation for catalog signing non-binary contents.\n"
__author__ = "Steve Dower <steve.dower@python.org>"
__version__ = "3.8"
import sys

__all__ = ["PYTHON_CAT_NAME", "PYTHON_CDF_NAME"]


def public(f):
    __all__.append(f.__name__)
    return f


PYTHON_CAT_NAME = "python.cat"
PYTHON_CDF_NAME = "python.cdf"
CATALOG_TEMPLATE = "[CatalogHeader]\nName={target.stem}.cat\nResultDir={target.parent}\nPublicVersion=1\nCatalogVersion=2\nHashAlgorithms=SHA256\nPageHashes=false\nEncodingType=\n\n[CatalogFiles]\n"


def can_sign(file):
    return file.is_file() and file.stat().st_size


@public
def write_catalog(target, files):
    with target.open("w", encoding="utf-8") as cat:
        cat.write(CATALOG_TEMPLATE.format(target=target))
        cat.writelines(
            ("<HASH>{}={}\n".format(n, f) for (n, f) in files if can_sign(f))
        )
