from typing import Callable

from bs4 import BeautifulSoup, NavigableString
from bs4.element import Tag

headings = ["h1", "h2", "h3", "h4", "h5", "h6"]


def make_hierarchy(html: str):
	soup = BeautifulSoup(html, "lxml")
	itr = flatten(soup.find("body"))
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
			print("next: ", next_level, next_title, "- current: ", level)
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


def flatten(container: Tag):
	for c in container.children:
		if not isinstance(c, NavigableString) and contains_headings(c):
			yield from flatten(c)
		else:
			yield c


class HtmlSection:
	"""
	Represent a hierarchized part of an HTML document.
	"""

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

	def find_sub(self, f: Callable):
		"""
		Finds the first sub-section that matches the given condition.
		:param f: the condition to check against each sub-section
		:return: the first sub-section that matches, or None
		"""
		return self.find(lambda e: isinstance(e, HtmlSection) and f(e))

	def findall_subs(self, f: Callable):
		"""
		Finds all the sub-sections that match the given condition.
		:param f: the condition to check against each sub-section
		:return: a generator that returns the maching sections
		"""
		return self.findall(lambda e: isinstance(e, HtmlSection) and f(e))

	def find_tag(self, f: Callable):
		"""
		Finds the first non-section tag that matches the given condition.
		:param f: the condition to check against each tag
		:return: the first non-section tag that matches, or None
		"""
		return self.find(lambda e: not isinstance(e, HtmlSection) and f(e))

	def findall_tags(self, f: Callable):
		"""
		Finds all the non-section tags that match the given condition.
		:param f: the condition to check against each tag
		:return: a generator that returns the maching tags
		"""
		return self.findall(lambda e: not isinstance(e, HtmlSection) and f(e))

	def subs(self):
		"""
		Constructs a list of all the sub-sections of this section.
		:return: a list containing the sub-sections of this section
		"""
		return self.findall(lambda e: isinstance(e, HtmlSection))

	def tags(self):
		"""
		Constructs a list of all the non-sections tags in this section.
		:return: a list containing the non-sections tags in this section
		"""
		return self.findall(lambda e: not isinstance(e, HtmlSection))
