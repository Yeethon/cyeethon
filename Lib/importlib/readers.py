import collections
import zipfile
import pathlib
from . import abc


def remove_duplicates(items):
    return iter(collections.OrderedDict.fromkeys(items))


class FileReader(abc.TraversableResources):
    def __init__(self, loader):
        self.path = pathlib.Path(loader.path).parent

    def resource_path(self, resource):
        "\n        Return the file system path to prevent\n        `resources.path()` from creating a temporary\n        copy.\n        "
        return str(self.path.joinpath(resource))

    def files(self):
        return self.path


class ZipReader(abc.TraversableResources):
    def __init__(self, loader, module):
        (_, _, name) = module.rpartition(".")
        self.prefix = (loader.prefix.replace("\\", "/") + name) + "/"
        self.archive = loader.archive

    def open_resource(self, resource):
        try:
            return super().open_resource(resource)
        except KeyError as exc:
            raise FileNotFoundError(exc.args[0])

    def is_resource(self, path):
        target = self.files().joinpath(path)
        return target.is_file() and target.exists()

    def files(self):
        return zipfile.Path(self.archive, self.prefix)


class MultiplexedPath(abc.Traversable):
    "\n    Given a series of Traversable objects, implement a merged\n    version of the interface across all objects. Useful for\n    namespace packages which may be multihomed at a single\n    name.\n    "

    def __init__(self, *paths):
        self._paths = list(map(pathlib.Path, remove_duplicates(paths)))
        if not self._paths:
            message = "MultiplexedPath must contain at least one path"
            raise FileNotFoundError(message)
        if not all((path.is_dir() for path in self._paths)):
            raise NotADirectoryError("MultiplexedPath only supports directories")

    def iterdir(self):
        visited = []
        for path in self._paths:
            for file in path.iterdir():
                if file.name in visited:
                    continue
                visited.append(file.name)
                (yield file)

    def read_bytes(self):
        raise FileNotFoundError(f"{self} is not a file")

    def read_text(self, *args, **kwargs):
        raise FileNotFoundError(f"{self} is not a file")

    def is_dir(self):
        return True

    def is_file(self):
        return False

    def joinpath(self, child):
        for file in self.iterdir():
            if file.name == child:
                return file
        return self._paths[0] / child

    __truediv__ = joinpath

    def open(self, *args, **kwargs):
        raise FileNotFoundError("{} is not a file".format(self))

    def name(self):
        return self._paths[0].name

    def __repr__(self):
        return "MultiplexedPath({})".format(
            ", ".join(("'{}'".format(path) for path in self._paths))
        )


class NamespaceReader(abc.TraversableResources):
    def __init__(self, namespace_path):
        if "NamespacePath" not in str(namespace_path):
            raise ValueError("Invalid path")
        self.path = MultiplexedPath(*list(namespace_path))

    def resource_path(self, resource):
        "\n        Return the file system path to prevent\n        `resources.path()` from creating a temporary\n        copy.\n        "
        return str(self.path.joinpath(resource))

    def files(self):
        return self.path
