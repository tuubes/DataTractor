import requests
from datatractor.utils.html_tools import *

## TEST ##
html = requests.get("http://wiki.vg/Protocol").text
sections = hierarchize_html(html, 2, True)
for section in sections:
	print(section)
	for e in section.content:
		print(str(e).replace("\n", ""))
	print("========================")
