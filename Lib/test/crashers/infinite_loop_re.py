import re

starttag = re.compile(
    "<[a-zA-Z][-_.:a-zA-Z0-9]*\\s*(\\s*([a-zA-Z_][-:.a-zA-Z_0-9]*)(\\s*=\\s*(\\'[^\\']*\\'|\"[^\"]*\"|[-a-zA-Z0-9./,:;+*%?!&$\\(\\)_#=~@][][\\-a-zA-Z0-9./,:;+*%?!&$\\(\\)_#=~\\'\"@]*(?=[\\s>/<])))?)*\\s*/?\\s*(?=[<>])"
)
if __name__ == "__main__":
    foo = '<table cellspacing="0" cellpadding="0" style="border-collapse'
    starttag.match(foo)
