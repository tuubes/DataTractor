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
