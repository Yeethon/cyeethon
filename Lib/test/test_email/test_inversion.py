"Test the parser and generator are inverses.\n\nNote that this is only strictly true if we are parsing RFC valid messages and\nproducing RFC valid messages.\n"
import io
import unittest
from email import policy, message_from_bytes
from email.message import EmailMessage
from email.generator import BytesGenerator
from test.test_email import TestEmailBase, parameterize


def dedent(bstr):
    lines = bstr.splitlines()
    if not lines[0].strip():
        raise ValueError("First line must contain text")
    stripamt = len(lines[0]) - len(lines[0].lstrip())
    return b"\r\n".join(
        [(x[stripamt:] if (len(x) >= stripamt) else b"") for x in lines]
    )


@parameterize
class TestInversion(TestEmailBase):
    policy = policy.default
    message = EmailMessage

    def msg_as_input(self, msg):
        m = message_from_bytes(msg, policy=policy.SMTP)
        b = io.BytesIO()
        g = BytesGenerator(b)
        g.flatten(m)
        self.assertEqual(b.getvalue(), msg)

    msg_params = {
        "header_with_one_space_body": (
            dedent(
                b"            From: abc@xyz.com\n            X-Status: \n            Subject: test\n\n            foo\n            "
            ),
        ),
        "header_with_invalid_date": (
            dedent(
                b"            Date: Tue, 06 Jun 2017 27:39:33 +0600\n            From: abc@xyz.com\n            Subject: timezones\n\n            How do they work even?\n            "
            ),
        ),
    }
    payload_params = {
        "plain_text": dict(payload=("This is a test\n" * 20)),
        "base64_text": dict(payload=((("xy a" * 40) + "\n") * 5), cte="base64"),
        "qp_text": dict(payload=((("xy a" * 40) + "\n") * 5), cte="quoted-printable"),
    }

    def payload_as_body(self, payload, **kw):
        msg = self._make_message()
        msg["From"] = "foo"
        msg["To"] = "bar"
        msg["Subject"] = "payload round trip test"
        msg.set_content(payload, **kw)
        b = bytes(msg)
        msg2 = message_from_bytes(b, policy=self.policy)
        self.assertEqual(bytes(msg2), b)
        self.assertEqual(msg2.get_content(), payload)


if __name__ == "__main__":
    unittest.main()
