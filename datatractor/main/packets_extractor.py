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
	print("=" * 50)
	return p


def parse_compound(ctx: LocalContext, p: PacketInfos, row, compound, nrows):
	global idx0
	end = row + nrows
	assert end <= ctx.rowlimit, f"Invalid end {end} = {row} + {nrows} for compound {compound}"

	option_guard_field = None
	length_field_force = 0  # when 0, length_field expires and is set to None
	length_field = None
	switch_field = None
	switch_field_is_out = False
	current_switch = None
	i = row
	while i < end:
		length_field_force = max(0, length_field_force - 1)
		if length_field_force == 0:
			length_field = None
		name_cell = ctx.table[i][ctx.names_col]
		if name_cell is None:
			# Fix for the packet https://wiki.vg/Protocol#Unlock_Recipes,
			# which has its ID,state=play and boundTo=client information on a separate line
			i += 1
			continue
		if name_cell.is_deleted:
			# Ignore deleted cells, for Pre-release protocol
			i += 1
			continue
		type_cell = ctx.table[i][ctx.types_col]
		notes_cell = ctx.table[i][ctx.notes_col]
		low_field_name = get_text(name_cell)
		if low_field_name is None:
			# Fix for packets that have no field and don't state "no fields" clearly
			i += 1
			continue
		low_field_name = low_field_name.lower().strip()
		field_type = get_text(type_cell)
		field_type = "" if field_type is None else field_type.lower()
		field_notes = get_text(notes_cell)
		# Switch entry ------------------------------------------
		# The switch is detected before the "no field" condition, otherwise we miss a few switch entries
		if re.fullmatch("\\d+\\s*:.+", low_field_name):
			if current_switch is None:  # new switch
				if switch_field is None:  # should NOT happen
					print(f"[ERROR] Invalid switch: no corresponding field")
				else:
					current_switch = Switch(switch_field, switch_field_is_out)
			if current_switch is not None:
				split = low_field_name.split(':', 1)
				entry_value = split[0]
				entry_name = classname(snake_case(split[1].strip()))
				s = SwitchEntry(entry_value, entry_name)
				current_switch.add_entry(s)
				ctx.names_col += 1  # move right
				# don't change the type column in a switch
				i = parse_compound(ctx, p, row=i, compound=s, nrows=name_cell.row_count())
				i -= 1  # reverse the 'i += 1' made by parse_compound, we'll do it after the condition 'if not...'
				ctx.names_col -= 1  # back to the current column
		# -------------------------------------------------------
		# No more processing of this row if there's no field
		elif not low_field_name.startswith("no field") and not field_type.startswith("no field"):
			field_name = varname(low_field_name)
			field_type = typename(field_type)
			# Defines the field of the following switch ---------
			if name_cell.is_header:
				field_name_lower = field_name.lower()
				maybe_switch_field = p.dict_fields.get(field_name_lower)
				if maybe_switch_field is None:
					print(f"[WARNING] No field corresponds to the header cell {name_cell} - Not a switch?")
				else:
					# Detect if the field we refer to is outside of the current compound (which containts the switch)
					switch_field_is_out = (field_name_lower not in compound.fields_dict)
					switch_field = maybe_switch_field
			# End of switch -------------------------------------
			elif current_switch is not None:
				compound.add_switch(current_switch)
				current_switch = None
			# Nested compound structure -------------------------
			elif name_cell.is_vertical():
				if field_type != "Array":
					print(f"[WARNING] Nested compound with type {field_type}, expected Array")

				compound_name = classname(snake_case(low_field_name))
				# Create the corresponding field in the current compound
				field_type = f"Array[{compound_name}]"
				low_field_name = plural(varname(low_field_name))
				field = Field(low_field_name, field_type, field_notes)
				compound.add_field(field)
				p.register_field(field)
				switch_field = field

				# Defines the array's length
				if length_field_force == 2 or (length_field_force == 1 and hint_give_length(length_field, field)):
					field.set_length_given_by(length_field)
					length_field_force = 0
					if length_field.name in ["length", "count", "size"]:  # ambiguous short name and maybe duplicated
						length_field.name = f"{field.name}Length"  # meaningful and unique name

				# Parse the compound structure
				compound_nested = Compound(compound_name, field)
				ctx.names_col += 1  # move right
				ctx.types_col += 1  # move the type too, it's not a switch
				i = parse_compound(ctx, p, row=i, compound=compound_nested, nrows=name_cell.row_count())
				i -= 1  # reverse the 'i += 1' made by parse_compound, we'll do it after the condition 'if not...'
				ctx.names_col -= 1  # back to the current column
				ctx.types_col -= 1  # don't forget the type :-)
			# Single field ---------------------------------------
			else:
				field_type, field_maxlength = extract_type_and_length(field_type)
				field = Field(field_name, field_type, field_notes, field_maxlength)
				compound.add_field(field)
				p.register_field(field)
				switch_field = field

				# Handle arrays' length
				if can_give_length(field):
					length_field = field
					length_field_force = 3  # will be 2 for the next field and 1 for the one after
				elif is_array(field):
					if length_field_force == 2 or (length_field_force == 1 and hint_give_length(length_field, field)):
						field.set_length_given_by(length_field)
						length_field_force = 0
						if length_field.name in ["length", "count", "size"]:
							# ambiguous short name and maybe duplicated => meaningful and unique name
							length_field.name = f"{field.name}Length"

				# Handle optional fields
				if is_optional(field):
					guard = option_guard_field
					if guard.type == "Boolean":
						field.only_if = guard.name
						field.only_if_bool = guard
						guard.is_condition_of = field
					elif field.comment is None:
						print(f"[WARNING] Cannot detect what determines the presence of {field}")
					else:
						c: str
						c = field.comment.lower()
						present_if = ("present if" in c)
						only_if = ("only if" in c)
						sent_when = ("sent when" in c)
						if not only_if and not sent_when:
							print(f"[WARNING] Cannot detect what determines the presence of {field}")
						else:
							if present_if:
								c = c[c.index("present if"):].replace("present if").strip()
							if only_if:
								c = c[c.index("only if"):].replace("only if", "").strip()
							else:  # sent_when
								c = c[c.index("sent when"):].replace("sent when", "").strip()
							if ';' in c:
								c = c[:c.index(';')]
							if '.' in c:
								c = c[:c.index('.')]
							# Parse the condition in the comments
							condition = find_guard_condition(p, field, guard, c)
							if condition is None:
								print(f"[WARNING] Cannot detect what determines the presence of {field}")
								print(f"	   -> c = {c}")
							else:
								field.only_if = condition

				else:
					option_guard_field = field

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
					elif "0x1:" in field_notes and "0x2:" in field_notes:
						# This a bitmask but we store its values the same way as an enum
						# The generator won't generate a real "enum" but a class with constants values so it's fine
						idx0 = field_notes.index("0x1:")
					elif "0xF0 =" in field_notes:  # priority over "0 ="
						is_semi_byte_a = (field_notes.count('=') == 2) and ("0x0F" in field_notes)
						is_semi_byte_b = "4 most significant bits" in field_notes
						if not is_semi_byte_a and not is_semi_byte_b:
							idx0 = field_notes.index("0xF0 =")
							field_notes = field_notes.replace(" =", ':').replace('=', ':')
					elif "0 =" in field_notes and not "20 = full" in field_notes:
						idx1 = field_notes.index("1 =") if "1 =" in field_notes else inf
						idx0 = field_notes.index("0 =")
						idx0 = min(idx0, idx1)
						field_notes = field_notes.replace(" =", ':').replace('=', ':')
					elif "0=" in field_notes and "from y=0" not in field_notes:
						idx1 = field_notes.index("1=") if "1=" in field_notes else inf
						idx0 = field_notes.index("0=")
						idx0 = min(idx0, idx1)
						field_notes = field_notes.replace(" =", ':').replace('=', ':')
					elif "1 for" in field_notes and "1 for every" not in field_notes:
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
					has_colon = ';' in sub
					use_colon = has_colon and ((',' not in sub) or (sub.index(';') < sub.index(',')))
					if use_colon:
						split = sub.split(';')
					elif has_colon:
						# Fix for https://wiki.vg/Protocol#Join_Game
						split = sub.split(';')[0].split(',')
					else:
						split = sub.split(',')
					# Parse the entries
					for s in split:
						parse_enum_textentry(enum, s)

		i += 1
	if current_switch is not None:
		compound.add_switch(current_switch)
	return i


