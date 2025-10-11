import csv
import phonenumbers
import pandas as pd


def get_phone_number_from_email(csv_file_path, target_email):
    """
    Looks up a phone number by email from a CSV file.
    Returns E.164 formatted number or 'Not found'.
    """
    with open(csv_file_path, mode="r", newline="", encoding="utf-8") as file:
        reader = csv.DictReader(file)
        for row in reader:
            email = row.get("Email")
            phone = row.get("Phone")

            if (
                email
                and phone
                and email.strip().lower() == target_email.strip().lower()
            ):
                return parse_international_phone_number(phone)

    return "Not found"


def parse_international_phone_number(phone_number):
    """
    Parses and formats a phone number in international format using the phonenumbers library.
    Returns a string in E.164 format like +447368166834.
    """
    if not phone_number.startswith("+"):
        phone_number = "+" + phone_number

    try:
        parsed = phonenumbers.parse(phone_number, None)
        if phonenumbers.is_valid_number(parsed):
            return phonenumbers.format_number(
                parsed, phonenumbers.PhoneNumberFormat.E164
            )
        return "Invalid"
    except phonenumbers.NumberParseException:
        return "Invalid"


def format_consent_csv(input_csv_path: str, output_csv_path: str):
    """
    Converts raw consent CSV to API-ready format.
    Splits names, reformats DOB, and maps columns.
    """
    df = pd.read_csv(input_csv_path)

    # Split Name field
    df["NameParts"] = df["Patient Name"].str.split(",")

    df["FirstName"] = df["NameParts"].apply(
        lambda x: x[0].strip() if isinstance(x, list) and len(x) > 0 else ""
    )
    df["LastName"] = df["NameParts"].apply(
        lambda x: x[-1].strip() if isinstance(x, list) and len(x) > 1 else ""
    )

    df["Birthdate"] = pd.to_datetime(
        df["Patient Date of Birth"], format="%d/%m/%Y"
    ).dt.strftime("%m/%d/%Y")

    new_df = pd.DataFrame(
        {
            "FirstName": df["FirstName"],
            "LastName": df["LastName"],
            "Gender": df["Gender"],
            "Birthdate": df["Birthdate"],
            "MRN": df["Email"],
            "Ethnicity": df["Ethnicity"],
            "Club/School Offering ECG": df["Club/School Offering ECG"],
            "Currently experiencing heart-related symptoms": df[
                "Are you currently experiencing any heart-related symptoms?"
            ],
            "Parent/Guardian Name": df["Parent/Guardian Name"],
            "Anonymous sharing opt out": df[
                "Opt out of anonymised data sharing for research purposes"
            ],
        }
    )

    new_df.to_csv(output_csv_path, index=False)
