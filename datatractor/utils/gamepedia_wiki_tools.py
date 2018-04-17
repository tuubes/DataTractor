import re
from datetime import date, datetime

import time
import requests

from datatractor.utils.html_tools import *

wiki_url = "https://minecraft.gamepedia.com"


def extract_release_infos(game_version: str, major_only: bool):
	"""
	Searches release date information on gamepedia.
	:param game_version: the version to look for
	:param major_only: True to inspect only the major versions, eg 1.11 and not 1.11.2
	:return: release_date, next_version, next_date
	"""
	html = requests.get(wiki_url + "/Java_Edition_version_history").text
	root = make_hierarchy(html)[0]
	next_version = None
	next_date = date.today()
	date_format = "%B %d, %Y"
	for table in root.recursive_findall(lambda e: isinstance(e, HtmlTable)):
		if table.column_count() == 2 and table.get(0, 0) == "Version":
			if major_only:
				rows = table.rows[table.row_count() - 1:]
			else:
				rows = table.rows[1:]  # skips header
			for row in rows:
				version = re.sub("\(.*?\)", "", get_text(row[0])).strip()
				release_date = datetime.strptime(get_text(row[1]), date_format).date()
				if version == game_version:
					return release_date, next_version, next_date
				else:
					next_version = version
					next_date = release_date
	return None, None, None  # not found


def get_revision_url(page_title: str, after_date: date, before_date: date):
	"""
	Searches the most up-to-date revision of the given page between the given dates.
	:param page_title: the page to search
	:param after_date: the date to search after
	:param before_date: the date to search before
	:return: the URL pointing to the corresponding revision of the page, or None if not found
	"""
	history_url = "%s/index.php?title=%s&action=history&year=%s&month=%s&tagfilter=" % (
		wiki_url, page_title, before_date.year, before_date.month)
	html = requests.get(history_url).text
	soup = BeautifulSoup(html, "lxml")
	date_format = "%H:%M, %d %B %Y"

	for revision in soup.find_all("a", {"class": "mw-changeslist-date"}):
		revision_date = datetime.strptime(get_text(revision), date_format).date()
		# DEBUG print(page_title, revision_date)
		if after_date < revision_date < before_date:
			link = revision["href"]
			return (wiki_url + link) if link.startswith("/") else link
	return None
