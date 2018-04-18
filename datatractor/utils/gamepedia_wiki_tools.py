import re
from datetime import date, datetime

from datatractor.utils.html_tools import *
from datatractor.utils.http_tools import *

wiki_url = "https://minecraft.gamepedia.com"
redirections = {
	"Flowers": "Flower",
	"Iron_Door": "Door",
	"Sugar_Cane": "Sugar_Canes",
	"Oak_Fence": "Fence",
	"Nether_Brick_Fence": "Fence",
	"Stained_Glass": "Glass",
	"Slabs": "Slab",
	"Weighted_Pressure_Plate": "Pressure_Plate",
	"Stained_Clay": "Terracotta",
	"Hardened_Clay": "Terracotta",
	"Stained_Glass_Pane": "Glass_Pane",
	"Iron_Trapdoor": "Trapdoor",
	"Oak Trapdoor": "Trapdoor",
	"Red_Sandstone": "Sandstone",
	"Repeating_Command_Block": "Command_Block",
	"Chain_Command_Block": "Command_Block",
	"Red_Nether_Brick": "Nether_Brick",
	"Structure_Void": "Structure Block",
}

_colors = ["White", "Orange", "Magenta", "Green", "Cyan", "Blue", "Light_Blue", "Yellow", "Red", "Purple", "Pink", "Lime", "Gray", "Light_Gray", "Brown", "Black"]

def redirect_many(pattern: str, redirect: str, values: list):
	for v in values:
		key = pattern.replace("$", v)
		redirections[key] = redirect

redirect_many("$_Shulker_Box", "Shulker_Box", _colors)
redirect_many("$_Glazed_Terracotta", "Glazed_Terracotta", _colors)

def extract_release_infos(game_version: str, major_only: bool):
	"""
	Searches release date information on gamepedia.
	:param game_version: the version to look for
	:param major_only: True to inspect only the major versions, eg 1.11 and not 1.11.2
	:return: release_date, next_version, next_date
	"""
	soup = robust_soup(page_url("Java_Edition_version_history"))
	root = make_hierarchy(soup)[0]
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
				if major_only:
					split = version.split(".")
					if len(split) > 2:
						version = ".".join(split[:2])
				release_date = datetime.strptime(get_text(row[1]), date_format).date()
				if version == game_version:
					return release_date, next_version, next_date
				else:
					next_version = version
					next_date = release_date
	return None, None, None  # not found


def find_revision_url(page_title: str, before_date: date):
	"""
	Searches the most up-to-date revision of the given page before the given date.
	:param page_title: the page to search
	:param before_date: the date to search before
	:return: the URL pointing to the corresponding revision of the page, or None if not found
	"""
	if page_title.startswith("/"):
		page_title = page_title[1:]
	if page_title.endswith("/"):
		page_title = page_title[:-1]
	history_url = "%s/index.php?title=%s&action=history&year=%s&month=%s&tagfilter=" % (
		wiki_url, page_title, before_date.year, before_date.month)
	html = robust_request(history_url).text
	# This request sometimes returns an empty string, for no apparent reason.
	# In that case, we clear the cache and do the request again. This is done by robust_request()
	soup = BeautifulSoup(html, "lxml")
	date_format = "%H:%M, %d %B %Y"

	for revision in soup.find_all("a", {"class": "mw-changeslist-date"}):
		revision_date = datetime.strptime(get_text(revision), date_format).date()
		# DEBUG print(page_title, revision_date)
		if revision_date < before_date:
			return page_url(revision["href"])
	return None


def real_page(page_title: str):
	return redirections.get(page_title, page_title)


def page_url(page_title: str):
	sep = "" if page_title.startswith("/") else "/"
	return wiki_url + sep + page_title
