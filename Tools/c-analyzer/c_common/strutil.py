import logging

logger = logging.getLogger(__name__)


def unrepr(value):
    raise NotImplementedError


def parse_entries(entries, *, ignoresep=None):
    for entry in entries:
        if ignoresep and (ignoresep in entry):
            subentries = [entry]
        else:
            subentries = entry.strip().replace(",", " ").split()
        for item in subentries:
            if item.startswith("+"):
                filename = item[1:]
                try:
                    infile = open(filename)
                except FileNotFoundError:
                    logger.debug(f"ignored in parse_entries(): +{filename}")
                    return
                with infile:
                    lines = infile.read().splitlines()
                for line in _iter_significant_lines(lines):
                    (yield (line, filename))
            else:
                (yield (item, None))


def _iter_significant_lines(lines):
    for line in lines:
        line = line.partition("#")[0]
        if not line.strip():
            continue
        (yield line)
