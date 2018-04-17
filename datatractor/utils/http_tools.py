import requests
import requests_cache
import time
from bs4 import BeautifulSoup


def robust_request(url: str, retry_interval=0.0, retry_max=20):
	response = requests.get(url)
	with requests_cache.disabled():
		retry_count = 0
		while response.status_code == 200 and not response.text and retry_count < retry_max:
			time.sleep(retry_interval)
			response = requests.get(url)
			retry_count += 1
	return response


def robust_soup(url: str, retry_interval=0.0, retry_max=20):
	return BeautifulSoup(robust_request(url, retry_interval, retry_max).text, "lxml")
