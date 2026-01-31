"""
A script to crawl text from websites, primarily used on novel websites.
"""
import os
import random
import re
import time
from collections.abc import Callable
from pathlib import Path
from typing import Any

import requests
from bs4 import BeautifulSoup, Tag
from selenium import webdriver
from selenium.webdriver.remote.webdriver import WebDriver

# ---------------------------------------------------------------------
# User input values
URL = ""
SAVE_FILE_PATH = Path("")


# ---------------------------------------------------------------------
# General constant
DEFAULT_FNAME = "store_content.txt"
ENCODING = "UTF-8"
HOR_RULE = "~" * 30
MIN_CHARS = 200
ZH_CHARS = r"[\u4E00-\u9FFF]"  # see: wikipedia.org/CJK_Unified_Ideographs

# Glossary
# Title: Name of the novel.
# Contents: List of headings in the novel.
# Chapter: Heading and body of a section in the novel.
# Heading: Name of the chapter.
# Body: Text of the chapter.

# Custom types
type Chapter = str
type ChapterLink = str
type Heading = str


# ---------------------------------------------------------------------


class ResultNotFoundError(Exception):
    """Raised when BeautifulSoup find-like function returns None."""


def check_url(url: str) -> None:
    """
    Check if url exist and is responding.

    Parameters
    ----------
    url : str
        The url to check.
    """
    assert url, "Please enter URL to the novel website."
    response = requests.get(url=url, timeout=10)
    response.raise_for_status()


def sanitize_file_path(file_path: Path) -> Path:
    """
    Ensure the file path contains a file and is writable.

    Parameters
    ----------
    file_path : Path
        The file path to check.

    Raises
    ------
    FileNotFoundError
        Raised if the file in file path doesn't exist.
    PermissionError
        Raised if doesn't have access right to the file.

    Returns
    -------
    Path
        The sanitized file path.
    """
    if file_path.is_dir():
        file_path = file_path / DEFAULT_FNAME
        print(
            "The entered path doesn't specify a file, the contents are stored "
            f"in the `{DEFAULT_FNAME}` within that folder."
            )

    try:
        os.access(file_path, os.W_OK)
    except FileNotFoundError:
        print(
            "Please enter a valid path with file name to load from or safe to."
            f"\nEntered path: `{file_path}`."
            )
    except PermissionError:
        print(f"You don't have permission on`{file_path}`.")

    return file_path


def alter_find(func: Callable[..., Any], *args: Any, **kwargs: Any) -> Any:
    """
    A wrapper for BeautifulSoup find-like functions that helps avoid
    static type checker warnings.

    All arguments and keyword arguments are passed through to the given
    function. If it returns ``None``, NoResultFoundError is raised.

    This is useful when working under `strict` type checking mode with
    tools like MyPy or Pyright.

    Parameters
    ----------
    func: Callable[..., Any]
        A find-like function from BeautifulSoup (example: :func:`find`,
        :func:`find_all`, ...).
        This function will be called with other provided arguments and
        keyword arguments.

    Returns
    -------
    Any
        The result returned by the find-like function. The type of value
        can be :type:`bs4.Tag`, :type:`bs4.element.ResultSet`, or other
        types, depending on the function used.

    Raises
    ------
    ResultNotFoundError
        Raised when the find-like function returns ``None``.
        The exception includes the function name and the arguments
        passed to assist in debugging.

    Examples
    --------
    **Using :func:`select_one()` in HTML**

    >>> soup = BeautifulSoup()
    >>> selected: Tag = alter_find(soup.select_one, selector=".class")

    **Using :func:`find_all()` on bs4.Tag**

    >>> a_tags: ResultSet = alter_find(tag.find_all, name="a")

    **Using :func:`get()` on bs4.Tag**

    >>> href: str | list[str] = alter_find(tag.get, key="href")

    """
    result: Any | None = func(*args, **kwargs)
    if result is None:
        arguments = [str(arg) for arg in args]

        message = f"The result of {func.__name__} is None.\n"
        message += f"All arguments: {', '.join(arguments)}." if args else ""
        message += f"\nAll keyword arguments: {kwargs}" if kwargs else ""

        raise ResultNotFoundError(message)
    return result


def zh_char_count(text: str) -> int:
    """
    Return the number of chinese characters in the :attr:`text`.

    Parameters
    ----------
    text: str
        The text to count characters.

    Returns
    -------
    int
        Number of characters in the text.
    """
    return len(re.findall(ZH_CHARS, text))


