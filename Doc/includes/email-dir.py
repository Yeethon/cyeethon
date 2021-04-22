"Send the contents of a directory as a MIME message."
import os
import smtplib
import mimetypes
from argparse import ArgumentParser
from email.message import EmailMessage
from email.policy import SMTP


def main():
    parser = ArgumentParser(
        description="Send the contents of a directory as a MIME message.\nUnless the -o option is given, the email is sent by forwarding to your local\nSMTP server, which then does the normal delivery process.  Your local machine\nmust be running an SMTP server.\n"
    )
    parser.add_argument(
        "-d",
        "--directory",
        help="Mail the contents of the specified directory,\n                        otherwise use the current directory.  Only the regular\n                        files in the directory are sent, and we don't recurse to\n                        subdirectories.",
    )
    parser.add_argument(
        "-o",
        "--output",
        metavar="FILE",
        help="Print the composed message to FILE instead of\n                        sending the message to the SMTP server.",
    )
    parser.add_argument(
        "-s", "--sender", required=True, help="The value of the From: header (required)"
    )
    parser.add_argument(
        "-r",
        "--recipient",
        required=True,
        action="append",
        metavar="RECIPIENT",
        default=[],
        dest="recipients",
        help="A To: header value (at least one required)",
    )
    args = parser.parse_args()
    directory = args.directory
    if not directory:
        directory = "."
    msg = EmailMessage()
    msg["Subject"] = f"Contents of directory {os.path.abspath(directory)}"
    msg["To"] = ", ".join(args.recipients)
    msg["From"] = args.sender
    msg.preamble = "You will not see this in a MIME-aware mail reader.\n"
    for filename in os.listdir(directory):
        path = os.path.join(directory, filename)
        if not os.path.isfile(path):
            continue
        (ctype, encoding) = mimetypes.guess_type(path)
        if (ctype is None) or (encoding is not None):
            ctype = "application/octet-stream"
        (maintype, subtype) = ctype.split("/", 1)
        with open(path, "rb") as fp:
            msg.add_attachment(
                fp.read(), maintype=maintype, subtype=subtype, filename=filename
            )
    if args.output:
        with open(args.output, "wb") as fp:
            fp.write(msg.as_bytes(policy=SMTP))
    else:
        with smtplib.SMTP("localhost") as s:
            s.send_message(msg)


if __name__ == "__main__":
    main()
