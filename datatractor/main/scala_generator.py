from datatractor.main.packets_extractor import PacketInfos
from datatractor.utils.string_tools import *


def scala_type(field_type: str) -> str:
	"""
	Returns the Scala type that corresponds to the given packet field type.
	:param field_type: the (non-scala) field's type
	:return: the corresponding Scala type
	"""
	t: str = field_type.replace("enum", "").strip()
	same = ["boolean", "byte", "short", "int", "long", "float", "double", "string"]
	if t in same:
		return t.title()
	if t == "uuid":
		return "UUID"
	if (t.startswith("string")) or (t in as_str):
		return "String"
	if (t == "varint") or (t == "unsigned byte") or (t == "unsigned short"):
		return "Int"
	if (t == "varlong") or (t == "position"):
		return "Long"
	if t == "entity metadata":
		# TODO support EntityMetadata storage
		return "AnyRef"
	if t == "slot":
		# TODO support items slots
		return "AnyRef"
	if t == "nbt tag":
		return "TagCompound"
	if t == "angle":
		return "Byte"
	if t == "no fields" or t == "no field" or t == "nofield":
		return "Nothing"

	if t.startswith("optional "):
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

	return "???"


def niol_write(field_type: str) -> str:
	"""
	Generates a Scala statement that writes the given field.
	:param field_type: the (non-scala) field's type
	:return: a code that writes the field
	"""
	t: str = field_type.replace("enum", "").strip()
	simple_dict = {
		"boolean": "out.putBool($)",
		"byte": "out.putByte($)",
		"short": "out.putShort($)",
		"int": "out.putInt($)",
		"unsigned byte": "out.putInt($)",
		"unsigned short": "out.putInt($)",
		"long": "out.putLong($)",
		"float": "out.putFloat($)",
		"double": "out.putDouble($)",
		"string": "out.putVarstring($, UTF_8)",
		"uuid": "out.putLong($.getMostSignificantBits); out.putLong($.getLeastSignificantBits)",
		"varint": "out.putVarint($)",
		"varlong": "out.putVarlong($)",
		"byte array": "out.putBytes($)",
		"array of byte": "out.putBytes($)",
		"array of int": "out.putInts($)",
		"array of long": "out.putLongs($)",
		"array of float": "out.putFloats($)",
		"array of double": "out.putDoubles($)",
		"position": "out.putLong($)",
		"angle": "out.putByte($)",
		"nbt tag": "$.writeNamed(new NiolToDataOutput(out))",
	}
	simple = simple_dict.get(t)
	if simple:
		return simple
	if t.startswith("string") or t in as_str:
		return simple_dict.get("string")

	if t.startswith("optional "):
		x = t[9:]
		write_x = niol_write(x)
		return "if ($.isDefined) {\n      %s\n    }" % write_x.replace("$", "$.get")

	if t.startswith("array of"):
		element_type = t.replace("array of ", "").split(" ")[0]
		loop = "var i_$ = 0\n    " \
			   "while (i_$ < $.length) {\n    " \
			   "  %s\n    " \
			   "  i_$ += 1\n    " \
			   "}" % parametrize(niol_write(element_type), "$", "$(i_$)")
		return loop

	# TODO support more data types

	return "// TODO write $"


def niol_read(field_type: str, prefix: str = "val ") -> str:
	"""
	Generates a Scala statement that reads the given field.
	:param field_type: the (non-scala) field's type
	:param prefix: the prefix to append before the assignation of the value
	:return: a code that reads the field
	"""
	t: str = field_type.replace("enum", "").strip()
	simple_dict = {
		"boolean": prefix + "$ = in.getBool()",
		"byte": prefix + "$ = in.getByte()",
		"short": prefix + "$ = in.getShort()",
		"int": prefix + "$ = in.getInt()",
		"long": prefix + "$ = in.getLong()",
		"float": prefix + "$ = in.getFloat()",
		"double": prefix + "$ = in.getDouble()",
		"uuid": prefix + "$ = new UUID(in.getLong(), in.getLong())",
		"varint": prefix + "$ = in.getVarint()",
		"varlong": prefix + "$ = in.getVarlong()",
		"unsigned byte": prefix + "$ = in.getUnsignedByte()",
		"unsigned short": prefix + "$ = in.getUnsignedShort()",
		"string": prefix + "$ = in.getVarstring(UTF_8)",
		"byte array": prefix + "$ = in.getBytes($Length)",
		"array of byte": prefix + "$ = in.getBytes($Length)",
		"array of int": prefix + "$ = in.getInts($Length)",
		"array of long": prefix + "$ = in.getLongs($Length)",
		"array of float": prefix + "$ = in.getFloats($Length)",
		"array of double": prefix + "$ = in.getLongs($Length)",
		"position": prefix + "$ = in.getLong()",
		"angle": prefix + "$ = in.getByte()",
		"nbt tag": prefix + "$ = TagCompound.readNamed(new NiolToDataInput(in))",
	}
	simple = simple_dict.get(t)
	if simple:
		return simple
	if t.startswith("string") or t in as_str:
		return simple_dict.get("string")
	if t.startswith("array of "):
		element_type = t.replace("array of ", "").split(" ")[0]
		loop = "var i_$ = 0\n    " \
			   "%s$ = new %s($Length)\n    " \
			   "while (i_$ < $Length) {\n    " \
			   "  %s\n    " \
			   "  i_$ += 1\n    " \
			   "}" % (prefix, scala_type(field_type), parametrize(niol_read(element_type, ""), "$", "$(i_$)"))
		return loop

	# TODO support more data types

	return "// TODO read $"