def get_last_heading(file_name: Path) -> str | None:
    """
    Return heading of the last chapter in the file, if there is content
    in the file.

    Parameters
    ----------
    file_name: Path
        The path to the safe file.

    Returns
    -------
    str | None
        The heading of last chapter.
    """
    with open(file_name, mode="r", encoding='UTF-8') as file:
        content = file.read()
        if content == "":
            return None

        # extract heading from file content
        last_heading = content.rsplit(HOR_RULE)[-2]

        return last_heading.strip()


def get_headings(
    url: str, driver: WebDriver, last_heading: str | None = None
) -> list[Tag]:
    """
    Crawl all chapter headings from the contents page, returns a list of
    HTML `<a>` tags contain headings.

    Parameters
    ----------
    url: str
        Link to the contents page.
    driver: WebDriver
        The chrome driver.
    last_heading: str | None, by default None
        Last heading in the store file. If provided, return only the
        following headings (skip all previous headings including this
        one).

    Returns
    -------
    list[Tag]
        A list of `<a>` tags contain chapter heading and url.
    """
    driver.get(url)
    soup = BeautifulSoup(driver.page_source, 'html.parser')

    chapter_list = alter_find(soup.select_one, selector=".chapter-list")

    if last_heading is None:
        chapter_rest = alter_find(chapter_list.find_all, name="a")
    else:
        target = alter_find(chapter_list.find, name="a", string=last_heading)
        parent = alter_find(target.find_parent, name="li")
        chapter_rest = alter_find(parent.find_next_siblings)

    return [
        alter_find(tag.find, name="a")
        for tag in chapter_rest
        if tag.find("a") is not None
        ]


def crawl_novel_body(
    contents: dict[ChapterLink, Heading], driver: WebDriver
) -> tuple[list[Chapter], list[tuple[Heading, ChapterLink]]]:
    """
    Use link in :attr:`contents` to crawl the body from website.

    Parameters
    ----------
    contents: dict[ChapterLink, Heading]
        The link and title of all chapters to crawl.
    driver: WebDriver
        The chrome driver.

    Returns
    -------
    tuple[list[Chapter], list[tuple[Heading, ChapterLink]]]
        List of crawled chapters.
        The title and link of chapters where body has fewer characters
        then expected.
    """
    flags: list[tuple[str, str]] = []

    chapters: list[str] = []
    for link, heading in contents.items():
        time.sleep(1.1 + random.random() * 1.4)

        chapter: str = ""

        driver.get(link)
        soup = BeautifulSoup(driver.page_source, 'html.parser')
        body = soup.select(".content")[0].text
        chars = zh_char_count(body)

        if chars < MIN_CHARS:
            flags.append((heading, link))
        else:
            chapter += HOR_RULE + "\n"
            chapter += heading + "\n"
            chapter += HOR_RULE + "\n\n"
            chapter += body + "\n\n\n"

        # show current progress
        print(f"\033[KWriting: {heading}", end="\r", flush=True)
        chapters.append(chapter)
    return chapters, flags


def store_chapters(chapters: list[str], file_path: Path) -> None:
    """
    Store (append) chapters to file.

    Parameters
    ----------
    chapters: list[str]
        The chapters to save.
    file_path: Path
        The path of file to store chapters.
    """
    for chapter in chapters:
        with open(file_path, mode="a+", encoding='UTF-8') as save_file:
            save_file.write(chapter)


def operation(url: str) -> None:
    """
    The whole process to get chapters from website to local file.

    Parameters
    ----------
    url: str, optional, by default URL
        Link to the novel website.
    """
    driver = webdriver.Chrome()

    last_heading = get_last_heading(SAVE_FILE_PATH)
    print(f"last heading exist: {last_heading}")

    element = get_headings(url, driver, last_heading)
    contents: dict[str, str] = {
        ("https:" + alter_find(tag.get, key="href")): tag.text
        for tag in element
        }

    chapters, flags = crawl_novel_body(contents, driver)
    store_chapters(chapters, SAVE_FILE_PATH)

    if not flags:
        print("There's no chapter having less than 200 characters.")
    else:
        print(f"There's {len(flags)} chapter having less than 200 characters.")
        for flag in flags:
            print(*flag)


if __name__ == "__main__":
    check_url(URL)
    sanitize_file_path(SAVE_FILE_PATH)
    operation(URL)
    print("Script ended.")
