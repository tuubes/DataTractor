from math import inf

import requests

from main.packets_data import *


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
	print("---------------------------")
	html = requests.get("http://wiki.vg/Protocol_version_numbers").text
	root = make_hierarchy(BeautifulSoup(html, "lxml"))[0]
	table: HtmlTable
	ll = list(root.recursive_findall(lambda e: isinstance(e, HtmlTable)))
	for table in root.recursive_findall(lambda e: isinstance(e, HtmlTable)):
		for row in table.rows[1:]:
			release_name = get_text(row[0])
			protocol = get_text(row[1])
			print(f"release {release_name}, protocol {protocol}")
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
	p = PacketInfos(section)
	# DEBUG print(p.main_table)
	# DEBUG print("   ----------------------------------   ")
	print(f"name: {p.main_compound.name}")
	print(f"id: {hex(p.main_id)} = {p.main_id}")

	# Parse the main table
	names_col, types_col, notes_col = find_compound_columns(p.main_table)
	ctx = LocalContext(p.main_table, names_col, types_col, notes_col)
	parse_compound(ctx, p, row=1, compound=p.main_compound, nrows=p.main_table.row_count() - 1)

	# Parse the data below the main table
	parse_below(p)
	l = []
	str_compound(l, p.main_compound, newline=False)
	print("".join(l))
	print("="*50)
	return p


def parse_compound(ctx: LocalContext, p: PacketInfos, row, compound, nrows):
	global idx0
	end = row + nrows
	assert end <= ctx.rowlimit, f"Invalid end {end} = {row} + {nrows} for compound {compound}"

	switch_field = None
	current_switch = None
	i = row
	while i < end:
		name_cell = ctx.table[i][ctx.names_col]
		if name_cell is None:
			# Fix for the packet https://wiki.vg/Protocol#Unlock_Recipes,
			# which has its ID,state=play and boundTo=client information on a separate line
			i += 1
			continue
		type_cell = ctx.table[i][ctx.types_col]
		notes_cell = ctx.table[i][ctx.notes_col]
		field_name = get_text(name_cell).lower()
		field_type = get_text(type_cell)
		field_type = "" if field_type is None else field_type.lower()
		field_notes = get_text(notes_cell)
		if not field_name.startswith("no field") and not field_type.startswith("no field"):
			field_name = varname(field_name.strip())
			field_type = typename(field_type)
			# Defines the field of the following switch ---------
			if name_cell.is_header:
				maybe_switch_field = p.dict_fields.get(field_name)
				if maybe_switch_field is None:
					print(f"[WARNING] No field corresponds to the header cell {name_cell} - Not a switch?")
				else:
					switch_field = maybe_switch_field
			# Switch entry --------------------------------------
			elif re.fullmatch("\\d+\\s*:.*", field_name):
				if current_switch is None:  # new switch
					if switch_field is None:  # should NOT happen
						print(f"[ERROR] Invalid switch: no corresponding field")
					else:
						current_switch = Switch(switch_field)
				if current_switch is not None:
					split = field_name.split(':', 1)
					entry_value = split[0]
					entry_name = classname(snake_case(split[1].strip()))
					s = SwitchEntry(entry_value, entry_name)
					current_switch.add_entry(s)
					ctx.names_col += 1  # move right
					# don't change the type column in a switch
					i = parse_compound(ctx, p, row=i, compound=s, nrows=name_cell.row_count())
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
				ctx.names_col += 1  # move right
				ctx.types_col += 1  # move the type too, it's not a switch
				i = parse_compound(ctx, p, row=i, compound=compound_nested, nrows=name_cell.row_count())
				i -= 1  # reverse the 'i += 1' made by parse_compound, we'll do it after the condition 'if not...'
				ctx.names_col -= 1  # back to the current column
				ctx.types_col -= 1  # don't forget the type :-)

				# Create the corresponding field in the current compound
				field_type = f"Array[{compound_name}]"
				field_name = plural(field_name)
				field = Field(field_name, field_type, field_notes)
				compound.add_field(field)
				p.register_field(field)
				switch_field = field
			# Single field ---------------------------------------
			else:
				field = Field(field_name, field_type, field_notes)
				compound.add_field(field)
				p.register_field(field)
				switch_field = field

				# Detect if the field is an enum with values defined in the field's notes
				# ... And admire the different syntaxes used in the documentation ><
				idx0 = None
				if field_notes is not None:
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
						field_notes = field_notes.replace(" =", ':').replace('=', ':')
					elif "0=" in field_notes:
						idx1 = field_notes.index("1=") if "1=" in field_notes else inf
						idx0 = field_notes.index("0=")
						idx0 = min(idx0, idx1)
						field_notes = field_notes.replace(" =", ':').replace('=', ':')
					elif "0xF0 =" in field_notes:
						idx0 = field_notes.index("0xF0 =")
						field_notes = field_notes.replace(" =", ':').replace('=', ':')
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
						field_notes = field_notes.replace(" -", ':').replace('-', ':')

				# Enum in notes ---------------------
				if idx0 is not None:
					enum = Enum(field)
					sub = field_notes[idx0:]
					split = sub.split(';') if ';' in sub else sub.split(',')
					for s in split:
						entry = parse_enum_textentry(s)
						if entry is not None:
							enum.add_entry(entry)

		i += 1
	if current_switch is not None:
		compound.add_switch(current_switch)
	return i


