
import os.path, random, re, time
from collections.abc import Callable
from typing import Any

from bs4 import BeautifulSoup, Tag
from selenium import webdriver


# general constant
PATN = r"[\u4E00-\u9FFF]" # PATN: pattern, didn't use `PATRN` because it looks like `print` in a glance
# cite: https://en.wikipedia.org/wiki/CJK_Unified_Ideographs#CJK_Unified_Ideographs_blocks
HOR_RULE = "~~~~~~~~~~~~~~~~~~~~~~~~~~~~~"

# directory related constant
DIR = "novel_crawler/"
SAVE_FNAME = DIR + "store_content.txt"
CRAWL_URL = DIR + "crawl_url.txt" # file contain only url to the contents of the novel
with open(CRAWL_URL) as file:
    URL = file.read()


#* Glossary: 
# title: Name of the novel
# contents: List of chapter titles in the novel
# chapter: Title and text of chapter
# heading: Title of chapter
# body: Text of chapter

#* Note: 
# The contents page and all chapters are in their dedicated url.

class NoResultFoundError(Exception):
    """Raised when BeautifulSoup find-like function returns None."""
    pass

def alter_find(func:Callable[..., Any], *args:Any, **kwargs:Any) -> Any:
    result:Any|None = func(*args, **kwargs)
    if result is None:
        message = f"The result of {func.__name__} is None."
        
        # empty sequences are considered false
        # cite:　https://docs.python.org/3/library/stdtypes.html#truth-value-testing
        message += f"\nAll arguments: {', '.join(
            map(str, args)
            )}." if args else "" 
        message += f"\nAll keyword arguments: {kwargs}" if kwargs else ""
        raise NoResultFoundError(message)
    return result

def character_count(body:str) -> int:
    """
    Return the number of chinese characters in the text.

    Parameters
    ----------
    text: (str)
        The text to count characters.

    Returns
    -------
    int
        Number of characters in the text.
    """
    return len(re.findall(PATN, body))

def get_last_heading() -> str|None:
    """
    Return heading of the last chapter in the file, 
    the file is defined by ``FNAME``.

    Returns
    -------
    str|None
        The heading of last chapter.
    """
    with open(SAVE_FNAME, mode="r", encoding='UTF-8') as file:
        content = file.read()
        if content == "":
            return None
        
        # extract heading from file content
        last_heading = content.rsplit(HOR_RULE)[-2]
        
        return last_heading.strip()

def get_contents(url:str, driver:webdriver.Chrome, last_heading:str|None=None) -> list[Tag]:
    """
    Crawl all chapter headings from the contents page, 
    returns a list of <a> tags contain heading.

    Parameters
    ----------
    url: (str)
        Link to the contents page.
    driver: (webdriver.Chrome)
        The chrome driver.
    last_heading: (str | None, optional, by default None)
        Last heading in the store file, if provided, return only the following headings.
        (skip all previous headings including this one)

    Returns
    -------
    list[str]
        A list of <a> tags contain chapter heading and url.
    """
    driver.get(url)
    soup = BeautifulSoup(driver.page_source,'html.parser')
    
    chapter_list = alter_find(soup.select_one, selector=".chapter-list")
    
    if last_heading is None:
        chapter_rest = alter_find(chapter_list.find_all, name="a")
    else:
        target = alter_find(chapter_list.find, name="a", string=last_heading)
        parent = alter_find(target.find_parent, name="li")
        chapter_rest = alter_find(parent.find_next_siblings)

    return [alter_find(tag.find, name="a") for tag in chapter_rest if tag.find("a") is not None]

def store_chapter(chapter:str) -> None:
    """
    Store (append) chapters to save file.

    Parameters
    ----------
    content: (str)
        The chapters to save.
    """
    with open(SAVE_FNAME, mode="a", encoding='UTF-8') as file:
        file.write(chapter)

def crawl_novel_body(contents:dict[str, str], driver:webdriver.Chrome) -> list[tuple[str, str]]:
    """
    Use link in `contents` to crawl the body from website.

    Parameters
    ----------
    contents: (dict[str, str])
        ``{chapter_link, chapter_title}``
        The link and title of all chapters to crawl.
    driver: (webdriver.Chrome)
        The chrome driver.
    
    Returns
    -------
    list[tuple[str, str]]
        ``[(chapter_title, chapter_link)]``
        The title and link of all chapters where body has fewer characters.
    """
    flags:list[tuple[str, str]] = []
    
    for link, heading in contents.items():
        # add time interval between crawl to avoid bot detection
        time.sleep(1.1 + random.random() * 1.4)
        
        content:str = ""
        
        # crawl
        driver.get(link)
        soup = BeautifulSoup(driver.page_source,'html.parser')
        body = soup.select(".content")[0].text
        chars = character_count(body)
        
        # if the number of character in content is < 200, flag the page
        if chars < 200:
            flags.append((heading, link))
        else:
            content += HOR_RULE + "\n"
            content += heading + "\n"
            content += HOR_RULE + "\n\n"
            content += body + "\n\n\n"
        
        # show current progress
        print(f"\033[KWriting: {heading}", end="\r", flush=True)
        
        store_chapter(content)
    return flags

def operation(url:str=URL):
    """
    The whole operation to get chapters from website to local file.

    Parameters
    ----------
    url: (str, optional, by default URL)
        Link to the novel website.
    """
    # setup driver
    driver = webdriver.Chrome()
    
    # setup file to store text
    if not os.path.isfile(SAVE_FNAME):
        with open(SAVE_FNAME, mode="w") as file:
            file.write("")
    
    # get last heading in file
    last_heading = get_last_heading()
    print(f"last heading exist: {last_heading}")
    
    # get all the <a> tag contain headings (title and link)
    element = get_contents(url, driver, last_heading)
    contents:dict[str, str] = {
        ("https:" + alter_find(tag.get, key="href")): tag.text
        for tag in element
        }
    
    # crawl body on website
    flags = crawl_novel_body(contents, driver)
    
    if flags == []:
        print("There's no chapter having less than 200 characters.")
    else:
        print(f"There's {len(flags)} chapter having less than 200 characters.")
        for flag in flags:
            print(*flag)

if __name__ == "__main__":
    operation()
    print("ended.")
