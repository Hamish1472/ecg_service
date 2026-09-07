import os
import mimetypes
import smtplib
from email.message import EmailMessage
from ecg_service.config import EMAIL_SENDER, EMAIL_PASSWORD, SMTP_SERVER, SMTP_PORT

MAX_ATTACHMENT_SIZE_MB = 25
MAX_ATTACHMENT_SIZE = MAX_ATTACHMENT_SIZE_MB * 1024 * 1024  # bytes


def send_email(
    recipient: str,
    subject: str,
    body: str,
    attachment_path=None,
    link: str | None = None,
    link_label: str | None = None,
):
    """
    Sends an email with an optional attachment and/or an optional hyperlinked download link.

    Args:
        recipient (str): Email recipient.
        subject (str): Email subject line.
        body (str): Email body text. If `link` is given, this should contain the raw
            URL somewhere in the text (used as the plain-text fallback and as the
            substring replaced with a hyperlink in the HTML version).
        attachment_path (str, optional): Path to attachment file.
        link (str, optional): URL to hyperlink in the HTML version of the email.
        link_label (str, optional): Display text for the hyperlink. Required if `link` is given.
    """
    msg = EmailMessage()
    msg["From"] = EMAIL_SENDER
    msg["To"] = recipient
    msg["Subject"] = subject
    msg.set_content(body)

    if link:
        if not link_label:
            raise ValueError("link_label is required when link is provided.")
        html_body = body.replace("\n", "<br>").replace(
            link, f'<a href="{link}">{link_label}</a>'
        )
        msg.add_alternative(
            f"<html><body><p>{html_body}</p></body></html>", subtype="html"
        )

    if attachment_path:
        attachment_size = os.path.getsize(attachment_path)
        if attachment_size > MAX_ATTACHMENT_SIZE:
            raise ValueError(
                f"Attachment too large ({attachment_size / (1024 * 1024):.2f} MB). "
                f"Maximum allowed is {MAX_ATTACHMENT_SIZE_MB} MB."
            )

        ctype, encoding = mimetypes.guess_type(attachment_path)
        if ctype is None or encoding is not None:
            ctype = "application/octet-stream"
        maintype, subtype = ctype.split("/", 1)

        with open(attachment_path, "rb") as f:
            msg.add_attachment(
                f.read(),
                maintype=maintype,
                subtype=subtype,
                filename=os.path.basename(attachment_path),
            )

    with smtplib.SMTP(SMTP_SERVER, SMTP_PORT) as smtp:
        smtp.starttls()
        smtp.login(EMAIL_SENDER, EMAIL_PASSWORD)
        smtp.send_message(msg)


if __name__ == "__main__":
    send_email(EMAIL_SENDER, "test", "body")
