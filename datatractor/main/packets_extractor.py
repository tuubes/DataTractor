import requests

from datatractor.utils.html_tools import *
from datatractor.main.packets_data import *


def extract_packets(game_version: str):
	"""Extracts packet data from wiki.vg"""
	print("Looking for the documentation of protocol", game_version, "...")
	url, protocol_number = find_documentation(game_version)

	if url is None:
		print("No result found!")
		return None

	print("Found url:", url)
	print("Protocol number:", protocol_number)

	print("Downloading the documentation...")
	protocol_html = requests.get(url).text

	print("Organizing the data...")
	soup = BeautifulSoup(protocol_html, "lxml")
	sections = make_hierarchy(soup)
	root = sections[0]

	print("Analysing the protocol...")
	protocol = extract_protocol(root, game_version, protocol_number)
	return protocol


def find_documentation(game_version: str):
	html = requests.get("http://wiki.vg/Protocol_version_numbers").text
	root = make_hierarchy(BeautifulSoup(html, "lxml"))[0]
	for table in root.recursive_findall(lambda e: isinstance(e, HtmlTable)):
		for row in table.row_count[1:]:
			release_name = get_text(row[0])
			protocol = get_text(row[1])
			try:
				protocol_number = int(protocol)
			except:
				protocol_number = None
			doc_link = get_link(row[2])
			if (release_name == game_version) and (doc_link is not None) and (protocol_number is not None):
				url = doc_link
				if url[0] == "/":
					url = "%s%s" % ("http://wiki.vg", url)

				return url, protocol_number
	return None, None


def extract_protocol(root: HtmlSection, game_version: str, protocol_number: int):
	s_handshake = root.sub_id("Handshaking")
	s_play = root.sub_id("Play")
	s_status = root.sub_id("Status")
	s_login = root.sub_id("Login")

	p_handshake = extract_subprotocol(s_handshake)
	p_play = extract_subprotocol(s_play)
	p_status = extract_subprotocol(s_status)
	p_login = extract_subprotocol(s_login)

	return Protocol(game_version, protocol_number, p_handshake, p_play, p_status, p_login)


def extract_subprotocol(s: HtmlSection):
	subprotocol_name = s.title
	s_clientbound = s.sub_title("Clientbound")
	s_serverbound = s.sub_title("Serverbound")

	cb = [] if (s_clientbound is None) else [extract_packet(section) for section in s_clientbound.subs()]
	sb = [] if (s_serverbound is None) else [extract_packet(section) for section in s_serverbound.subs()]
	return SubProtocol(subprotocol_name, cb, sb)

def extract_packet(section: HtmlSection):
	table: HtmlTable = section.find(lambda e: isinstance(e, HtmlTable))
	packet_name = section.title
	packet_id = table.get(1, 0)
	packet_fields = []
	print("----------------------------------------")
	print(packet_name)
	print(packet_id)
	print(table)
	# Analyses the header
	name_col = None
	type_col = None
	comment_col = None
	comment_cols = []
	for j in range(table.column_count() - 1, -1, -1):
		cell = table.get(0, j)
		if cell.lower() == "field name":
			if name_col is None:
				name_col = j
			else:
				# adds any additional information as a comment:
				comment_cols.append(j)
		if (cell.lower() == "field type") and (type_col is None):
			type_col = j
		if (cell.lower() == "notes") and (comment_col is None):
			comment_col = j

	name_col = 3 if (name_col is None) else name_col
	type_col = 4 if (type_col is None) else type_col
	comment_col = 5 if (comment_col is None) else comment_col
	comment_cols.append(comment_col)

	# Parses the table
	for row in table.row_count[1:]:  # [1:] to skip the header
		field_name = get_text(row[name_col])
		field_type = get_text(row[type_col])
		field_comment = get_text([row[j] for j in comment_cols], "; ")
		# DEBUG print("row: %s, %s, %s" % (field_name, field_type, field_comment))
		if field_type:
			field = Field(field_name, field_type, field_comment)
			packet_fields.append(field)
			# DEBUG print(field)
	return Packet(packet_name, packet_id, packet_fields)
