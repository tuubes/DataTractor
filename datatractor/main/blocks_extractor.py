from datatractor.utils.gamepedia_wiki_tools import *
from datatractor.utils.string_tools import *
from datatractor.utils.http_tools import *


def extract_blocks(date_limit: date):
	url = find_revision_url("Java_Edition_data_values/Block_IDs", date_limit)
	ids_html = robust_request(url).text
	soup = BeautifulSoup(ids_html, "lxml")
	blocks = []
	for table_tag in soup.find_all("table"):
		table = parse_table(table_tag, True)
		if get_text(table.get(0, 0)) == "Icon":
			extract_blocks_from_table(date_limit, table, blocks)
	return blocks


def extract_blocks_from_table(date_limit: date, table: HtmlTable, dest: list):
	for row in table.rows[1:]:
		block_id = int(get_text(row[1]))
		block_mc_name = get_text(row[3])
		nice_raw = row[4][0] if isinstance(row[4], list) else row[4]
		block_nice_name = get_text(nice_raw)
		block_page = get_link(row[4])

		if block_page is None:
			print("WARNING - No page found for block '%s' %s %s" % (block_nice_name, block_mc_name, block_id))
			continue

		# Remove sub-parts if any:
		if "#" in block_page:
			block_page = block_page.split("#")[0]
		if block_page.startswith("/"):
			block_page = block_page[1:]

		# Gets the final url:
		block_url = find_revision_url(real_page(block_page), date_limit)

		# DEBUG
		if block_url is None:
			print("WARNING - No url found for block %s, page %s" % (block_mc_name, block_page))
			continue
		else:
			print("Extracting block '%s':'%s' with page %s -> %s" % (
				block_nice_name, block_mc_name, block_page, block_url))

		# Constructs the blog:
		block = gather_block_infos(block_id, block_mc_name, block_nice_name, block_url)
		if block:
			dest.append(block)


def gather_block_infos(block_id, block_mc_name, block_nice_name, block_url):
	details_html = robust_request(block_url).text
	soup = BeautifulSoup(details_html, "lxml")
	sections = make_hierarchy(soup)
	root = sections[0]

	# Gets the block properties
	props = {}
	table_tag = soup.find("table", {"class": "infobox-rows"})
	if table_tag is None:
		print("WARNING: Unable to find the properties of", block_mc_name)
		return None

	props_table = parse_table(table_tag, True)
	for row in props_table.rows:
		prop_name = to_snake_case(get_text(row[0]).strip())
		prop_value = row[1]
		props[prop_name] = prop_value

	# Gets the block hardness
	obtain_section = root.recursive_find(lambda e: isinstance(e, HtmlSection) and e.html_id == "Obtaining")
	obtain_table = obtain_section.find(lambda e: isinstance(e, HtmlTable)) if obtain_section else None
	if obtain_table:
		for row in obtain_table.rows:
			prop_name = get_text(row[0]).strip().lower()
			prop_value = row[1]
			if prop_name == "hardness":
				props["hardness"] = prop_value

	# Gets the data values, if any
	data_values = []
	data_section = root.recursive_find(lambda e: isinstance(e, HtmlSection) and e.html_id == "Block_data")
	data_table = data_section.find(lambda e: isinstance(e, HtmlTable)) if data_section else None
	if data_table:
		first_not_data = (data_table.column_count() > 2 and data_table.get(0, 0) == "")
		value_col = 1 if first_not_data else 0
		desc_col = 2 if first_not_data else 1
		for j in range(0, data_table.column_count()):
			if get_text(data_table.get(0, j)) == "Description":
				desc_col = j
		for row in data_table.rows[1:]:
			value = get_text(row[value_col])
			if value:
				desc = get_text(row[desc_col])
				dv = DataValue(value, desc)
				data_values.append(dv)

	# Constructs a Block object
	return Block(block_id, block_mc_name, block_nice_name, data_values, props)


class Block:
	"""Represents a minecraft block"""

	def __init__(self, numeric_id, string_id, nice_name, values: list, props: dict):
		self.numeric_id = numeric_id
		self.string_id = string_id
		self.nice_name = nice_name
		self.values = values
		self.is_transparent = as_bool(props, "transparency", False)
		self.is_flammable = as_bool(props, "flammable", False)
		self.is_renewable = as_bool(props, "renewable", False)
		self.luminance = as_intbool(props, "luminance", 0, 0)
		self.hardness = as_float(props, "hardness", 0)
		self.blast_resistance = as_float(props, "blast_resistance", 0)
		self.max_stack = as_intbool(props, "stackable", 64, 1)
		tool_prop = props.get("tool", "any tool")
		if isinstance(tool_prop, Tag):
			tool_a = tool_prop.find("a")
			if tool_a is None:
				self.tool = None
			else:
				self.tool = tool_a["href"].replace("/", "").lower()
		else:
			self.tool = None

	def __str__(self):
		return "Block(%s, %s, %s, %s)" % (
			self.nice_name, self.string_id, self.numeric_id, [dv.value for dv in self.values])

	def __repr__(self):
		return self.__str__()  # TODO


class DataValue:
	"""Represents a block data value"""

	def __init__(self, value: str, description: str):
		self.value = value
		self.description = description


def as_bool(p: dict, k: str, default: bool):
	v = get_text(p.get(k))
	if v is None:
		return default
	else:
		return v.strip().lower().startswith("yes")


def as_int(p: dict, k: str, default: int):
	try:
		return int(get_text(p.get(k, "")).strip())
	except:
		return default


def as_float(p: dict, k: str, default: float):
	try:
		return float(get_text(p.get(k), "").strip())
	except:
		return default


def as_intbool(p: dict, k: str, default: int, if_no: int):
	v = get_text(p.get(k))
	if v is None:
		return default
	v = v.strip().lower()
	if v.startswith("no"):
		return if_no
	if "(" in v and ")" in v:
		v = v[v.find("(") + 1:v.find(")")]
	try:
		return int(v)
	except:
		return default
