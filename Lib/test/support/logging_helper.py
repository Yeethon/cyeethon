import logging.handlers


class TestHandler(logging.handlers.BufferingHandler):
    def __init__(self, matcher):
        logging.handlers.BufferingHandler.__init__(self, 0)
        self.matcher = matcher

    def shouldFlush(self):
        return False

    def emit(self, record):
        self.format(record)
        self.buffer.append(record.__dict__)

    def matches(self, **kwargs):
        "\n        Look for a saved dict whose keys/values match the supplied arguments.\n        "
        result = False
        for d in self.buffer:
            if self.matcher.matches(d, **kwargs):
                result = True
                break
        return result
