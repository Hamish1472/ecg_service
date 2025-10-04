import os
import datetime
import logging


def cleanup_old_csvs(data_dir, days):
    for filename in os.listdir(data_dir):
        if not filename.endswith(".csv"):
            continue
        try:
            file_date = datetime.datetime.strptime(
                filename.replace(".csv", ""), "%Y-%m-%d"
            ).date()
        except ValueError:
            continue
        if (datetime.date.today() - file_date).days > days:
            os.remove(os.path.join(data_dir, filename))
            logging.info(f"Deleted old CSV: {filename}")
