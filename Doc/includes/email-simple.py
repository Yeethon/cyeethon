import smtplib
from email.message import EmailMessage

with open(textfile) as fp:
    msg = EmailMessage()
    msg.set_content(fp.read())
msg["Subject"] = f"The contents of {textfile}"
msg["From"] = me
msg["To"] = you
s = smtplib.SMTP("localhost")
s.send_message(msg)
s.quit()
