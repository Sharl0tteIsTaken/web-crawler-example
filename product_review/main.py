"""
A script to crawl product reviews.
"""
from typing import TypeAlias, Literal
from pathlib import Path

from resources.utilities import get_coverage_cutoff

# import requests
# from bs4 import BeautifulSoup, Tag
from selenium import webdriver
# from selenium.webdriver.remote.webdriver import WebDriver

# ---------------------------------------------------------------------
Platform: TypeAlias = Literal["Reddit", "Youtube", "Bahamut"]

CRAWL_KEYWORD = "apple vision pro" or "steam machine"
CRAWL_PLATFORM: Platform = ""
CRAWL_OUTPUT_DIR = Path("")

# Glossary
# post: post on Reddit & Bahamut / video on Youtube
# thread: discussion thread in comment section
# popularity threshold: how popular is a comment to be included, most
#                       platform have upvote/like system, this is used
#                       to get the majority opinion on products.


# crawl parameters
MAX_POST_COUNT = 10
MAX_THREAD_DEPTH = 3  # how much post
POPULARITY_THRESHOLD = 0.9
INTERACTION_THRESHOLD = 100


# get platform instruction
# each platform have different instruction to crawl
driver = webdriver.Chrome()
get_coverage_cutoff()
