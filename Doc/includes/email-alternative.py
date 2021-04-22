import smtplib
from email.message import EmailMessage
from email.headerregistry import Address
from email.utils import make_msgid

msg = EmailMessage()
msg["Subject"] = "Ayons asperges pour le déjeuner"
msg["From"] = Address("Pepé Le Pew", "pepe", "example.com")
msg["To"] = (
    Address("Penelope Pussycat", "penelope", "example.com"),
    Address("Fabrette Pussycat", "fabrette", "example.com"),
)
msg.set_content(
    "Salut!\n\nCela ressemble à un excellent recipie[1] déjeuner.\n\n[1] http://www.yummly.com/recipe/Roasted-Asparagus-Epicurious-203718\n\n--Pepé\n"
)
asparagus_cid = make_msgid()
msg.add_alternative(
    '<html>\n  <head></head>\n  <body>\n    <p>Salut!</p>\n    <p>Cela ressemble à un excellent\n        <a href="http://www.yummly.com/recipe/Roasted-Asparagus-Epicurious-203718">\n            recipie\n        </a> déjeuner.\n    </p>\n    <img src="cid:{asparagus_cid}" />\n  </body>\n</html>\n'.format(
        asparagus_cid=asparagus_cid[1:(-1)]
    ),
    subtype="html",
)
with open("roasted-asparagus.jpg", "rb") as img:
    msg.get_payload()[1].add_related(img.read(), "image", "jpeg", cid=asparagus_cid)
with open("outgoing.msg", "wb") as f:
    f.write(bytes(msg))
with smtplib.SMTP("localhost") as s:
    s.send_message(msg)
