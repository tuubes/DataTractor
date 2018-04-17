import requests

from datatractor.utils.html_tools import *


def print_sections(sections):
	for section in sections:
		print(section)
		for sub in section.subs():
			print(">>>", sub)
	print("---------------------")


html = """
<body>
<h1>Main Title</h1>
<h2>H2</h2>
<h3>H3</h3>
This is in the sub-section

<div><div id="body">

<h2>Title 1</h2>
This is some text.
<div>This is a div</div>

<h3>SubTitle</h3>
This is in the sub-section

<h2>Title 2</h2>
This is more text.
<div><div><div><span>hello</span></div></div></div>
</div></div>
</body>
"""
sections = make_hierarchy(html, True)
print_sections(sections)

protocol_html = requests.get("http://wiki.vg/Protocol").text
sections = make_hierarchy(protocol_html, True)
print_sections(sections)

s1 = sections[0]
search_level = 4
print("Identified H%ds:" % search_level)
for h in s1.recursive_findall(lambda e: isinstance(e, HtmlSection) and e.level == search_level):
	print("%s : \"%s\"" % (str(h.html_id).center(42), h.title))
	for t in h.recursive_findall(lambda e: isinstance(e, HtmlTable)):
		print(t)
		for row in t.itr_rows():
			l = list(row)
			print("row:", len(l), ":", l)
		print("cells:", list(t.itr_cells()))

print("---------------------")
l = [["a", "b", "c"], [0, 1, 2], [3, 4, 5], [6, 7, 8]]
table = HtmlTable(l)
print("table:", table)
print("cells:", list(table.itr_cells()))
for row in table.itr_rows():
	print("row:", list(row))
for column in table.itr_columns():
	print("column:", list(column))
