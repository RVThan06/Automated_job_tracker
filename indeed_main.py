"""Main file containing function calls to utility
    functions that will scrap indeed.com based on different
    job titles.
"""

# standard library import
import time
import csv

# third party import

# library imports
import indeed_scraper_utils as utils
import indeed_send_email as send_email


# Main Program
def main() -> None:
    """Main function that calls to
        iterate over all different job tiles stored in csv file.
    """

    # 1. to scrap data for each job title and store it in respective tables
    with open("jobs_location/indeed_jobs_location.csv", "r") as indeed:
        jobs = csv.reader(indeed)

        for job_info in jobs:
            utils.search_all_jobs(job_info[0], job_info[1], job_info[2], job_info[3])
            time.sleep(5)

    # 2. To check for a new entry and then send email alert
    with open("jobs_location/indeed_jobs_location.csv", "r") as indeed:
        jobs = csv.reader(indeed)

        for job_info in jobs:
            send_email.check_new_jobs(job_info[2], job_info[3])
            time.sleep(10)


if __name__ == "__main__":
    main()