def can_give_length(field: Field):
	t = field.type
	if t.startswith("Option["):
		t = multireplace(t, {"Option[": "", ']': ""})
	return t in ["Varint", "Int", "Short", "Byte"]


def hint_give_length(field: Field, to: Field):
	return can_give_length(field) and (to.name in field.name)


def is_array(field: Field):
	return field.type.startswith("Array") or field.type.startswith("Option[Array")


def is_optional(field: Field):
	return field.type.startswith("Option")


def find_guard_value(guard: Field, value: str):
	if value.isdigit() or value in ["true", "false"]:
		return value
	elif guard.type == "String":
		content = value.replace('"', "")
		return f'"{content}"'
	elif guard.enum is not None:
		big_v = constname(snake_case(value))
		entry: EnumEntry
		for entry in guard.enum.entries:
			if entry.name == big_v:
				return f"{guard.enum.name}.{entry.name}"
	return None


def find_guard_condition(p: PacketInfos, field: Field, guard: Field, c: str):
	m = re.match("(.+) is (.+) or (.+)", c)
	if m is not None:
		g = p.dict_fields.get(varname(snake_case(m.group(1))))
		guard = g if g is not None else guard
		return f"{guard.name} == {m.group(2)} || {guard.name} == {m.group(3)}"

	if "indicates it" in c and guard.enum is not None and len(guard.enum.entries) > 0:
		return f"{guard.name} & {guard.enum.entries[0].name} != 0"

	operator = None
	m = re.match("(.+) does not equal (.+)", c)
	if m is not None:
		operator = "!="
	else:
		m = re.match("(.+) is more than (.+)", c)
		if m is not None:
			operator = ">"
		else:
			m = re.match("(.+) is less than (.+)", c)
			if m is not None:
				operator = "<"
			else:
				m = re.match("(.+) is (.+)", c)
				if m is not None:
					operator = "=="
				else:
					return None

	specified_guard_name = m.group(1)
	g = p.dict_fields.get(varname(snake_case(specified_guard_name)))
	guard = g if g is not None else guard
	if guard is None:
		return None

	specified_value = m.group(2)
	value = find_guard_value(guard, specified_value)
	if value is None:
		return None

	return f"{guard.name} {operator} {value}"


