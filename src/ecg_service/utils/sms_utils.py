from vonage import Auth, Vonage
from vonage_sms import SmsMessage, SmsResponse
from ecg_service.config import VONAGE_API_KEY, VONAGE_API_SECRET, EMAIL_SENDER


def send_sms(phone_number: str, password: str, sender_id: str = "Cardiologic"):
    """
    Sends a password via SMS using Vonage.

    Args:
        phone_number (str): Recipient phone number in E.164 format.
        password (str): Password to send.
        sender_id (str): SMS sender ID (default: 'Cardiologic').
    """
    client = Vonage(Auth(api_key=VONAGE_API_KEY, api_secret=VONAGE_API_SECRET))

    message = SmsMessage(
        to=phone_number,
        from_=sender_id,
        text=(
            f"Do Not Reply\n\nPassword to PDF:\n\n{password}\n\n"
            f"Please check your spam folder for an email from {EMAIL_SENDER} "
            f"if you have not received the PDF"
        ),
    )

    response: SmsResponse = client.sms.send(message)
    # Log or return response if needed
    return response
