import requests
import random
from bs4 import BeautifulSoup, SoupStrainer, element
from urllib.parse import urljoin
import typing as t

# Links

BASE = "https://www.edge.org/"
LANDING = "https://www.edge.org/annual-questions" # List of annual questions

ANNUAL = "/annual-question/"
CONTRIB = "/contributors/"

class EdgeContent(t.NamedTuple):
    """A Random response from Edge.org's annual questions
    as a named tuple
    """
    question: str
    url: str
    title: str
    content: str

def get_annual_question_links() -> t.List[element.Tag]:
    """Returns a list of BeautifulSoup Tag objects that represent
    the links to every annual question on Edge.org. This should ideally
    be run only once and cached"""
    
    landing = requests.get(LANDING)
    
    links = []
    for link in BeautifulSoup(landing.text, parse_only=SoupStrainer('a'), features="html.parser"):
        if isinstance(link, element.Tag):
            links.append(link)

    annual_questions = list({link for link in links if link.get("href", "").startswith(ANNUAL)})
    assert len(annual_questions) == 22, "There were 22 links when I coded this"
    return annual_questions

def get_contributors_url(question_tag: element.Tag) -> str:
    """Returns the URL of the contributors page for the annual
    question selected from the output of `get_annual_question_links`"""
    question_url = urljoin(BASE, question_tag["href"])
    contrib_url = question_url.replace(ANNUAL, CONTRIB)
    return contrib_url

def get_response_urls(contrib_url: str) -> t.List[t.Tuple[str,str]]:
    """Retruns a list of title, URL pairs to the responses of each contributor
    when the link returned by `get_contributors_url` is provided as
    input"""
    contrib_soup = BeautifulSoup(requests.get(contrib_url).text, features="html.parser")
    entries = contrib_soup.find_all(attrs={"class": "contribution-title"})
    response_urls = list({(entry.text.strip(), urljoin(BASE, entry.find("a")['href'])) for entry in entries})
    return response_urls

def get_response_text(response_url: str) -> t.Tuple[str,str]:
    """Returns the title and text of the response when provided the
    URL of the response as input"""
    body = BeautifulSoup(requests.get(response_url).text, features="html.parser")
    title = body.find(attrs={"class": "response-title"}).text.strip()
    answer = body.find(attrs={"class": "views-field views-field-body"}).text
    return title, answer

def provoke() -> EdgeContent:
    annual_questions = get_annual_question_links()
    question = random.choice(annual_questions)
    contrib_url = get_contributors_url(question)
    response_urls = get_response_urls(contrib_url)
    title, response_url = random.choice(response_urls)
    r_title, content = get_response_text(response_url)
    assert title == r_title
    return EdgeContent(question=question.text, url=response_url, title=title, content=content)