def can_be_related(field: Field, is_enum: bool):
	comment = "" if field.comment is None else field.comment.lower()
	not_enum = not is_enum or (field.enum is None)
	not_compound = is_enum or (field.compound is None)
	compatible_type = field.type not in ["Boolean", "Array", "Float", "Double", "Long"]
	comment_hint_ok = all(x not in comment for x in ["number", "offset", "length", "count"])
	return not_enum and not_compound and compatible_type and comment_hint_ok


def parse_below(p: PacketInfos):
	# Put the longer names first to get the most specific result when searching for the related field:
	fields = sorted(p.all_fields, key=lambda f: len(f.name), reverse=True)
	last: str = ""
	for elem in p.below_main:
		if isinstance(elem, HtmlTable):
			# Find the table's meaning: Compound or Enum?
			compound_columns = find_compound_columns(elem)
			attribute_columns = find_attribute_columns(elem)
			is_enum = (compound_columns is None)
			is_attr = (attribute_columns is not None)

			# Find the related field
			row0: List[str] = [get_text(cell).lower() for cell in elem.rows[0] if not cell.is_deleted]
			compatible_fields = [(f, f.name.lower()) for f in fields if can_be_related(f, is_enum)]
			related_field: Field = None
			for (field, name) in compatible_fields:
				if name in last or name in row0:
					related_field = field
					break
			if related_field is None:  # Try harder
				for (field, name) in compatible_fields:
					if last in name:
						related_field = field
						break
			if related_field is None:  # Retry harder
				l = last.replace(' ', "")
				for (field, name) in compatible_fields:
					# DEBUG print(f"{name}: {field.type} ?")
					if l in field.type.lower():
						related_field = field
						break
			if related_field is None and is_enum:
				print(f"[WARNING] Last resort to find the related field. Compatible fields: {compatible_fields}")
				for (field, name) in compatible_fields:
					if "type" in name:
						for header in row0:
							if "type" in header:
								related_field = field
								break
					elif "id" in name:
						for header in row0:
							if "id" in header:
								related_field = field
								break
			# Parse the data
			# Attribute data ------------------------
			if is_attr:
				if related_field is None:
					print(">" * 30)
					print(f"[ERROR] Attributes-like table found without a corresponding field")
					print(f"Last text: {last}")
					print(f"Fields: {[(f.name, f.type) for f in fields]}")
					print(f"Row0: {row0}")
					print(f"Table: {elem}")
					print("<" * 30)
				else:
					key_col = attribute_columns[0]
					def_col = attribute_columns[1]
					min_col = attribute_columns[2]
					max_col = attribute_columns[3]
					lab_col = attribute_columns[4]
					# Save the values as an enum with comments
					enum = Enum(related_field)
					for attr_row in elem.rows[1:]:
						attr_key = get_text(attr_row[key_col])
						attr_def = get_text(attr_row[def_col])
						attr_min = get_text(attr_row[min_col])
						attr_max = get_text(attr_row[max_col])
						attr_lab = get_text(attr_row[lab_col])

						entry_value = attr_key
						entry_name = constname(entry_value)
						entry_comment = f"{attr_lab}; default {attr_def}, min {attr_min}, max {attr_max}"
						entry = EnumEntry(entry_value, entry_name, entry_comment)
						enum.add_entry(entry)
			# Enum data -----------------------------
			elif is_enum:
				if related_field is None:
					print(">" * 30)
					print(f"[ERROR] Enum-like table found without a corresponding field")
					print(f"Last text: {last}")
					print(f"Fields: {[(f.name, f.type) for f in fields]}")
					print(f"Row0: {row0}")
					print(f"Table: {elem}")
					print("<" * 30)
				else:
					# >>>Search for the columns indexes<<<
					names_with_values = False
					if elem.column_count() == 1:
						# Only one column => use it for the values and the names
						values_col = names_col = 0
						comments_col = None
					else:
						# Find which column contains the values
						values_col = 0
						row1 = [get_text(cell) for cell in elem.rows[1]]
						for icol, content in enumerate(row1):
							c = content.strip()
							if re.match("\\d+", c):
								if re.fullmatch("\\d+:.+", c):
									names_with_values = True
									names_col = values_col
									comments_col = values_col + 1
								values_col = icol
								break
						# Find which column contains the names, defaults to values_col+1
						if not names_with_values:
							names_col = values_col + 1
							for icol, content in enumerate(row0):
								c = content.lower()
								if icol != values_col and (related_field.name.lower() == c or "name" in c):
									names_col = icol
									break
							# Find which column contains the notes, defaults to names_col+1 or None
							comments_col = names_col + 1
							for icol, content in enumerate(row0):
								c = content.lower()
								if icol not in [values_col, names_col] and c == "notes":
									comments_col = icol
									break
						# Prevent IndexError in case of a weird table
						if names_col >= elem.column_count():
							names_col = 0
						if (comments_col is not None) and (comments_col >= elem.column_count()):
							# Try to use the third column for the comments
							if elem.column_count() >= 3:
								for i in range(0, elem.column_count()):
									if i != values_col and i != names_col:
										comments_col = i
							# There is no third column => there are no comments
							else:
								comments_col = None
						# Avoid to create an invalid enum
						first_name = row1[names_col]
						if re.match("\\d+", first_name):
							print(
								f"[ERROR] Invalid enum table: the name of the first entry, \"{first_name}\", begins with a digit")
							continue
					# >>>Parse the enum entries<<<
					enum = Enum(related_field)
					for entry_row in elem.rows[1:]:
						# Fix for the packet https://wiki.vg/Protocol#Effect, which has headers in the enum table
						v = entry_row[values_col]
						if not ((v.is_header and v.is_horizontal()) or v.is_left_ref()):
							if names_with_values:
								entry_value_and_name = get_text(entry_row[values_col])
								entry_comment = None if comments_col is None else get_text(entry_row[comments_col])
								s = entry_value_and_name.split(':', 1)
								entry_value = s[0]
								entry_name = s[1]
							else:
								entry_value = get_text(entry_row[values_col])
								entry_name = get_text(entry_row[names_col])
								entry_comment = None if comments_col is None else get_text(entry_row[comments_col])
							if entry_name is not None:
								parse_enum_entry(enum, entry_value, entry_name, entry_comment)
			# Compound data -------------------------
			else:
				names_col, types_col, notes_col = compound_columns
				ctx = LocalContext(elem, names_col, types_col, notes_col)
				if related_field is None:
					print(">" * 30)
					print("[ERROR] Compound-like table found without a corresponding field")
					print(f"Last text: {last}")
					print(f"Fields: {[(f.name, f.type) for f in fields]}")
					print(f"Row0: {row0}")
					print(f"Table: {elem}")
					print("<" * 30)
				else:
					t = related_field.type
					if '[' in t:
						rep = {"Array[": "", "Option[": "", ']': ""}
						compound_name = multireplace(t, rep)
					else:
						compound_name = t
					compound = Compound(compound_name, related_field)
					parse_compound(ctx, p, row=1, compound=compound, nrows=ctx.rowlimit - 1)
					# Recreate the field list to include the fields of the new compound:
					fields = sorted(p.all_fields, key=lambda f: len(f.name), reverse=True)
			last = ""
		# Enum data in list -------------------------
		# (often used in the old protocol documentation)
		elif isinstance(elem, HtmlList):  # Enum data in list
			# Find the related field
			related_field: Field = None
			for field in p.all_fields:
				if field.enum is None and field.name.lower() in last:
					# The field shouldn't have an enum already defined
					related_field = field
					break
			if related_field is not None:
				# Parse the enum fields
				enum = Enum(related_field)
				for li in elem.elements:
					if isinstance(li, str):
						parse_enum_textentry(enum, li)
				if len(enum.entries) == 0:
					print(f"[WARNING] Empty enum parsed (from a list) for {related_field}, it will be removed.")
					related_field.enum = None
			last = ""
		else:
			rep = {"structure:": "", "values:": "", ':': ""}
			last = multireplace(get_text(elem).lower(), rep).strip()
			# Fix for https://wiki.vg/Protocol#Player_List_Item
			if last.startswith("<dinnerbone> it's a bitfield"):
				last = "flags"


