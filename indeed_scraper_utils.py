"""This file contains utility functions that will
    support for the webscraping on indeed.com and storing
    the scraped job info into a database.
"""


# standard library imports
import time
import sqlite3
import re
import logging
from datetime import date
from datetime import datetime
from datetime import timedelta


# third party imports
from selenium import webdriver
from selenium.webdriver.chrome.webdriver import WebDriver
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selectolax.parser import HTMLParser  # a different parser


# logging format
current_date = str(date.today())
logging.basicConfig(filename=f"./log_files/{current_date}_indeed_log.txt", level=logging.INFO, format=' %(asctime)s - %(levelname)s- %(message)s')


# 1. launch browser
def launch_browser(region:str) -> WebDriver:
    """To launch malaysian indeed.com using chrome."""

    options = webdriver.ChromeOptions()
    options.add_experimental_option("detach", True)  # so that borwser doesn't close
    driver = webdriver.Chrome()
    webpage_url = "https://malaysia.indeed.com/"

    if region == "SG":
        webpage_url = "https://sg.indeed.com/"

    driver.get(webpage_url)
    return driver


# 2. Perform job search
def search_job(driver: WebDriver, job_title: str, job_location: str) -> None:
    """To search the webpage for desired job."""

    # find the job_title box and input job title
    job_title_box = driver.find_element(By.ID, "text-input-what")
    job_title_box.send_keys(job_title)

    # find the location and input location
    location_box = driver.find_element(By.ID, "text-input-where")
    location_box.send_keys(job_location)
    location_box.send_keys(Keys.ENTER)  # to search

    logging.info(f"Webscraping started for {job_title}, {job_location}")


# 3. Sort job by date
def sort_job_by_date(driver: WebDriver) -> None:
    """To select date option to sort jobs."""

    try:
        date = driver.find_element(By.XPATH,
                               '/html/body/main/div/div[1]/div/div[5]/div/div[1]/div[4]/div/div/div[1]/span[2]/a')
    except:
        date = driver.find_element(By.XPATH,
                               '//*[@id="jobsearch-JapanPage"]/div/div[5]/div[1]/div[4]/div/div/div[1]/span[2]/a')

    date.click()


def close_pop_up(driver: WebDriver, region:str) -> None:
    """To close pop up notification."""

    # privacy policy pop-up
    privacy = driver.find_element(By.XPATH, '//*[@id="CookiePrivacyNotice"]/div/button')
    privacy.click()
    time.sleep(2)

    if region == "SG":
        # singaporean indeed has cookies to be rejected
        cookies = driver.find_element(By.XPATH, '//*[@id="onetrust-reject-all-handler"]')
        cookies.click()
        time.sleep(3)

        # singaporean indeed has email pop up
        email_pop_up = driver.find_element(By.XPATH, '//*[@id="google-Only-Modal"]/div/div[1]/button')
        email_pop_up.click()
        time.sleep(3)

        # to close normal pop-up
        try:
            normal_pop_up = driver.find_element(By.CSS_SELECTOR, "button.css-yi9ndv")
            normal_pop_up.click()
        except:
            logging.info("No normal pop up in indeed singapore")

        time.sleep(3)
        driver.execute_script("window.scrollTo(0, document.body.scrollHeight)")
        return

    # to close normal popup in MY
    normal_pop_up = driver.find_element(By.CSS_SELECTOR, "button.css-yi9ndv")
    normal_pop_up.click()
    time.sleep(3)
    driver.execute_script("window.scrollTo(0, document.body.scrollHeight)")


# 4a. Extract job tile, company name, location, link, unique data for id purpose
def extract_each_job(container) -> tuple:
    """To extract info from each job container"""

    base_url = "https://malaysia.indeed.com"
    job_info_list = []
    job_info_list.append(container.css_first("h2.jobTitle > a").attributes["data-jk"])  # job_id
    job_info_list.append(container.css_first("h2.jobTitle > a").text())  # job-title
    job_info_list.append(container.css_first("div.company_location > div > span").text())  # company name
    job_info_list.append(container.css_first("div.company_location > div > div").text())  # company location
    job_info_list.append(base_url + container.css_first("h2.jobTitle > a").attributes["href"])  # link
    return tuple(job_info_list)


# 4b. Extract job descriptions and dates
def extract_jobdesc(descrip, dates) -> tuple:
    """To extract job description and date."""

    job_descrip_list = []

    # to extract the job date
    posted_date = dates.text()[6:]
    temp = re.findall(r'\d+', posted_date)  # get only number
    obtained_date = list(map(int, temp))
    posted_date = 0  #posted today
    if obtained_date:
        posted_date = obtained_date.pop()

    # to extract job description
    descr = descrip.css("li")
    descrip_text = ""
    for desc in descr:
        descrip_text = descrip_text + desc.text() + "\n"

    # append for each job
    job_descrip_list.append(descrip_text)
    job_descrip_list.append(posted_date)
    job_descrip_list.append(date.today())
    job_descrip_list.append("Not read")  # read or favourite status
    job_descrip_list.append("Not sent")  # email status

    return tuple(job_descrip_list)


