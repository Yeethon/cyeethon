import os
import sys
import tempfile
import mimetypes
import webbrowser
from email import policy
from email.parser import BytesParser
from imaginary import magic_html_parser

with open("outgoing.msg", "rb") as fp:
    msg = BytesParser(policy=policy.default).parse(fp)
print("To:", msg["to"])
print("From:", msg["from"])
print("Subject:", msg["subject"])
simplest = msg.get_body(preferencelist=("plain", "html"))
print()
print("".join(simplest.get_content().splitlines(keepends=True)[:3]))
ans = input("View full message?")
if ans.lower()[0] == "n":
    sys.exit()
richest = msg.get_body()
partfiles = {}
if richest["content-type"].maintype == "text":
    if richest["content-type"].subtype == "plain":
        for line in richest.get_content().splitlines():
            print(line)
        sys.exit()
    elif richest["content-type"].subtype == "html":
        body = richest
    else:
        print("Don't know how to display {}".format(richest.get_content_type()))
        sys.exit()
elif richest["content-type"].content_type == "multipart/related":
    body = richest.get_body(preferencelist="html")
    for part in richest.iter_attachments():
        fn = part.get_filename()
        if fn:
            extension = os.path.splitext(part.get_filename())[1]
        else:
            extension = mimetypes.guess_extension(part.get_content_type())
        with tempfile.NamedTemporaryFile(suffix=extension, delete=False) as f:
            f.write(part.get_content())
            partfiles[part["content-id"][1:(-1)]] = f.name
else:
    print("Don't know how to display {}".format(richest.get_content_type()))
    sys.exit()
with tempfile.NamedTemporaryFile(mode="w", delete=False) as f:
    f.write(magic_html_parser(body.get_content(), partfiles))
webbrowser.open(f.name)
os.remove(f.name)
for fn in partfiles.values():
    os.remove(fn)
