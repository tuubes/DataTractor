import requests
from datatractor.utils.html_tools import *


def print_sections(sections):
	for section in sections:
		for c in section.content:
			print(type(c), ":", str(c).replace("\n", "").strip())


html = """
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
"""
sections = hierarchize_html(html, 1)
print_sections(sections)

#protocol_html = requests.get("http://wiki.vg/Protocol").text
#sections = hierarchize_html(protocol_html, 1)
#print_sections(sections)