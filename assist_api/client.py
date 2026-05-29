from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import (
    TimeoutException,
    NoSuchElementException,
    WebDriverException,
    StaleElementReferenceException,
    InvalidSessionIdException,
)
from bs4 import BeautifulSoup, Tag
from typing import List, Optional
import time

from .objects import (
    Course,
    Series,
    Agreement,
    Row,
    Section,
    Group,
    ClauseType,
    CSSClasses,
)
from .exceptions import *


def retry_call(f, *args, max_retries=2, delay=0.3, **kwargs):
    for attempt in range(max_retries + 1):
        try:
            return f(*args, **kwargs)

        except (TimeoutException, StaleElementReferenceException) as e:
            if attempt == max_retries:
                raise PageLoadTimeoutError() from e
            time.sleep(delay)

        except NoSuchElementException as e:
            raise ElementNotFoundError() from e

        except (WebDriverException, InvalidSessionIdException) as e:
            raise WebDriverError() from e


class AssistAPI:
    def __init__(self):
        self.options: Options = Options()
        self.options.add_argument("--headless=new")
        self.options.add_argument("--window-size=1920,1080")
        self.options.add_argument("--disable-gpu")
        self.options.add_argument("--no-sandbox")

        self.options.page_load_strategy = "normal"

    def __enter__(self):
        self.driver = webdriver.Chrome(options=self.options)
        self.wait = WebDriverWait(self.driver, 10)
        return self

    def __exit__(self, exc_type, exc_value, traceback):
        self.driver.quit()

    def _load_colleges_from(self):
        self.driver.get("https://assist.org")

        # click the "from colleges" button to show the options
        from_button = self.wait.until(
            EC.element_to_be_clickable((By.ID, "None-governing-institution-select"))
        )
        from_button.click()

    def _load_colleges_to(self, from_college: str):
        self._load_colleges_from()

        # select the choice that matches the string
        from_choice = self.wait.until(
            EC.element_to_be_clickable(
                (
                    By.XPATH,
                    f"//amc-option//span[contains(@class,'option__primary-text') and normalize-space()='{from_college}']",
                )
            )
        )
        from_choice.click()

        # click the "to colleges" button to show the options
        to_button = self.wait.until(
            EC.element_to_be_clickable((By.ID, "None-agreement-institution-select"))
        )
        to_button.click()

    def _load_programs(self, from_college: str, to_college: str):
        self._load_colleges_to(from_college)

        # select the college transferring to
        to_choice = self.wait.until(
            EC.element_to_be_clickable(
                (
                    By.XPATH,
                    f"//amc-option//span[contains(@class,'option__primary-text') and normalize-space()='{to_college}']",
                )
            )
        )
        to_choice.click()

        # press the submit button to load the programs page
        submit = self.wait.until(
            EC.element_to_be_clickable(
                (By.XPATH, "//button[normalize-space()='View Agreements']")
            )
        )
        submit.click()

    def get_colleges(self) -> List[str]:
        def helper():
            self._load_colleges_from()

            elements = self.wait.until(
                EC.presence_of_all_elements_located(
                    (
                        By.XPATH,
                        "//amc-option//span[contains(@class,'option__primary-text')]",
                    )
                )
            )

            # discard the last element, it is NOT a college
            return [element.text.strip() for element in elements][:-1]

        # wrap function to retry and throw appropriately
        return retry_call(helper)

    def get_transfer_colleges(self, from_college: str) -> List[str]:
        def helper(from_college: str):
            self._load_colleges_to(from_college)

            colleges = self.wait.until(
                EC.presence_of_all_elements_located(
                    (
                        By.XPATH,
                        "//amc-option//span[contains(@class,'option__primary-text')]",
                    )
                )
            )

            college_names = [college.text.strip() for college in colleges]
            return college_names[:-1]

        return retry_call(helper, from_college)

    def get_programs(self, from_college: str, to_college: str) -> List[str]:
        def helper(from_college: str, to_college: str):
            self._load_programs(from_college, to_college)

            rows = self.wait.until(
                EC.presence_of_all_elements_located((By.CLASS_NAME, "viewByRowColText"))
            )

            programs = [row.text.strip() for row in rows]
            return programs

        return retry_call(helper, from_college, to_college)

    def _get_html(self, from_college: str, to_college: str, program: str) -> str:
        self._load_programs(from_college, to_college)

        program_button = self.wait.until(
            EC.element_to_be_clickable(
                (
                    By.XPATH,
                    f"//div[contains(@class,'viewByRowColText') and normalize-space()='{program}']",
                )
            )
        )
        program_button.click()

        self.wait.until(EC.presence_of_element_located((By.CLASS_NAME, "template")))

        return self.driver.page_source

    def _walk(
        self, root_element: Tag, res: List[Course | Series]
    ) -> List[Course | Series]:
        for element in root_element.find_all(recursive=False):
            classes = element.get("class", [])

            # singluar course
            if CSSClasses.COURSE in classes:
                res.append(Course.from_element(element))
            elif CSSClasses.SERIES in classes:
                content = element.find(class_=CSSClasses.SERIES_CONTENT)

                if content:
                    children = self._walk(content, [])
                    series = Series.from_element(content, children)
                    res.append(series)
        return res

    def get_agreement(
        self, from_college: str, to_college: str, program: str
    ) -> Optional[Agreement]:
        # attempt to scrape html
        try:
            html = retry_call(self._get_html, from_college, to_college, program)
        except (TimeoutError, ElementNotFoundError) as e:
            raise HtmlParseError() from e

        soup = BeautifulSoup(html, "html.parser")
        requirements = []

        try:
            groups = soup.find_all(class_=CSSClasses.GROUP)
            for group in groups:
                group_number = int(
                    group.find(class_=CSSClasses.GROUP_NUMBER).get_text().strip()
                )
                group_header = " ".join(
                    group.find(class_=CSSClasses.GROUP_HEADER).get_text().split()
                )

                sections = []

                for section in group.find_all(class_=CSSClasses.SECTION):
                    section_letter = section.find(class_=CSSClasses.SECTION_LETTER)
                    rows = []

                    for row in section.find_all(class_=CSSClasses.ROW):
                        row_receiving = row.find(class_=CSSClasses.RECEIVING)
                        row_sending = row.find(class_=CSSClasses.SENDING)

                        receiving = None
                        sending = None

                        if row_receiving:
                            data = self._walk(row_receiving, [])

                            if len(data) == 1:
                                receiving = data[0]

                        # do first layer iteratively
                        if row_sending:
                            # first layer clause
                            root_clause = None

                            if row_sending.find(class_=CSSClasses.OR_ROOT):
                                root_clause = ClauseType.OR
                            elif row_sending.find(class_=CSSClasses.AND_ROOT):
                                root_clause = ClauseType.AND

                            # the presence of a root clause implies there is > 1 courses
                            if root_clause:
                                sending = Series(
                                    root_clause, self._walk(row_sending, [])
                                )

                            # the root is either a series or singular course
                            else:
                                data = self._walk(row_sending, [])

                                if len(data) == 1:
                                    sending = data[0]
                                elif len(data) > 1:
                                    sending = Series(ClauseType.AND, data)

                        rows.append(Row(receiving, sending))
                    sections.append(
                        Section(
                            section_letter.get_text().strip()
                            if section_letter
                            else None,
                            rows,
                        )
                    )
                requirements.append(Group(group_number, group_header, sections))
            return Agreement(requirements)

        except Exception as e:
            raise AgreementParseError() from e
