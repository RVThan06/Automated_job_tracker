"""Program file to read the database for any new job entry and
    notify user via email alert.
"""


# standard library imports
import sqlite3
import logging
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart


# logging format
logging.basicConfig(level=logging.INFO, format=' %(asctime)s - %(levelname)s- %(message)s')


def select_new_jobs(table_name: str, region:str) -> list:
    """To check the database for a new entry and then
        send an email to notify on basic job details.
    """

    database = "./databases/indeed_my.db"
    if region == "SG":
        database = "./databases/indeed_sg.db"

    # get the whole duration column
    conn = sqlite3.connect(database)
    cursor = conn.cursor()
    cursor.execute(f'''SELECT duration FROM {table_name}''')
    durations = cursor.fetchall()

    # get the email status for all jobs
    cursor.execute(f'''SELECT email FROM {table_name}''')
    email_status = cursor.fetchall()

    # check if duraation <= 5 and no email sent, indicating job was posted today and haven't notify
    new_entry_list = []

    # if job posted within 5 days then send email
    for index,_ in enumerate(durations):
        if durations[index][0] <= 5.0 and email_status[index][0] == "Not sent":
            cursor.execute(f'''SELECT * FROM {table_name} WHERE rowid = {index + 1}''')
            results = cursor.fetchall()
            new_entry_list.append(results)
            cursor.execute(f'''Update {table_name} set email = "sent" where rowid = {index + 1}''')

    logging.info(f"New enteries fetched successfully for {table_name}")

    # close the connections
    conn.commit()
    cursor.close()
    conn.close()

    # return all new entries as a list of list with tuple
    return new_entry_list


def convert_jobinfo_to_string(job_info:tuple) -> None:
    """To convert the job info into string.
        This function is called on each query fetched
        from the database.
    """

    job_data = []
    for column, item in enumerate(job_info):

        # avoid the primary key part
        if column == 0:
            continue
        job_data.append(item)
        # stop till the link column which is 5th column
        if column == 5:
            break
    # concat the list items into single string
    job_data = ",\n".join(job_data)
    return job_data


def send_email(new_message: str, table_name:str, region:str) -> None:
    """To send email on RAM modules scraped."""

    message = MIMEMultipart()
    message["Subject"] = f"Indeed MY - {table_name}"
    if region == "SG":
        message["Subject"] = f"Indeed SG - {table_name}"
    message["From"] = "rv10_python_project@outlook.com"
    message["To"] = "arvinthevar06@gmail.com"

    info = MIMEText(new_message)
    message.attach(info)  # to attach the actual message

    with smtplib.SMTP("smtp.office365.com", 587) as server:
        server.ehlo()
        server.starttls()
        server.login("rv10_python_project@outlook.com", "Wfneujb986n93nn45")
        server.sendmail("rv10_python_project@outlook.com", "arvinthevar06@gmail.com", message.as_string())

    logging.info(f"Email sent successfully on new enteries for {table_name}")


# main function to incorporate all3 functions above
def check_new_jobs(table_name:str, region:str) -> None:
    """To check for new jobs and notify the user."""

    # get the new job enteries
    new_job_entries = select_new_jobs(table_name, region)

    # create a single string message using all new enteries
    message = ""
    for jobs in new_job_entries:
        message = message + convert_jobinfo_to_string(jobs[0]) + "\n" # double line gap between new entries

    # send email if and only if there are new jobs
    if message:
        send_email(message, table_name, region)
