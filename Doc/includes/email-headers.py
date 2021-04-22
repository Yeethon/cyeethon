from email.parser import BytesParser, Parser
from email.policy import default

headers = Parser(policy=default).parsestr(
    "From: Foo Bar <user@example.com>\nTo: <someone_else@example.com>\nSubject: Test message\n\nBody would go here\n"
)
print("To: {}".format(headers["to"]))
print("From: {}".format(headers["from"]))
print("Subject: {}".format(headers["subject"]))
print("Recipient username: {}".format(headers["to"].addresses[0].username))
print("Sender name: {}".format(headers["from"].addresses[0].display_name))
