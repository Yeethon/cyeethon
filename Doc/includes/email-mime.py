import smtplib
import imghdr
from email.message import EmailMessage

msg = EmailMessage()
msg["Subject"] = "Our family reunion"
msg["From"] = me
msg["To"] = ", ".join(family)
msg.preamble = "You will not see this in a MIME-aware mail reader.\n"
for file in pngfiles:
    with open(file, "rb") as fp:
        img_data = fp.read()
    msg.add_attachment(img_data, maintype="image", subtype=imghdr.what(None, img_data))
with smtplib.SMTP("localhost") as s:
    s.send_message(msg)
