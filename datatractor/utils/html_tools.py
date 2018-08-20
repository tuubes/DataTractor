from typing import Callable, List

from bs4 import BeautifulSoup, NavigableString
from bs4.element import Tag

from utils.string_tools import pretty_matrix_str

headings = ["h1", "h2", "h3", "h4", "h5", "h6"]


def get_text(element, joiner=" "):
	if element is None:
		return None
	elif isinstance(element, HtmlCell):
		return get_text(element.content)
	elif isinstance(element, list):
		if len(element) == 1:
			return get_text(element[0])
		else:
			return joiner.join((v for v in (get_text(e) for e in element) if v is not None))
	elif isinstance(element, Tag):
		return get_text(element.contents)
	else:
		return str(element)


def get_link(element):
	if element is None:
		return None
	elif isinstance(element, HtmlCell):
		return get_link(element.content)
	elif isinstance(element, list):
		for e in element:
			link = get_link(e)
			if link is not None:
				return link
		return None
	elif isinstance(element, Tag) and element.has_attr("href"):
		return element["href"]
	else:
		return None


def make_hierarchy(soup: BeautifulSoup, trim: bool = True):
	"""Organizes an HTML document according to its headings (h1, h2, etc.)."""
	itr = flatten(soup.find("body"), trim)
	sections = []

	next_heading = None
	for tag in itr:
		if tag.name in headings:
			next_heading = tag
			break

	while next_heading:
		level, html_id, title = inspect_heading(next_heading)
		section, next_heading = make_section(itr, level, html_id, title)
		sections.append(section)

	return sections


def make_section(itr, level, html_id, title):
	"""Creates an HtmlSection whose content starts at the next tag given by itr."""
	content = []
	next_tag = next(itr, None)
	while next_tag:
		if next_tag.name in headings:
			next_level, next_html_id, next_title = inspect_heading(next_tag)
			if next_level <= level:
				break
			else:
				section, next_tag = make_section(itr, next_level, next_html_id, next_title)
				content.append(section)
		else:
			content.append(next_tag)
			next_tag = next(itr, None)

	return HtmlSection(level, title, html_id, content), next_tag


def inspect_heading(h: Tag):
	"""Extracts the informations about an html heading tag."""
	level = int(h.name[1])  # for ex. gets the "2" in "h2"
	html_id = None
	title = None
	if h.has_attr("id"):
		html_id = h["id"]
	if len(h.contents) > 0:
		c0 = h.contents[0]
		if isinstance(c0, Tag):  # if we have for ex. <h2><span id="some_id">some name</span></h2>
			if html_id is None and c0.has_attr("id"):
				html_id = c0["id"]
			if len(c0.contents) > 0:
				title = c0.contents[0]
		else:
			title = c0
	return level, html_id, title


def contains_headings(tag: Tag):
	"""Returns true if the tag contains an html heading."""
	for heading in headings:
		if tag.find(heading):
			return True
	return False


def contains_table(tag: Tag):
	"""Returns true if the tag contains an html table."""
	return tag.find("table")


def contains_list(tag: Tag):
	"""Returns true if the tag contains an html list."""
	return tag.find(["ol", "ul"])


def flatten(container: Tag, trim: bool):
	"""Iterates over the children of the container, flattening the <div> tags and parsing the <table> tags."""
	for c in container.children:
		is_tag = isinstance(c, Tag)
		if is_tag and (contains_headings(c) or contains_table(c)):
			yield from flatten(c, trim)
		elif is_tag and c.name == "table":
			yield parse_table(c, trim)
		elif is_tag and c.name in ["ol", "ul"]:
			yield parse_list(c, trim)
		else:
			if trim and isinstance(c, str):
				trimmed = c.strip()
				if len(trimmed) > 0:
					yield NavigableString(trimmed)
			else:
				yield c


def parse_list(list: Tag, trim: bool):
	"""Parses a <ol></ol> or <ul></ul> and produces an HtmlList."""
	elements = []
	ordered = (list.name == "ol")
	for e in list.find_all("li"):
		inside = e.contents
		if isinstance(inside, List) and len(inside) == 1:
			inside = inside[0]
		if isinstance(inside, Tag):
			if inside.name in ["ol", "ul"]:
				elements.append(parse_list(inside, trim))
				continue
			elif inside.name == "table":
				elements.append(parse_table(inside, trim))
				continue
		if trim and isinstance(e, str):
			trimmed = e.strip()
			if len(trimmed) > 0:
				elements.append(NavigableString(trimmed))
		else:
			elements.append(get_text(inside))
	return HtmlList(elements, ordered)


