import requests
from datatractor.utils.html_tools import *
from datatractor.utils.string_tools import *


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
	sections = make_hierarchy(protocol_html)
	root = sections[0]

	print("Analysing the protocol...")
	protocol = extract_protocol(root, game_version, protocol_number)
	print("Done!")
	return protocol


def find_documentation(game_version: str):
	html = requests.get("http://wiki.vg/Protocol_version_numbers").text
	root = make_hierarchy(html)[0]
	for table in root.recursive_findall(lambda e: isinstance(e, HtmlTable)):
		for row in table.rows[1:]:
			release_name = get_text(row[0])
			protocol = row[1]
			try:
				protocol_number = int(protocol)
			except:
				protocol_number = None
			doc_link = row[2]
			if (release_name == game_version) and (doc_link is not None) and (protocol_number is not None):
				url = doc_link["href"]
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
	for row in table.rows[1:]:  # [1:] to skip the header
		field_name = get_text(row[name_col])
		field_type = get_text(row[type_col])
		field_comment = get_text([row[j] for j in comment_cols])
		# DEBUG print("row: %s, %s, %s" % (field_name, field_type, field_comment))
		if field_type:
			field = Field(field_name, field_type, field_comment)
			packet_fields.append(field)
			# DEBUG print(field)
	return Packet(packet_name, packet_id, packet_fields)


class Protocol:
	"""Represents a minecraft protocol"""

	def __init__(self, game_version, number, sub_handshake, sub_play, sub_status, sub_login):
		self.game_version = game_version
		self.number = number
		self.handshake = sub_handshake
		self.play = sub_play
		self.status = sub_status
		self.login = sub_login

	def __repr__(self):
		return "Protocol(%s, %d, handshake:%s, play:%s, status:%s, login:%s)" % (
			self.game_version, self.number, repr(self.handshake), repr(self.play), repr(self.status), repr(self.login))

	def __str__(self):
		return "Protocol(%s, %d, %s, %s, %s, %s)" % (
			self.game_version, self.number, str(self.handshake), str(self.play), str(self.status), str(self.login))


class SubProtocol:
	"""Represents a sub-protocol"""

	def __init__(self, name, packets_cb, packets_sb):
		self.name = name
		self.clientbound = packets_cb
		self.serverbound = packets_sb

	def __repr__(self):
		return "SubProtocol(%s, client_bound:%s, server_bound:%s)" % (self.name, self.clientbound, self.serverbound)

	def __str__(self):
		return "SubProtocol(%s, client_bound:%d packets, server_bound:%d packets)" % (
			self.name, len(self.clientbound), len(self.serverbound))

	def packet_count(self):
		return len(self.clientbound) + len(self.serverbound)

	def clientbound_byname(self, packet_name: str):
		snake = to_snake_case(packet_name)
		for packet in self.clientbound:
			if packet.name_snake == snake:
				return packet
		return None

	def serverbound_byname(self, packet_name: str):
		snake = to_snake_case(packet_name)
		for packet in self.serverbound:
			if packet.name_snake == snake:
				return packet
		return None

	def clientbound_byid(self, packet_id: int):
		return self.clientbound[packet_id]

	def serverbound_byid(self, packet_id: int):
		return self.serverbound[packet_id]


class Packet:
	"""Represents a packet."""

	def __init__(self, name_str, id_str, fields):
		self.name_snake = to_snake_case(name_str)
		self.name = to_pascal_case(self.name_snake)
		self.id = int(id_str, 0)
		self.fields = fields

	def __repr__(self):
		return "Packet(%s, %s, %s)" % (self.name, self.id, repr(self.fields))

	def __str__(self):
		return "Packet(%s, %s, %d fields)" % (self.name, self.id, len(self.fields))


class Field:
	"""Represents a packet's field."""

	def __init__(self, name_str, type_str, comment):
		# DEBUG print("Field: %s:%s, %s:%s, %s;%s" % (name_str, type(name_str), type_str, type(type_str), comment, type(comment)))
		self.name_snake = to_snake_case(name_str)
		self.name = to_camel_case(self.name_snake)
		self.type = type_str
		self.comment = comment

	def __repr__(self):
		return "Field(%s, %s, %s)" % (self.name, self.type, self.comment)

	def __str__(self):
		return "Field(%s, %s)" % (self.name, self.type)
