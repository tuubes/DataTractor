import requests, time

from datatractor.utils.html_tools import *


def extract_blocks(url: str):
	time.sleep(1)
	ids_html = requests.get(url).text
	soup = BeautifulSoup(ids_html, "lxml")
	blocks = []
	for table_tag in soup.find_all("table"):
		table = parse_table(table_tag, True)
		if get_text(table.get(0, 0)) == "Icon":
			extract_blocks_from_table(table, blocks)
	return blocks


def extract_blocks_from_table(table: HtmlTable, dest: list):
	for row in table.rows[1:]:
		block_id = int(get_text(row[1]))
		block_mc_name = get_text(row[3])
		block_nice_name = get_text(row[4])
		block_url = get_link(row[4])
		print("found block: %s %s %s" % (block_id, block_mc_name, block_url))