def parse_table(table: Tag, trim: bool):
	"""Parses a <table></table> and produces an HtmlTable."""
	# First, we need to construct the arrays with the right number of rows and columns, in order to
	# make the rowspan and colspan work
	row_count = 0
	col_count = 0
	for tr in table.find_all("tr"):
		row_count += 1
		if row_count == 1:
			for td in tr.find_all(["th", "td"]):
				if td.has_attr("colspan"):
					col_count += int(td["colspan"])
				else:
					col_count += 1

	rows: List[List[HtmlCell]] = []
	for i in range(0, row_count):
		row = [None] * col_count
		rows.append(row)

	# Then we can fill the arrays with the cells' content
	tr: Tag
	td: Tag
	i: int = 0  # row index
	for tr in table.find_all("tr"):
		j: int = 0  # column index
		for td in tr.find_all(["th", "td"]):
			# Skips already populated cells, eg by rowspan or colspan
			while (j < col_count) and (rows[i][j] is not None):
				j += 1

			# Remembers if it's a tr or th
			is_header = (td.name == "th")
			# Gets cell content and trims it if required
			cell_content: List = td.contents
			if trim:
				clean_cell = []
				for e in cell_content:
					if isinstance(e, str):
						trimmed = e.strip()
						if len(trimmed) > 0:
							clean_cell.append(NavigableString(trimmed))
					else:
						clean_cell.append(e)
				cell_content = clean_cell

			if len(cell_content) == 0:
				cell_content = None
			elif len(cell_content) == 1:
				cell_content = cell_content[0]

			# Populates the cell(s) and respects rowspan and colspan if present
			ispan = int(td["rowspan"]) if td.has_attr("rowspan") else 1
			jspan = int(td["colspan"]) if td.has_attr("colspan") else 1
			ispan = max(ispan, 1)  # fix values <= 0
			jspan = max(jspan, 1)  # fix values <= 0
			if ispan == jspan == 1:
				rows[i][j] = HtmlCell(cell_content, is_header)
			else:
				ref = BigCell(cell_content, is_header, ispan, jspan)
				for xi in range(i, min(i + ispan, row_count)):
					for xj in range(j, min(j + jspan, col_count)):
						if xi == i and xj == j:
							rows[xi][xj] = ref
						else:
							rows[xi][xj] = RefCell(ref)

			j += jspan
		i += 1
	return HtmlTable(rows)


class HtmlSection:
	"""Represents a hierarchized part of an HTML document"""

	def __init__(self, level: int, title: str, html_id: str, content: List[Tag]):
		self.level = level
		self.title = title
		self.html_id = html_id
		self.content = content

	def __str__(self):
		return "HtmlSection(level=%d, id=%s, title=%s, content_length=%d)" % (
			self.level, self.html_id, self.title, len(self.content))

	def __repr__(self):
		return "HtmlSection(level=%d, id=%s, title=%s, content=%d:%s)" % (
			self.level, self.html_id, self.title, len(self.content), str(self.content).replace("\n", ""))

	def recursive_content(self):
		"""
		Recursively iterates over the content of this section, its sub-sections, etc.
		:return: a recursive generator of the elements
		"""
		for e in self.content:
			if isinstance(e, HtmlSection):
				yield from e.recursive_content()
			else:
				yield e

	def find(self, f: Callable):
		"""
		Finds the first element that matches the given condition.
		:param f: the condition to check against each element, including the sub-sections
		:return: the first element that matches, or None
		"""
		for e in self.content:
			if f(e):
				return e
		return None

	def find_i(self, f: Callable):
		"""
		Finds the first element that matches the given condition;
		:param f: the condition to check against each element, including the sub-sections
		:return: the first element that matches and its index, or (None, -1) if not found
		"""
		for (i, e) in enumerate(self.content):
			if f(e):
				return e, i
		return None, -1

	def findall(self, f: Callable):
		"""
		Finds all the elements that match the given condition.
		:param f: the condition to check against each element, including the sub-sections
		:return: a generator that returns the maching elements
		"""
		for e in self.content:
			if f(e):
				yield e

	def findall_i(self, f: Callable):
		"""
		Finds all the elements that match the given condition.
		:param f: the condition to check against each element, including the sub-sections
		:return: a generator that returns the maching elements with their indexes, as (elem, index) tuples
		"""
		for (i, e) in enumerate(self.content):
			if f(e):
				yield e, i

	def recursive_find(self, f: Callable):
		"""
		Recursively finds the first element that match the given condition.
		:param f: the condition to check against each element, including the sub-sections
		:return: the first element that matches, or None
		"""
		for e in self.content:
			if f(e):
				return e
			elif isinstance(e, HtmlSection):
				rec = e.recursive_find(f)
				if rec:
					return rec
		return None

	def recursive_findall(self, f: Callable):
		"""
		Recursively finds all the elements that match the given condition.
		:param f: the condition to check against each element, including the sub-sections
		:return: a generator that returns the maching elements
		"""
		for e in self.content:
			if f(e):
				yield e
			elif isinstance(e, HtmlSection):
				yield from e.recursive_findall(f)

	def subs(self):
		"""
		Iterates over all the sub-sections of this section.
		:return: an iterator of the sub-sections
		"""
		return self.findall(lambda e: isinstance(e, HtmlSection))

	def tags(self):
		"""
		Iterates over all the non-sections tags in this section.
		:return: an iterator of the non-sections tags
		"""
		return self.findall(lambda e: not isinstance(e, HtmlSection))

	def sub_id(self, html_id: str):
		"""Finds the sub-section with the given id."""
		return self.find(lambda e: isinstance(e, HtmlSection) and e.html_id == html_id)

	def sub_title(self, title: str):
		"""Finds the sub-section with the given title."""
		return self.find(lambda e: isinstance(e, HtmlSection) and e.title == title)


