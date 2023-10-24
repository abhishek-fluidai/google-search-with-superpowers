import random
import threading
import queue
from bs4 import BeautifulSoup
import requests
import logging

# Logging configuration
if not os.path.exists('logs'):
    os.makedirs('logs', exist_ok=True)
    open('logs/error.log', 'a').close()

logging.basicConfig(level=logging.ERROR, format='%(asctime)s - %(levelname)s - %(message)s', datefmt='%d-%b-%y %H:%M:%S', filename='logs/error.log')

# get proxies from file
proxies = []
with open('utils/valid_proxies.txt', 'r') as f:
    proxies = f.read().split('\n')
    if '' in proxies:
        proxies.remove('')

# select random proxy
def get_proxy():
    # select a random proxy with index 
    proxy_index = random.randint(0, len(proxies)-1)
    return {
        'index': proxy_index,
        'proxy': proxies[proxy_index]
    }

def get_proxy_list_length():
    return len(proxies)

def remove_proxy(index):
    with open('utils/valid_proxies.txt', 'w') as f:
        f.write('')
    proxies.pop(index)
    with open('utils/valid_proxies.txt', 'a') as f:
        for p in proxies:
            f.write(p + '\n')

def get_one_proxy():
    try:
        res = requests.get('https://free-proxy-list.net/')
        soup = BeautifulSoup(res.text, 'html.parser')
        table = soup.find('tbody')

        for row in table.find_all('tr'):
            cols = row.find_all('td')
            if cols[5].text == 'yes':
                url = cols[0].text + ':' + cols[1].text
                isValid = check_proxy(url)
                if isValid:
                    proxies.append(url)
                return url
        return False
    except Exception as e:
        print(e)
        logging.error(e)
        return False

def refresh_proxies():
    valid_proxies = []
    try:
        res = requests.get('https://free-proxy-list.net/')
        soup = BeautifulSoup(res.text, 'html.parser')
        table = soup.find('tbody')

        for row in table.find_all('tr'):
            cols = row.find_all('td')
            if cols[5].text == 'yes':
                url = cols[0].text + ':' + cols[1].text
                isValid = check_proxy(url)
                if isValid:
                    valid_proxies.append(url)
                    print(f'Valid proxy: {url}')

        with open('utils/valid_proxies.txt', 'w') as f:
            f.write('')
        with open('utils/valid_proxies.txt', 'a') as f:
            for p in valid_proxies:
                f.write(p + '\n')
        proxies = valid_proxies
        if len(valid_proxies) == 0:
            return False
        return True
    except Exception as e:
        print(e)
        logging.error(e)
        return False

# check if proxies are valid
def check_proxy(url):
    try:
        r = requests.get('http://google.com/search?q=test', proxies={
            'http': url}, timeout=10)
    except:
        return False
    if r.status_code == 200:
        return True
