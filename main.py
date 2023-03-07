from collections import namedtuple
from email.header import decode_header
from email.parser import BytesParser

from aiosmtpd.controller import Controller
from flask import Flask

Email = namedtuple("Email", ["subject", "from_address", "to_addresses", "body"])


class CustomHandler:
    def __init__(self):
        self.emails = []

    async def handle_DATA(self, server, session, envelope):
        mail_from = envelope.mail_from
        rcpt_tos = envelope.rcpt_tos
        data = envelope.content  # type: bytes
        # Process message data...
        msg = BytesParser().parsebytes(data)

        # Find the text/html version
        if msg.is_multipart():
            body = "?"
            for tgt_mime in ["text/plain", "text/html"]:
                for part in msg.walk():
                    ctype = part.get_content_type()
                    cdispo = str(part.get('Content-Disposition'))

                    # skip any text/plain (txt) attachments
                    if ctype == tgt_mime and 'attachment' not in cdispo:
                        body = part.get_payload(decode=True).decode()  # decode
                        break
        # not multipart - i.e. plain text, no attachments, keeping fingers crossed
        else:
            body = msg.get_payload(decode=True).decode()

        subject_raw, subject_encoding = decode_header(msg.get("Subject"))[0]
        if subject_encoding is None:
            subject = subject_raw
        else:
            subject = subject_raw.decode()
        self.emails.append(Email(
            subject,
            mail_from,
            rcpt_tos,
            body
        ))

        return '250 OK'

    def reset(self):
        self.emails = []


handler = CustomHandler()
app = Flask(__name__)


@app.route('/mail')
def mail():
    return {
        "mailItems": [
            mail._asdict()
            for mail in handler.emails
        ]
    }


@app.route('/reset')
def say_hello():
    handler.reset()
    return 'OK'


if __name__ == '__main__':
    controller = Controller(handler, hostname='127.0.0.1', port=10025)
    # Run the event loop in a separate thread.
    controller.start()
    app.run("localhost", 8085)
    # Wait for the user to press Return.
    input('SMTP server running. Press Return to stop server and exit.')
    controller.stop()
