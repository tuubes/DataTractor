from math import inf

import requests

from datatractor.main.packets_data import *
from datatractor.utils.html_tools import *
from main.packets_data import Compound, Field
from utils.html_tools import HtmlTable


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
	return "WIP"

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


def parse_compound(ctx: LocalContext, p: PacketContext, row, compound, nrows):
	global idx0
	end = row + nrows
	assert end <= ctx.rowlimit, f"Invalid end {end} = {row} + {nrows} for compound {compound}"

	last_field = None
	current_switch = None
	i = row
	while i < end:
		name_cell = ctx.table[i][ctx.names_col]
		type_cell = ctx.table[i][ctx.types_col]
		notes_cell = ctx.table[i][ctx.notes_col]
		field_name = get_text(name_cell).lower()
		field_type = get_text(type_cell).lower()
		field_notes = get_text(notes_cell)
		if not field_name.startswith("no field") and not field_type.startswith("no field"):
			field_name = varname(field_name.strip())
			field_type = typename(field_type)
			# Defines the field of the following switch ---------
			if name_cell.is_header:
				defined = p.dict_fields.get(field_name)
				if defined is None:
					print(f"[WARNING] No field corresponds to the header cell {name_cell} - Not a switch?")
				else:
					last_field = defined
			# Switch entry --------------------------------------
			elif re.fullmatch("\\d+\\s*:.*", field_name):
				if current_switch is None:  # new switch
					if last_field is None:  # should NOT happen
						print(f"[ERROR] Invalid switch: no corresponding field")
					current_switch = Switch(last_field)
					p.register_switch(current_switch)
				split = field_name.split(':', 1)
				entry_value = split[0]
				entry_name = classname(snake_case(split[1].strip()))
				s = SwitchEntry(entry_value, entry_name)
				current_switch.add_entry(s)
				ctx.names_col += 1  # move right
				# don't change the type column in a switch
				i = parse_compound(ctx, p, row, s, name_cell.column_count())
				i -= 1  # reverse the 'i += 1' made by parse_compound, we'll do it after the condition 'if not...'
				ctx.names_col -= 1  # back to the current column
			# End of switch -------------------------------------
			elif current_switch is not None:
				compound.add_switch(current_switch)
				current_switch = None
			# Nested compound structure -------------------------
			elif name_cell.is_vertical():
				if field_type != "Array":
					print(f"[WARNING] Nested compound with type {field_type}, expected Array")

				# Parse the compound structure
				compound_name = classname(field_name)
				compound_nested = Compound(compound_name)
				p.register_compound(compound_nested)
				ctx.names_col += 1  # move right
				ctx.types_col += 1  # move the type too, it's not a switch
				i = parse_compound(ctx, p, row, compound_nested, name_cell.row_count())
				i -= 1  # reverse the 'i += 1' made by parse_compound, we'll do it after the condition 'if not...'
				ctx.names_col -= 1  # back to the current column
				ctx.types_col -= 1  # don't forget the type :-)

				# Create the corresponding field in the current compound
				field_type = f"Array[{compound_name}]"
				field_name = plural(field_name)
				field = Field(field_name, field_type, field_notes)
				compound.add_field(field)
				p.register_field(field)
				last_field = field
			# Single field ---------------------------------------
			else:
				field = Field(field_name, field_type, field_notes)
				compound.add_field(field)
				p.register_field(field)
				last_field = field

				idx0 = None
				if "-1:" in field_notes:
					idx0 = field_notes.index("-1:")
				elif "0:" in field_notes:
					idx0 = field_notes.index("0:")
				elif "0 :" in field_notes:
					idx0 = field_notes.index("0 :")
				elif "0 =" in field_notes:
					idx1 = field_notes.index("1 =") if "1 =" in field_notes else inf
					idx0 = field_notes.index("0 =")
					idx0 = min(idx0, idx1)
					field_notes = field_notes.replace(" =", ':').replace("=", ':')
				elif "0=" in field_notes:
					idx1 = field_notes.index("1=") if "1=" in field_notes else inf
					idx0 = field_notes.index("0=")
					idx0 = min(idx0, idx1)
					field_notes = field_notes.replace(" =", ':').replace("=", ':')
				elif "0xF0 =" in field_notes:
					idx0 = field_notes.index("0xF0 =")
					field_notes = field_notes.replace(" =", ':').replace("=", ':')
				elif "1 for" in field_notes:
					idx0 = field_notes.index("1 for")
					field_notes = field_notes.replace(" for", ':')
				elif "North =" in field_notes and "," in field_notes:
					idx0 = field_notes.index("North =")
					field_notes = field_notes.replace("North = 2, South = 0, West = 1, East = 3",
													  "0: South, 1: West, 2: North, 3: East")
				elif "1 -" in field_notes and ("2 -" in field_notes or "0 -" in field_notes):
					idx1 = field_notes.index("1 -")
					idx0 = field_notes.index("0 -") if "0 -" in field_notes else inf
					idx0 = min(idx0, idx1)
					field_notes = field_notes.replace(" -", ':')

				# Enum in notes ---------------------
				if idx0 is not None:
					enum = Enum(field)
					sub = field_notes[idx0:]
					split = sub.split(";") if ";" in sub else sub.split(",")
					for s in split:
						parts = s.split(":", 1)
						if len(parts) < 2:
							continue
						entry_value = parts[0].strip()
						entry_name = parts[1]
						if "(" in entry_name:
							parts = entry_name.split("(", 1)
							entry_name = parts[0]
							entry_comments = parts[1].replace(")", "", 1)
						else:
							entry_comments = None
						if len(entry_name) > 20:
							entry_comments = entry_name + entry_comments
							entry_name = entry_name[:20]
						entry_name = constname(entry_name)
						entry = EnumEntry(entry_value, entry_name, entry_comments)
						enum.add_entry(entry)
					p.register_enum(enum)



		i += 1
	if current_switch is not None:
		compound.add_switch(current_switch)
	return i

