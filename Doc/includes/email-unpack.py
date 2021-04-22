"Unpack a MIME message into a directory of files."
import os
import email
import mimetypes
from email.policy import default
from argparse import ArgumentParser


def main():
    parser = ArgumentParser(
        description="Unpack a MIME message into a directory of files.\n"
    )
    parser.add_argument(
        "-d",
        "--directory",
        required=True,
        help="Unpack the MIME message into the named\n                        directory, which will be created if it doesn't already\n                        exist.",
    )
    parser.add_argument("msgfile")
    args = parser.parse_args()
    with open(args.msgfile, "rb") as fp:
        msg = email.message_from_binary_file(fp, policy=default)
    try:
        os.mkdir(args.directory)
    except FileExistsError:
        pass
    counter = 1
    for part in msg.walk():
        if part.get_content_maintype() == "multipart":
            continue
        filename = part.get_filename()
        if not filename:
            ext = mimetypes.guess_extension(part.get_content_type())
            if not ext:
                ext = ".bin"
            filename = f"part-{counter:03d}{ext}"
        counter += 1
        with open(os.path.join(args.directory, filename), "wb") as fp:
            fp.write(part.get_payload(decode=True))


if __name__ == "__main__":
    main()
