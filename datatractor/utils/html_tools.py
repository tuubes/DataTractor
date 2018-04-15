from typing import Callable

from bs4 import BeautifulSoup, NavigableString
from bs4.element import Tag

headings = ["h1", "h2", "h3", "h4", "h5", "h6"]


def make_hierarchy(html: str, trim: bool):
	soup = BeautifulSoup(html, "lxml")
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
	for heading in headings:
		if tag.find(heading):
			return True
	return False


def flatten(container: Tag, trim: bool):
	for c in container.children:
		if isinstance(c, Tag) and contains_headings(c):
			yield from flatten(c, trim)
		else:
			if trim and isinstance(c, str):
				trimmed = c.strip()
				if len(trimmed) > 0:
					yield NavigableString(trimmed)
			else:
				yield c


class HtmlSection:
	"""Represents a hierarchized part of an HTML document"""

	def __init__(self, level: int, title: str, html_id: str, content: list):
		self.level = level
		self.title = title
		self.html_id = html_id
		self.content = content

	def __str__(self):
		return "HtmlSection(level=%d, id=%s, title=%s, content=%d:%s)" % (
			self.level, self.html_id, self.title, len(self.content), str(self.content).replace("\n", ""))

	def __repr__(self):
		return self.__str__()

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

	def findall(self, f: Callable):
		"""
		Finds all the elements that match the given condition.
		:param f: the condition to check against each element, including the sub-sections
		:return: a generator that returns the maching elements
		"""
		for e in self.content:
			if f(e):
				yield e

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


class HtmlTable:
	"""Represents an HTML table"""

	def __init__(self, rows):
		self.rows = rows

	def __str__(self):
		return "HtmlTable(size=%d, cells=%s)" % (self.cell_count(), list(self.itr_cells()))

	def __repr__(self):
		return self.__str__()

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
		for row in self.rows:
			yield iter(row)

	def itr_columns(self):
		for j in range(0, self.column_count()):
			yield (self.rows[i][j] for i in range(0, self.row_count()))

	def itr_cells(self):
		for i in range(0, self.row_count()):
			for j in range(0, self.column_count()):
				yield self.rows[i][j]

	def find(self, f: Callable):
		for cell in self.itr_cells():
			if f(cell):
				return cell
		return None
