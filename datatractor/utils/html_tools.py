from bs4 import BeautifulSoup, element
from typing import Callable

def hierarchize_html(html: str, first_level: int, through_div: bool):
	soup = BeautifulSoup(html, "lxml")

	sections = []
	for h in soup.find_all("h%d" % first_level):
		section = build_hierarchy(h, first_level, through_div)
		sections.append(section)
	return sections


def build_hierarchy(h_tag: element.Tag, h_level: int, through_div: bool):
	h_level_next = h_level + 1
	h_current = "h%d" % h_level
	h_sub = "h%d" % h_level_next

	html_id = h_tag["id"] if h_tag.has_attr("id") else None
	span_tag = h_tag.find("span")
	if span_tag is not None:
		title = span_tag.contents[0]
		if html_id is None:
			html_id = span_tag["id"] if span_tag.has_attr("id") else None
	else:
		title = h_tag.contents[0]

	content = []
	## TODO go through divs that contain h titles and add divs that don't as normal tags
	for tag in h_tag.find_next_siblings():
		if tag.name == h_current:  # end of the section
			break

		if tag.name == h_sub:  # sub-section
			content.append(build_hierarchy(tag, h_level_next, through_div))
		elif tag.name == "div" and through_div: # div
			go_through_div(tag, content)
		else:
			content.append(tag)

	return HtmlSection(h_level, title, html_id, content)


def go_through_div(div: element.Tag, dest: list):
	for tag in div.contents:
		if tag.name == "div":
			go_through_div(tag, dest)
		else:
			dest.append(tag)


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
		return "HtmlSection(level=%d, id=%s, title=%s, content=%d:%s)" % (self.level, self.title, self.html_id, len(self.content), str(self.content).replace("\n", ""))

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