def parse_enum_textentry(enum: Enum, text: str):
	parts = text.split(':', maxsplit=1)
	if len(parts) >= 2:
		parse_enum_entry(enum, parts[0], parts[1])


def parse_enum_entry(enum: Enum, entry_value: str, entry_name: str, entry_comments: str = None):
	entry_value = entry_value.strip()
	entry_name = entry_name.strip()
	if '(' in entry_name:
		parts = entry_name.split('(', 1)
		# Fix for https://wiki.vg/Protocol#Entity_Equipment slots
		if ('–' in entry_value or '-' in entry_value) and (':' in parts[1]):
			s = parts[1].split(':', 1)
			entry_value = s[0]
			entry_name = s[1]
		else:
			# Usual parentheses containing comments
			entry_name = parts[0]
			if entry_comments is not None:
				entry_comments = entry_comments + parts[1].replace(')', "", 1)
			else:
				entry_comments = parts[1].replace(')', "", 1)
	if len(entry_name) > 29:
		# Fix for https://wiki.vg/Protocol#Entity_Effect flags
		if "- " in entry_name:
			s = entry_name.split("- ", 1)
			c = s[1].strip()
			entry_name = s[0]
			entry_comments = c if entry_comments is None else entry_comments + c
		# Fix for https://wiki.vg/Protocol#Update_Block_Entity
		elif ", " in entry_name:
			s = entry_name.split(", ", 1)
			c = s[1].strip()
			entry_name = s[0]
			entry_comments = c if entry_comments is None else entry_comments + c
		# Fix for https://wiki.vg/Protocol#Client_Settings chat mode
		elif ". " in entry_name:
			s = entry_name.split(". ", 1)
			c = s[1].strip()
			entry_name = s[0]
			entry_comments = c if entry_comments is None else entry_comments + c
		else:
			# Fix for https://wiki.vg/Protocol#Window_Property
			rep = {"the ": "", "of ": "",
				   "shown on mouse hover over ": "", "requirement for ": "", "enchantment slot": "slot",
				   "Play elder guardian mob appearance effect and sound": "elder guardian appearance"}
			short_name = multireplace(entry_name, rep)
			entry_comments = entry_name if entry_comments is None else entry_name + entry_comments
			entry_name = short_name[:29]
	elif len(entry_name) == 0:
		if entry_comments:
			entry_name = entry_comments.replace('?', "")
		else:
			entry_name = "_" + entry_value

	entry_name = constname(entry_name)
	entry = EnumEntry(entry_value, entry_name, entry_comments)
	enum.add_entry(entry)


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


def find_attribute_columns(table: HtmlTable):
	if table.column_count() != 5:
		return None
	r = [get_text(cell).lower() for cell in table.rows[0]]
	if r == ["key", "default", "min", "max", "label"]:
		return 0, 1, 2, 3, 4
	else:
		return None


def extract_type_and_length(field_type: str):
	if "String" in field_type and '(' in field_type:
		ltyp = []
		lmax = []
		p = False
		for ch in field_type:
			if ch == '(':
				p = True
			elif ch == ')':
				p = False
			elif p:
				lmax.append(ch)
			else:
				ltyp.append(ch)
		type = "".join(ltyp)
		max = int("".join(lmax))
		return type, max
	return field_type, None
