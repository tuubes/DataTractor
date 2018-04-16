def scala_type(field_type: str):
	t: str = field_type.lower().replace("unsigned", "").replace("enum", "").strip()
	same = ["boolean", "byte", "short", "int", "long", "float", "double", "string", "uuid"]
	as_str = ["chat", "identifier"]
	if t in same:
		return field_type
	if ("string" in t) or (t in as_str):
		return "String"
	if t == "varint":
		return "Int"
	if (t == "varlong") or (t == "position"):
		return "Long"
	#if t == "entity metadata":
		# TODO support EntityMetadata storage
		#return "AnyRef"
	#if t == "slot":
		# TODO support items slots
		#return "AnyRef"
	#if t == "nbt tag":
		# TODO support nbt tags
		#return "AnyRef"
	if t == "angle":
		return "Byte"

	if t.startswith("optional"):
		x = t[9:]
		scala_x = scala_type(x)
		return "Option[%s]" % scala_x
	if t.startswith("array of "):
		x = t[8:]
		scala_x = scala_type(x)
		return "Array[%s]" % scala_x
	if t.endswith(" array"):
		x = t[:-6]
		scala_x = scala_type(x)
		return "Array[%s]" % scala_x

	print("Unknown/Unsupported type:", t)
	return "AnyRef"