# 4c. Extract job tile, company name, location, link, unique data for id purpose
def extract_jobs(html_source, main_job_info_list: list) -> None:
    """To get all job containers in the page and extract
        job infos with the description and posted date.
    """

    # parse the html
    time.sleep(5)
    html_parser = HTMLParser(html_source)

    # extract each container
    containers = html_parser.css("td.resultContent")  # main container
    descr_containers = html_parser.css("div.css-146u2z1.eu4oa1w0 > ul")  # div.job-snippet
    date_container = html_parser.css("span.css-qvloho") # "span.date"

    # put all containers in a tuple for iteration purpose
    main_tuple = []

    for index,_ in enumerate(containers):
        main_tuple.append((containers[index], descr_containers[index], date_container[index]))
    tuple(main_tuple)

    for container, descrip, dates in main_tuple:
        # to extract job-tilte, location, comapny name, link and ID
        job_info = extract_each_job(container)
        # to extract job description and date posted
        description_info = extract_jobdesc(descrip, dates)
        # concat both tuples
        main_job_info_list.append(job_info+description_info)


# 5. pagination and scrap next page
def next_page(driver: WebDriver, prev_url:str, counter:int) -> list:
    """To navigate to next page and return status of next page with the next
        page url.
    """

    # counter is set to limit the number of pages to scrap
    if counter > 6:
        return False, None

    pages = driver.find_elements(By.CSS_SELECTOR, "ul.css-1g90gv6 > li")  # list of pages
    last_page = pages[-1].find_element(By.CSS_SELECTOR, "a")  # find next page a tag

    # if next page same as previous then no more pages so end the loop
    url = last_page.get_attribute("href")
    if prev_url == url:
        return False, None

    last_page.click()
    return True, url


# 6a. Store all scraped data in sqlite database
def connect_to_db(job_title:str, region:str) -> tuple:
    """To connect to database."""

    database = "./databases/indeed_my.db"
    if region == "SG":
        database = "./databases/indeed_sg.db"
    conn = sqlite3.connect(database, detect_types=sqlite3.PARSE_DECLTYPES |
                                                        sqlite3.PARSE_COLNAMES)
    cursor = conn.cursor()

    # the job_id is the primary key, so no duplicate jobs
    cursor.execute(f'''CREATE TABLE IF NOT EXISTS {job_title}
                   (job_id TEXT PRIMARY KEY, job_title TEXT, company_name TEXT, location TEXT, link TEXT,
                    description TEXT, duration REAL, date TIMESTAMP, flag TEXT, email TEXT)''')
    conn.commit()
    return (conn, cursor)


# 6b. Insert data into database
def insert_to_database(main_job_list:list, conn, cursor, job_title:str) -> None:
    """To insert data into the database."""

    # insert a list of tuples only if the entry is new or else ignore it
    cursor.executemany(f'''INSERT OR IGNORE INTO {job_title} VALUES(?,?,?,?,?,?,?,?,?,?)''', main_job_list)
    conn.commit()

    # close the connections
    logging.info(f"Job info for {job_title} successfully stored in database.")
    cursor.close()
    conn.close()


# 7a. Helper function to get dates
def get_dates(table_name:str, database:str) -> None:
    """To uget the current date column from table"""

    conn = sqlite3.connect(database)
    cursor = conn.cursor()
    cursor.execute(f'''SELECT date as "[timestamp]" FROM {table_name}''')
    dates = cursor.fetchall()
    cursor.close()
    conn.close()

    return dates


# 7b. To check the date column and update it everyday
def update_duration_date(table_name:str, region:str) -> None:
    """To update the duration and datesfor prexisting job daily.
        If the scraper is run more than once in a day, the date column
        will not be updated more than once. This column is updates only if
        the dates in database are older than current date.
    """

    database = "./databases/indeed_my.db"
    if region == "SG":
        database = "./databases/indeed_sg.db"

    dates = get_dates(table_name, database)
    conn = sqlite3.connect(database)
    cursor = conn.cursor()

    for index, my_date in enumerate(dates):

        # convert string date to date obj
        date_string = my_date[0]
        date_format = "%Y-%m-%d"
        date_obj = datetime.strptime(date_string, date_format).date()

        # if the scraper is running on next day, update the date and duration cols
        if date_obj < date.today():
            current_duration = cursor.execute(f'''SELECT duration FROM {table_name} WHERE rowid = {index + 1}''')
            current_duration = cursor.fetchall()
            new_duration = current_duration[0][0] + 1
            cursor.execute(f'''Update {table_name} set duration = {new_duration} where rowid = {index + 1}''')
            # use "" to prevent interpreting date as integer
            cursor.execute(f'''Update {table_name} set date = "{date_obj + timedelta(1)}" where rowid = {index + 1}''')

    # always commit and close connections
    conn.commit()
    cursor.close()
    conn.close()


def search_all_jobs(job: str, location: str, database_table: str, region: str) -> None:
    """Main function containing each fundamental function calls.
         to scrap indeed for a given job search.
    """

    # 1. Launch browser and search
    driver = launch_browser(region)
    time.sleep(4)
    search_job(driver, job, location)

    # 2. to sort by date
    time.sleep(4)
    sort_job_by_date(driver)

    # 3. to close pop up
    time.sleep(4)
    close_pop_up(driver, region)

    # 4. Scrap job search data
    time.sleep(4)
    status = True
    main_job_list = []
    prev_url = ""
    counter = 0  # to set limit to pages to be scraped

    while status:
        # data extraction for each page
        html_source = driver.page_source  # new page source html
        extract_jobs(html_source, main_job_list)
        status, prev_url = next_page(driver, prev_url, counter)
        counter = counter + 1
        time.sleep(8)

    # 5. Connect to indeed.db and insert data into the table specific to job title
    conn, cursor = connect_to_db(database_table, region)
    insert_to_database(main_job_list, conn, cursor, database_table)

    # 6. Update the duration and dates if we are scraping the next day
    update_duration_date(database_table, region)

    # 6. close the browser
    logging.info(f"Webscraping for {job}, {location} successful \n")
    driver.close()