class HtmlCell:
	"""A cell in a table"""

	def __init__(self, content, is_header):
		self.content = content
		self.is_header = is_header

	def __str__(self) -> str:
		prefix = "$" if self.is_header else ""
		content = "ø" if self.is_empty() else f"\"{self.content}\""
		return f"{prefix}HtmlCell {content}"

	def __repr__(self):
		return str(self)

	def column_count(self) -> int:
		return 1

	def row_count(self) -> int:
		return 1

	def is_up_ref(self) -> bool:
		return False

	def is_left_ref(self) -> bool:
		return False

	def is_vertical(self) -> bool:
		return self.row_count() > 1

	def is_horizontal(self) -> bool:
		return self.column_count() > 1

	def is_empty(self) -> bool:
		return self.content is None


class BigCell(HtmlCell):
	"""
	A cell that lies in several rows and/or columns.
	The BigCell is stored in its first table cell, the other occupied cells are filled with RefCells.
	"""

	def __init__(self, content, is_header, rowspan, colspan):
		super().__init__(content, is_header)
		self.rowspan = rowspan
		self.colspan = colspan

	def __str__(self) -> str:
		prefix = "$" if self.is_header else ""
		content = "ø" if self.is_empty() else f"\"{self.content}\""
		return f"{prefix}BigCell({self.rowspan}x{self.colspan}) {content}"

	def __repr__(self):
		return str(self)

	def column_count(self):
		return self.colspan

	def row_count(self):
		return self.rowspan


class RefCell(HtmlCell):
	"""Reference to a BigCell"""

	def __init__(self, ref: BigCell):
		super().__init__(ref.content, ref.is_header)
		self.ref = ref

	def __str__(self) -> str:
		prefix = "$" if self.is_header else ""
		if self.is_up_ref():
			if self.is_left_ref():
				arrow = "<^"
			else:
				return f"^{prefix}RefCell{prefix}^"
		elif self.is_left_ref():
			arrow = "<-"
		else:
			arrow = "??"
		suffix = "ø" if self.ref.is_empty() else ""
		return f"{arrow}{prefix}RefCell {suffix}"

	def __repr__(self):
		return str(self)

	def is_up_ref(self):
		return self.ref.row_count() > 1  # ref cell is vertical

	def is_left_ref(self):
		return self.ref.column_count() > 1  # ref cell is horizontal


class HtmlTable:
	"""Represents an HTML table"""

	def __init__(self, rows: List[List[HtmlCell]]):
		self.rows = rows

	def __str__(self):
		return f"HtmlTable {self.row_count()}x{self.column_count()} \n{pretty_matrix_str(self.rows)}"

	def __repr__(self):
		return str(self)

	@property
	def name(self):
		return None

	def get(self, row, column):
		return self.rows[row][column]

	def row_count(self):
		return len(self.rows)

	def column_count(self):
		if self.row_count() > 0:
			return len(self.rows[0])
		else:
			return 0

	def cell_count(self):
		return self.row_count() * self.column_count()

	def itr_rows(self):
		"""Iterates over the rows"""
		for row in self.rows:
			yield iter(row)

	def itr_columns(self):
		"""Iterates over the columns"""
		for j in range(0, self.column_count()):
			yield (self.rows[i][j] for i in range(0, self.row_count()))

	def itr_cells(self):
		"""Iterates over the cells, row by row"""
		for i in range(0, self.row_count()):
			for j in range(0, self.column_count()):
				yield self.rows[i][j]

	def find_cell(self, f: Callable):
		"""Finds the first cell that satisfies the given condition."""
		for cell in self.itr_cells():
			if f(cell):
				return cell
		return None

	def find_row(self, f: Callable):
		"""Finds the first row that satisfies the given condition."""
		for row in self.rows:
			if f(row):
				return row
		return None


class HtmlList:
	"""Represents an HTML list, ordered or unordered"""

	def __init__(self, elements: list, ordered: bool):
		self.elements = elements
		self.is_ordered = ordered

	def __str__(self):
		return f"HtmlList{str(self.elements)}"

	def __repr__(self):
		return str(self)

	@property
	def name(self):
		return None
