"""Fork of googlesearch, a pip package."""
import urllib
import logging
import json
import openai
import os
from bs4 import BeautifulSoup
from requests import get, Response, exceptions
from .user_agents import get_useragent
from utils.proxyhandler import get_proxy, get_proxy_list_length, remove_proxy, refresh_proxies, get_one_proxy

# Global variables
USE_FREE_PROXIES = os.environ.get("USE_FREE_PROXIES", 'true').lower() == 'true'
PAID_PROXY_API = os.environ.get("PAID_PROXY_API", "http://scraperapi:efa4f8b93620a48d98940d13c3a6a631@proxy-server.scraperapi.com:8001")
OPEN_AI_KEY = os.environ.get("OPEN_AI_KEY")


# Logging configuration
if not os.path.exists('logs'):
    os.makedirs('logs', exist_ok=True)
    open('logs/error.log', 'a').close()

logging.basicConfig(level=logging.ERROR, datefmt='%d-%b-%y %H:%M:%S', filename='logs/error.log')

###
## Classes
class SearchResult:
    def __init__(self, url, title, description):
        self.url = url
        self.title = title
        self.description = description

    def __repr__(self):
        return f"SearchResult(url={self.url}, title={self.title}, description={self.description})"


####
## Functions
def _error_resp(message, status_code):
    res = Response()
    res.message = message
    res.status_code = status_code
    return res

def _req(term, results, lang, start,timeout, is_retry=False, proxy=None):
    if get_proxy_list_length() == 0:
        refresh_proxies()
    proxies = get_proxy()
    try:
        resp = get(
            url="http://www.google.com/search",
            headers={
                "User-Agent": get_useragent(),
            },
            params={
                "q": term,
                "num": results + 2,  # Prevents multiple requests
                "hl": lang,
                "start": start,
            },
            proxies={
                "http": (proxy if proxy else (USE_FREE_PROXIES is True and proxies['proxy']) or PAID_PROXY_API)
            },
            timeout=timeout,
        )
        resp.raise_for_status()
        return resp
        
    except exceptions.ProxyError as e:
        # If paid proxy is down
        if (USE_FREE_PROXIES is False):
            message = "Proxy server is down."
            logging.error(message)
            return _error_resp(message, 500)
        remove_proxy(proxies['index'])
        logging.error(f"Proxy {proxies['proxy']} is down.")
        ## If no more proxies, get more proxies
        if get_proxy_list_length() == 0:
            # Enhancement: Send alert
            logging.error("No more proxies available.")
            refresh_proxies()
        return _req(term, results, lang, start,timeout, is_retry=1)
        
    except exceptions.Timeout as e:
        if (is_retry ==1):
            logging.error("Request timed out.")
            print("Request timed out.")
            return _error_resp("Request timed out.", 500)
        return _req(term, results, lang, start,timeout, is_retry=1)

    except exceptions.HTTPError as e:
        if (e.response.status_code == 429):
            logging.error(f"Proxy {proxies['proxy']} has been banned by Google.")
            remove_proxy(proxies['index'])
            ## If no more proxies, get more proxies
            if get_proxy_list_length() == 0:
                # Enhancement: Send alert
                message = "No more proxies available."
                logging.error(message)
                print(message)
                refresh_proxies()
            if (is_retry ==1):
                proxy_url = get_one_proxy()
                if proxy_url:
                    return _req(term, results, lang, start,timeout, is_retry=2, proxy=proxy_url)
                else:
                    message = "No more proxies available."
                    print(message)
                    logging.error(message)
                    return _error_resp(message, 500)
            if (is_retry == 2):
                message = "Request failed with retry."
                print(message)
                logging.error(message)
                return _error_resp(message, 500)
            return _req(term, results, lang, start,timeout, is_retry=1)
        else:
            logging.error(e)
            return _error_resp(e,500)
    except Exception as e:        
        logging.error(e)
        return _error_resp(e,500)

def search(term, num_results=10, lang="en", page=1, sleep_interval=0, timeout=30, advanced=False):
    """Search the Google search engine with pagination support
        term: Term to search for
        num_results: Number of results to return
        lang: Language
        proxy: Proxy
        page: Page number
        sleep_interval: Sleep between requests
        timeout: Timeout
        advanced: Return advanced object( SearchResults(url, title, description) )
    
    """

    escaped_term = urllib.parse.quote_plus(term) # make 'site:xxx.xxx.xxx ' works.

    # Initialize start and end pages
    start = (page - 1) * num_results
    end = page * num_results

    # Fetch and paginate
    while start < end:
        # Send request
        resp = _req(escaped_term, num_results, lang, start, timeout)
        if resp.status_code != 200:
            return {
                "error": resp.message,
                "status_code": resp.status_code,
            }

        # Parse
        soup = BeautifulSoup(resp.text, "html.parser")
        result_block = soup.find_all("div", attrs={"class": "g"})
        try:
            for result in result_block:
                # Find link, title, description
                    link = result.find("a", href=True)
                    title = result.find("h3")
                    description_box = result.find("div", {"style": "-webkit-line-clamp:2"})
                    if description_box:
                        description = description_box.text
                        if link and title and description:
                            start += 1
                            if advanced:
                                yield SearchResult(link["href"], title.text, description)
                            else:
                                yield link["href"]
        except Exception as e:
            logging.error(e)
            return None

        # Sleep between requests (if sleep_interval is specified)
        if sleep_interval > 0 and start < end:
            sleep(sleep_interval)

def get_meta_information(url, timeout=10):
    try:
        resp = get(url, timeout=timeout)
        resp.raise_for_status()
        soup = BeautifulSoup(resp.text, "html.parser")
        
        # Extract meta information
        meta_title = soup.find("title")
        meta_description = soup.find("meta", attrs={"name": "description"})
        meta_keywords = soup.find("meta", attrs={"name": "keywords"})
        
        return {
            "meta_title": meta_title.text if meta_title else None,
            "meta_description": meta_description["content"] if meta_description else None,
            "meta_keywords": meta_keywords["content"] if meta_keywords else None,
        }
    except Exception as e:
        return {
            "meta_title": None,
            "meta_description": None,
            "meta_keywords": None,
        }

def generate_new_data_from_gpt3(num_data = 2, result_data = []):
    openai.api_key = OPEN_AI_KEY
    response = openai.ChatCompletion.create(
        model="gpt-3.5-turbo-0613",
        messages=[{
                'role': 'system',
                'content': 'You will be provided with a array of data. You need to generate 2 new data blocks based on the given data. The data should be in the same format as the given data. The data should be unique and should not be present in the given data. The data should be relevant to the given data. Expected output: [{"meta_title": "title", "meta_description": "description", "meta_keywords": "keywords"}, {"meta_title": "title", "meta_description": "description", "meta_keywords": "keywords"}]'
            },
            {
                'role': 'user',
                'content': json.dumps(result_data)
            }
        ],
        temperature=0.8,
        max_tokens=1000,
        
    )
    return response

    