def parse_below(p: PacketInfos):
	# Put the longer names first to get the most specific result when searching for the related field:
	fields = sorted(p.dict_fields.values(), key=lambda f: len(f.name), reverse=True)
	last: str = ""
	for elem in p.below_main:
		if isinstance(elem, HtmlTable):
			if "Optional advancement display" in str(elem):
				print("HEY")
			last = ""
			# Find the table's meaning: Compound or Enum?
			compound_columns = find_compound_columns(elem)
			is_enum = (compound_columns is None)

			# Find the related field
			row0: List[str] = [get_text(cell).lower() for cell in elem.rows[0]]
			related_field: Field = None
			for field in fields:
				if is_enum and field.enum is not None:
					# The field shouldn't have an enum already defined
					continue
				if field.name in last or field.name in row0:
					related_field = field
					break
			if related_field is None:  # Try harder
				for field in fields:
					if is_enum and field.enum is not None:
						continue
					if last in field.name:
						related_field = field
						break

			# Parse the data
			# Enum data -----------------------------
			if is_enum:
				if related_field is None:
					print(f"[ERROR] Enum-like table found without a corresponding field")
					print(f"Fields: {[f.name for f in fields]}")
					print(f"Row0: {row0}")
					print(f"Table: {elem}")
					print("<<<<<<<<<<<<<<<<<<<<<<<<<<<<<")
				else:
					# >>>Search for the columns indexes<<<
					if elem.column_count() == 1:
						# Only one column => use it for the values and the names
						values_col = names_col = 0
					else:
						# Find which column contains the values
						values_col = 0
						row1 = [get_text(cell) for cell in elem.rows[1]]
						for icol, content in enumerate(row1):
							if re.match("\\d+", content.strip()):
								values_col = icol
								break
						# Find which column contains the names, defaults to values_col+1
						names_col = values_col + 1
						for icol, content in enumerate(row0):
							c = content.lower()
							if icol != values_col and (related_field.name.lower() == c or "name" in c):
								names_col = icol
								break
						# Prevent IndexError in case of a weird table
						if names_col >= elem.column_count():
							names_col = 0
						# Avoid to create an invalid enum
						first_name = row1[names_col]
						if re.match("\\d+", first_name):
							print(f"[ERROR] Invalid enum table: the name of the first entry, \"{first_name}\", begins with a digit")
							continue
					# >>>Parse the enum entries<<<
					enum = Enum(related_field)
					for entry_row in elem.rows[1:]:
						# Fix for the packet https://wiki.vg/Protocol#Effect, which has headers in the enum table
						v = entry_row[values_col]
						if not ((v.is_header and v.is_horizontal()) or v.is_left_ref()):
							entry_value = get_text(entry_row[values_col])
							entry_name = get_text(entry_row[names_col])
							if entry_name is not None:
								entry = parse_enum_entry(entry_value, entry_name)
								enum.add_entry(entry)
			# Compound data -------------------------
			else:  # Compound data
				names_col, types_col, notes_col = compound_columns
				ctx = LocalContext(elem, names_col, types_col, notes_col)
				if related_field is None:
					print("f[ERROR] Compound-like table found without a corresponding field")
				else:
					compound_name = classname(related_field.name)
					compound = Compound(compound_name, related_field)
					parse_compound(ctx, p, row=1, compound=compound, nrows=ctx.rowlimit - 1)
		# Enum data in list -------------------------
		# (often used in the old protocol documentation)
		elif isinstance(elem, HtmlList):  # Enum data in list
			last = ""
			# Find the related field
			related_field: Field = None
			for (name, field) in p.dict_fields.items():
				if field.enum is None and name in last:
					# The field shouldn't have an enum already defined
					related_field = field
					break
			if related_field is not None:
				# Parse the enum fields
				enum = Enum(related_field)
				for li in elem.elements:
					if isinstance(li, str):
						entry = parse_enum_textentry(li)
						if entry is not None:
							enum.add_entry(entry)
		else:
			last = get_text(elem)


def parse_enum_textentry(text: str):
	parts = text.split(':', maxsplit=1)
	if len(parts) < 2:
		return None
	return parse_enum_entry(parts[0], parts[1])


def parse_enum_entry(entry_value: str, entry_name: str):
	entry_value = entry_value.strip()
	entry_name = entry_name.strip()
	if '(' in entry_name:
		parts = entry_name.split('(', 1)
		entry_name = parts[0]
		entry_comments = parts[1].replace(')', "", 1)
	else:
		entry_comments = None
	if len(entry_name) > 20:
		entry_comments = entry_name if entry_comments is None else entry_name + entry_comments
		entry_name = entry_name[:20]
	entry_name = constname(entry_name)
	return EnumEntry(entry_value, entry_name, entry_comments)


def find_compound_columns(table: HtmlTable):
	# default values
	names_col = None
	types_col = None
	notes_col = None

	# search
	first_row = table.rows[0]
	ncol = len(first_row)
	i = 0
	while i < ncol:
		cell = first_row[i]
		if not isinstance(cell, RefCell):
			text = get_text(cell).strip().lower()
			if text == "field name":
				names_col = i
			elif text == "field type":
				types_col = i
			elif text == "notes":
				notes_col = i
		i += 1
	if names_col is None and types_col is None:  # names_col and types_col are None
		return None
	return names_col, types_col, notes_col  # names_col and types_col aren't None