as_str = ["chat", "identifier"]
todo_count = 0
unhandled_type_count = 0


def generate_packet_class(p: PacketInfos, package: str) -> (str, str):
	"""
	Generates scala classes from packet data.
	:param p: the packet
	:return: the name of the generated class, and the generated class (as a string)
	"""
	integers = ["Byte", "Short", "Int"]
	pname = p.name + "Packet"
	bname = pname + "Builder"
	decl = []
	write = []
	read = []
	construct = []
	b_decl = []
	b_with = []
	traits = []
	complete = [pname]
	additional_getters = []
	imports = set()
	skip = False
	if len(p.fields) == 1:
		field = p.fields[0]
		rawtype = field.type.strip().lower()
		ftype = scala_type(rawtype)
		if ftype == "Nothing":
			skip = True
	for i in range(len(p.fields)):
		if skip:
			skip = False
			continue
		field = p.fields[i]
		fname = field.name
		rawtype = field.type.strip().lower()
		ftype = scala_type(rawtype)
		is_length_field = False
		if ftype in integers and i + 1 < len(p.fields):
			next_field = p.fields[i + 1]
			next_fname = next_field.name
			next_rawtype = next_field.type.strip().lower()
			next_ftype = scala_type(next_rawtype)
			if next_ftype.startswith("Array"):
				# type that has a length, except String (because in that case we have to use the utf8 byte count, not the character count)
				is_length_field = True
				skip = True

				fname = next_fname + "Length"
				length_field = field
				length_fname = fname
				length_rawtype = rawtype
				length_ftype = ftype

				field = next_field
				fname = next_fname
				rawtype = next_rawtype
				ftype = next_ftype

		if is_length_field:
			# Reads and writes the length before the actual value
			# The length field isn't in the constructor nor in the builder.
			length_fwrite = parametrize(niol_write(length_rawtype), "$", fname + ".length")
			write.append("    " + length_fwrite)

			length_fread = parametrize(niol_read(length_rawtype), "$", length_fname)
			read.append("    " + length_fread)

		name_and_type = "%s: %s" % (fname, ftype)
		decl.append("var " + name_and_type)
		b_decl.append("  private[this] var %s = _" % name_and_type)

		if "String" in ftype:
			imports.add("import java.nio.charset.StandardCharsets.UTF_8")
		elif "UUID" in ftype:
			imports.add("import java.util.UUID")
		elif "TagCompound" in ftype:
			imports.add("import com.electronwill.nbj.TagCompound")
			imports.add("import com.electronwill.niol.compatibility._")
		elif rawtype == "position":
			imports.add("import com.electronwill.utils.Vec3i")
		elif rawtype == "angle":
			imports.add("import com.electronwill.utils.{Pi2, InvPi2}")

		fwrite = parametrize(niol_write(rawtype), "$", fname)
		write.append("    " + fwrite)

		fread = parametrize(niol_read(rawtype), "$", fname)
		read.append("    " + fread)

		global todo_count
		global unhandled_type_count
		if "TODO" in fwrite:
			todo_count += 1
		if "TODO" in fread:
			todo_count += 1
		if ftype in ["???", "AnyRef", "Nothing"]:
			unhandled_type_count += 1

		construct.append(fname)

		fcapital = pascal_case(field.name_snake)
		with1 = "  def with%s(%s): %s[P with %s] = {" % (fcapital, name_and_type, bname, fcapital)
		with2 = "    this.%s = %s" % (fname, fname)
		with3 = "    this.asInstanceOf[%s[P with %s]]" % (bname, fcapital)
		with4 = "  }"
		b_with.append("\n".join([with1, with2, with3, with4]))

		if rawtype == "position":  # build with Vec3i instead of long
			with1 = "  def with%s(v: Vec3i): %s[P with %s] = {" % (fcapital, bname, fcapital)
			with2 = "    this.%s = ((v.x & 0x3ffffff) << 38) | ((v.y & 0xfff) << 26) | (v.z & 0x3ffffff)" % fname
			with3 = "    this.asInstanceOf[%s[P with %s]]" % (bname, fcapital)
			with4 = "  }"
			b_with.append("\n".join([with1, with2, with3, with4]))

			get1 = "  def vec%s: Vec3i = {" % fcapital
			get2 = "    val x = %s >> 38" % fname
			get3 = "    val y = (%s >> 26) & 0xfff" % fname
			get4 = "    val z = %s << 38 >> 38" % fname
			get5 = "    new Vec3i(x.toInt, y.toInt, z.toInt)"
			get6 = "  }"
			additional_getters.append("\n".join([get1, get2, get3, get4, get5, get6]))
		elif rawtype == "angle":
			with1 = "  def with%s(angle: Float): %s[P with %s] = {" % (fcapital, bname, fcapital)
			with2 = "    this.%s = (angle * InvPi2 * 256f).toByte  " % fname
			with3 = "    this.asInstanceOf[%s[P with %s]]" % (bname, fcapital)
			with4 = "  }"
			b_with.append("\n".join([with1, with2, with3, with4]))

			get1 = "  def rad%s: Float = {" % fcapital
			get2 = "    %s * Pi2 / 256f" % fname
			get3 = "  }"
			additional_getters.append("\n".join([get1, get2, get3]))

		traits.append("sealed trait %s" % fcapital)
		complete.append(fcapital)

	fields_declaration = ", ".join(decl)
	fields_writing = "\n".join(write)
	fields_reading = "\n".join(read)
	packet_constructing = ", ".join(construct)
	builder_fields = "\n".join(b_decl)
	builder_setters = "\n\n".join(b_with)
	traits_declaration = "\n  ".join(traits)
	mixin_declaration = " with ".join(complete)

	# TODO import tuubes.core.network.packets or something like this
	imports.add("import com.electronwill.niol.{NiolInput, NiolOutput}")
	imports.add("import org.tuubes.craft.CraftAttach")
	imports.add("import org.tuubes.core.network._")
	imports.add("import %s._" % bname)

	pclass = """
package %s

%s

/** Packet class auto-generated by DataTractor */
final class %s(%s) extends Packet[CraftAttach] {
  override def write(out: NiolOutput): Unit = {
%s
  }
	
  override def obj = %s

%s	
}
object %s extends PacketObj[CraftAttach, %s] {
  override val id = %d
	
  override def read(in: NiolInput): %s = {
%s
    new %s(%s)
  }
}
/** Packet builder auto-generated by DataTractor */
final class %s[P <: %s] extends PacketBuilder[%s, P =:= Complete] {
%s

%s

  override def build()(implicit evidence: P =:= Complete) = {
    new %s(%s)
  }
}
object %s {
  %s
  type Complete = %s
}
""" % (package,
	   "\n".join(imports),
	   pname, fields_declaration,
	   fields_writing,
	   pname,
	   "\n".join(additional_getters),
	   pname, pname,
	   p.id,
	   pname,
	   fields_reading,
	   pname, packet_constructing,

	   bname, pname, pname,
	   builder_fields,
	   builder_setters,
	   pname, packet_constructing,
	   bname,
	   traits_declaration,
	   mixin_declaration
	   )

	return pname, pclass.strip() + "\n"


def write_packet_class(folder, packet, package):
	pname, pclass = generate_packet_class(packet, package)
	output_file = "%s/%s.scala" % (folder, pname)
	f = open(output_file, "w+")
	f.write(pclass)
	f.close()


def generate_protocol_class(sub_protocol, package) -> (str, str):
	registrations = []
	sname = sub_protocol.name + "Protocol"
	sub_protocol.serverbound.sort(key=lambda x: x.name)
	for packet in sub_protocol.serverbound:
		pname = packet.name + "Packet"
		registrations.append("registerPacket(%s)" % pname)
	sclass = """
package %s

import %s.serverbound._
import org.tuubes.craft.MinecraftProtocol

/** Protocol class auto-generated by DataTractor */
object %s extends MinecraftProtocol {
  %s
}
""" % (package, package, sname, "\n  ".join(registrations))
	return sname, sclass.strip() + "\n"


def write_protocol_class(folder, sub_protocol, package):
	print("Generating %sProtocol..." % sub_protocol.name)
	sname, pclass = generate_protocol_class(sub_protocol, package)
	output_file = "%s/%s.scala" % (folder, sname)
	f = open(output_file, "w+")
	f.write(pclass)
	f.close()
