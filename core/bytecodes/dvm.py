
from core import bytecode
from core import dexobject
from core import dexinstructions

from core.autoconf import CONF, debug

import sys
import re
import struct
from struct import pack, unpack, calcsize

#dex file
DEX_FILE_MAGIC_35 = 'dex\n035\x00'
DEX_FILE_MAGIC_36 = 'dex\n036\x00'

#odex file
ODEX_FILE_MAGIC_35 = 'dey\n035\x00'
ODEX_FILE_MAGIC_36 = 'dey\n036\x00'

TYPE_MAP_ITEM = {
					0x0:	"TYPE_HEADER_ITEM",
					0x1:	"TYPE_STRING_ID_ITEM",
					0x2:	"TYPE_TYPE_ID_ITEM",
					0x3:	"TYPE_PROTO_ID_ITEM",
					0x4:	"TYPE_FIELD_ID_ITEM",
					0x5:	"TYPE_METHOD_ID_ITEM",
					0x6:	"TYPE_CLASS_DEF_ITEM",
					0x1000:	"TYPE_MAP_LIST",
					0x1001:	"TYPE_TYPE_LIST",
					0x1002:	"TYPE_ANNOTATION_SET_REF_LIST",
					0x1003:	"TYPE_ANNOTATION_SET_ITEM",
					0x2000:	"TYPE_CLASS_DATA_ITEM",
					0x2001: "TYPE_CODE_ITEM",
					0x2002:	"TYPE_STRING_DATA_ITEM",
					0x2003:	"TYPE_DEBUG_INFO_ITEM",
					0x2004:	"TYPE_ANNOTATION_ITEM",
					0x2005:	"TYPE_ENCODED_ARRAY_ITEM",
					0x2006:	"TYPE_ANNOTATIONS_DIRECTORY_ITEM",
				}

ACCESS_FLAGS = [
	(0x1, 'public'),
	(0x2, 'private'),
	(0x4, 'protected'),
	(0x8, 'static'),
	(0x10, 'final'),
	(0x20, 'synchronized'),
	(0x40, 'bridge'),
	(0x80, 'varargs'),
	(0x100, 'native'),
	(0x200, 'interface'),
	(0x400, 'abstract'),
	(0x800, 'strictfp'),
	(0x1000, 'synthetic'),
	(0x4000, 'enum'),
	(0x8000, 'unused'),
	(0x10000, 'constructor'),
	(0x20000, 'synchronized')
]

TYPE_DESCRIPTOR = {
	'V': 'void',
	'Z': 'boolean',
	'B': 'byte',
	'S': 'short',
	'C': 'char',
	'I': 'int',
	'J': 'long',
	'F': 'float',
	'D': 'double'
}


class PackedSwitch(object):
	"""
	"""
	def __init__(self, buff):
		self.notes = []
		self.format_general_size = calcsize("=HHI")

		self.ident = unpack("=H", buff[0:2])[0]
		self.size = unpack("=H", buff[2:4])[0]
		self.first_key = unpack("=i", buff[4:8])[0]

		self.targets = []

		idx = self.format_general_size

		max_size = self.size
		if (max_size * 4) > len(buff):
			max_size = len(buff) - idx - 8

		for i in xrange(0, max_size):
			self.targets.append(unpack("=l", buff[idx:idx + 4])[0])
			idx += 4

	def add_notes(self, msg):
		return self.notes

	def get_op_value(self):
		return self.ident

	def get_keys(self):
		return [(self.first_key + i) for i in range(0, len(self.targets))]

	def get_values(self):
		return self.get_keys()

	def get_targets(self):
		return self.targets

	def get_output(self, idx=-1):
		return " ".join("%x" % ((self.first_key + i) for i in range(0, len(self.targets))))

	def get_operands(self, idx=-1):
		return []

	def get_formatted_operands(self):
		return None

	def get_name(self):
		return "packed-switch-payload"

	def show_buff(self, idx=-1):
		buff = self.get_name() + " "
		buff += "%x" % self.first_key

		for i in self.targets:
			buff += " %x" % i

		return buff

	def show(self, pos):
		print self.show_buff(pos)

	def get_length(self):
		return self.format_general_size + (self.size * calcsize('=L'))

	def get_raw(self):
		return pack("=H", self.ident) + pack("=H", self.size) + pack("=i", self.first_key) + ''.join(pack("=l", i) for i in self.targets)

class SparseSwitch(object):
	"""
	"""
	def __init__(self, buff):
		self.notes = []
		self.format_general_size = calcsize("=HH")
		self.ident = unpack("=H", buff[0:2])[0]
		self.size = unpack("=H", buff[2:4])[0]

		self.keys = []
		self.targets = []

		idx = self.format_general_size
		for i in xrange(0, self.size):
			self.keys.append(unpack('=l', buff[idx:idx + 4])[0])
			idx += 4

		for i in xrange(0, self.size):
			self.targets.append(unpack("=l", buff[idx:idx + 4])[0])
			idx += 4

	def add_notes(self, msg):
		self.notes.append(msg)

	def get_notes(self):
		return self.notes

	def get_op_value(self):
		return self.ident

	def get_keys(self):
		return self.keys

	def get_targets(self):
		return self.targets

	def get_output(self, idx=-1):
		return " ".join("%x" % i for i in self.keys)

	def get_formatted_operands(self):
		return None

	def get_name(self):
		return "sparse-switch-payload"

	def show_buff(self, pos):
		buff = self.get_name() + " "
		for i in xrange(0, len(self.keys)):
			buff += "%x:%x " % (self.keys[i], self.targets[i])

		return buff

	def show(self, pos):
		print self.show_buff(pos)

	def get_length(self):
		return self.format_general_size + (self.size * calcsize('<L')) * 2

	def get_raw(self):
		return pack("=H", self.ident) + pack("=H", self.size) + ''.join(pack("=l", i) for i in self.keys)


class FillArrayData(object):
	"""
	"""
	def __init__(self, buff):
		self.notes = []
		self.format_general_size = calcsize("=HHI")
		self.ident = unpack("=H", buff[0:2])[0]
		self.element_width = unpack("=H", buff[2:4])[0]
		self.size = unpack("=I", buff[4:8])[0]

		self.data = buff[self.format_general_size:self.format_general_size + (self.size * self.element_width)]

	def add_note(self, msg):
		self.notes.append(msg)

	def get_notes(self):
		return self.notes

	def get_op_value(self):
		return self.ident

	def get_output(self, idx=-1):
		buff = ""
		data = self.get_data()

		buff += repr(data) + " | "
		for i in xrange(0, len(data)):
			buff += "\\x%02x" % ord(data[i])

		return buff

	def get_operands(self, idx=-1):
		return [(OPERAND_RAW, repr(self.get_data()))]

	def get_formatted_operands(self):
		return None

	def get_name(self):
		 return "fill-array-data-payload"

	def show_buff(self, pos):
		buff = self.get_name() + " "

		for i in xrange(0, len(self.data)):
			buff += "\\x%02x" % ord(self.data[i])
		return buff	    

	def get_raw(self):
		return pack("=H", self.ident) + pack("=H", self.element_width) + pack("=I", self.size) + self.data


	def show(self, pos):
		print self.show_buff(pos)

	def get_length(self):
		return ((self.size * self.element_width + 1) / 2 + 4) * 2

	def get_raw(self):
		return pack("=H", self.ident) + pack("=H", self.element_width) + pack("=I", self.size) + self.data


DALVIK_OPCODES_PAYLOAD = {
	0x0100 : [PackedSwitch],
	0x0200 : [SparseSwitch],
	0x0300 : [FillArrayData],
}

def get_access_flags_string(value):
	buff = ""
	for i in ACCESS_FLAGS:
		if (i[0] & value) == i[0]:
			buff += i[1] + " "

	if buff != "":
		return buff[:-1]
	return buff

def get_type(atype, size=None):
	if atype.startswith('java.lang'):
		atype = atype.replace('java.lang.', '')
	res = TYPE_DESCRIPTOR.get(atype.lstrip('java.lang'))
	if res is None:
		if atype[0] == 'L':
			res = atype[1:-1].replace('/', '.')
		elif atype[0] == '[':
			if size is None:
				res = '%s[]' % get_type(atype[1:])
			else:
				res = '%s[%s]' % (get_type(atype[1:]), size)
		else:
			res = atype
	return res	

def get_instruction(cm, op_value, buff, odex=False):
	print "opcode ", op_value
	if not odex and (op_value >= 0xe3 and op_value <= 0xfe):
		return InstructionInvalid(cm, buff)

	try:
		print "point 3"
		return dexinstructions.DALVIK_OPCODES_FORMAT[op_value][0](cm, buff)
	except KeyError:
		return InstructionInvalid(cm, buff)
	#except:
	#	return dexinstructions.Unresolved(cm, buff)

def get_instruction_payload(op_value, buff):
	return DALVIK_OPCODES_PAYLOAD[op_value][0]( buff )


class StringIdItem(object):
	"""
		This class can parse a string_id_item of a dex file.
	"""
	def __init__(self, buff, cm):
		self.__CM = cm
		self.offset = buff.get_idx()
		self.string_data_off = unpack("=I", buff.read(4))[0]

	def get_string_data_off(self):
		return self.string_data_off

	def set_off(self, off):
		self.offset = off

	def get_off(self):
		return self.offset

	def show(self):
		bytecode._PrintSubBanner("String Id Item")
		if self.string_data_off != None:
			bytecode._PrintDefault("string_data_off=%x\n" % self.string_data_off)

	def reload(self):
		pass

class TypeIdItem(object):
	"""
		This class can parse a type_id_item of a dex file.
	"""
	def __init__(self, buff, cm):
		self.__CM = cm
		self.offset = buff.get_idx()
		self.descriptor_idx = unpack("=I", buff.read(4))[0]
		self.descriptor_idx_value = None

	def get_descriptor_idx(self):
		return self.descriptor_idx

	def show(self):
		bytecode._PrintSubBanner("Type Id Item")
		bytecode._PrintDefault("descriptor_idx=%d descriptor_idx_value=%s\n" % (self.descriptor_idx, self.descriptor_idx_value))

	def reload(self):
		self.descriptor_idx_value = self.__CM.get_string(self.descriptor_idx)

class TypeHIdItem(object):
	"""
	"""
	def __init__(self, size, buff, cm):
		self.__CM = cm
		self.offset = buff.get_idx()
		self.type = []
		for i in xrange(0, size):
			self.type.append(TypeIdItem(buff, cm))

	def get_type(self):
		return self.type

	def get(self, idx):
		try:
			return self.type[idx].get_descriptor_idx()
		except IndexError:
			return -1

	def set_off(self, off):
		self.offset = off

	def get_off(self):
		self.offset = off

	def get_off(self):
		return self.offset

	def reload(self):
		for i in self.type:
			i.reload()

	def show(self):
		bytecode._PrintSubBanner("Type List Item")
		for i in self.type:
			i.show()


class ProtoIdItem(object):
	"""
	"""
	def __init__(self, buff, cm):
		self.__CM = cm
		self.offset = buff.get_idx()

		self.shorty_idx = unpack("=I", buff.read(4))[0]
		self.return_type_idx = unpack("=I", buff.read(4))[0]
		self.parameters_off = unpack("=I", buff.read(4))[0]

		self.shorty_idx_value = None
		self.return_type_idx_value = None
		self.parameters_off_value = None

	def reload(self):
		self.shorty_idx_value = self.__CM.get_string(self.shorty_idx)
		self.return_type_idx_value = self.__CM.get_string(self.return_type_idx)
		params = self.__CM.get_type_list(self.parameters_off)
		self.parameters_off_value = '({})'.format(' '.join(params))

	def show(self):
		bytecode._PrintSubBanner("Proto Item")
		bytecode._PrintDefault("shorty_idx=%d return_type_idx=%d parameters_off=%d\n" 
			% (self.shorty_idx, self.return_type_idx, self.parameters_off))
		bytecode._PrintDefault("shorty_idx_value=%s return_type_idx=%s parameters_off_value=%s\n" 
			% (self.shorty_idx_value, self.return_type_idx_value, self.parameters_off_value))

	def get_parameters_off_value(self):
		return self.parameters_off_value

	def get_return_type_idx_value(self):
		return self.return_type_idx_value

class ProtoHIdItem(object):
	"""
	"""
	def __init__(self, size, buff, cm):
		self.__CM = cm
		self.offset = buff.get_idx()

		self.proto = []

		for i in xrange(0, size):
			self.proto.append(ProtoIdItem(buff, cm))

	def get_off(self):
		return self.offset

	def set_off(self, off):
		self.offset = off

	def get(self, idx):
		try:
			return self.proto[idx]
		except IndexError:
			pass

	def get_obj(self):
		return [i for i in self.proto]

	def get_raw(self):
		return ''.join(i.get_raw() for i in self.proto)

	def get_length(self):
		length = 0
		for i in self.proto:
			length += i.get_length()
		return length
	
	def show(self):
		bytecode._PrintSubBanner("Proto List Item")
		for u in self.proto:
			u.show()

	def reload(self):
		for i in self.proto:
			i.reload()

class FieldIdItem(object):
	"""
	"""
	def __init__(self, buff, cm):
		self.__CM = cm
		self.offset = buff.get_idx()

		self.class_idx = unpack("=H", buff.read(2))[0]
		self.type_idx = unpack("=H", buff.read(2))[0]
		self.name_idx = unpack("=I", buff.read(4))[0]

		self.class_idx_value = None
		self.type_idx_value = None
		self.name_idx_value = None

	def show(self):
		bytecode._PrintSubBanner("Field Id type")
		bytecode._PrintDefault("class_idx=%d type_idx=%d name_idx=%d\n" 
			% (self.class_idx, self.type_idx, self.name_idx))
		bytecode._PrintDefault("class_idx_value=%s type_idx_value=%s name_idx_value=%s\n"
			% (self.class_idx_value, self.type_idx_value, self.name_idx_value))

	def reload(self):
		self.class_idx_value = self.__CM.get_type(self.class_idx)
		self.type_idx_value = self.__CM.get_type(self.type_idx)
		self.name_idx_value = self.__CM.get_string(self.name_idx)

	def get_class_name(self):
		return self.class_idx_value

	def get_type(self):
		return self.type_idx_value

	def get_name(self):
		return self.name_idx_value

class FieldHIdItem(object):
	"""
	"""
	def __init__(self, size, buff, cm):
		self.__CM = cm
		self.offset = buff.get_idx()
		self.elem = []
		for i in xrange(0, size):
			self.elem.append(FieldIdItem(buff, cm))

	def show(self):
		bytecode._PrintDefault("Field Id")
		for u in self.elem:
			u.show()

	def reload(self):
		for i in self.elem:
			i.reload()

	def get(self, idx):
		try:
			return self.elem[idx]
		except IndexError:
			return -1

class MethodIdItem(object):
	"""
	"""
	def __init__(self, buff, cm):
		self.__CM = cm
		self.offset = buff.get_idx()

		self.class_idx = unpack("=H", buff.read(2))[0]
		self.proto_idx = unpack("=H", buff.read(2))[0]
		#self.raw_name = buff.read(4)
		self.name_idx = 0#unpack("=I", buff.read(4))[0] 

		self.class_idx_value = None
		self.proto_idx_value = None
		self.name_idx_value = None

	def show(self):
		bytecode._PrintSubBanner("Method Id Item")
		bytecode._PrintDefault("class_idx=%d proto_idx=%d name_idx=%d\n"
			% (self.class_idx, self.proto_idx, self.name_idx))
		bytecode._PrintDefault("class_idx_value=%s proto_idx_value=%s name_idx_value=%s\n"
			% (self.class_idx_value, self.proto_idx_value, self.name_idx_value))

	def reload(self):
		self.class_idx_value = self.__CM.get_type(self.class_idx)
		self.proto_idx_value = self.__CM.get_proto(self.proto_idx)
		self.name_idx_value = self.__CM.get_string(self.name_idx)

	def get_class_name(self):
		return self.class_idx_value

	def get_name(self):
		return self.name_idx_value

	def get_proto(self):
		return self.proto_idx_value

	def get_descriptor(self):
		proto = self.get_proto()
		return proto[0] + proto[1]


class MethodHIdItem(object):
	"""
	"""
	def __init__(self, size, buff, cm):
		self.__CM = cm
		self.offset = buff.get_idx()

		self.methods = []
		for i in xrange(0, size):
			self.methods.append(MethodIdItem(buff, cm))

	def show(self):
		bytecode._PrintSubBanner("Method Id Item")
		for u in self.methods:
			u.show()

	def reload(self):
		for i in self.methods:
			i.reload()

	def get(self, idx):
		try:
			return self.methods[ idx ]
		except IndexError:
			return MethodIdItemInvalid()

class ClassDefItem(dexobject.DexObject):
	"""
	"""
	def __init__(self, buff, cm):
		dexobject.DexObject.__init__(self, buff, cm)

		self.class_idx = unpack("=I", buff.read(4))[0]
		self.access_flag = unpack("=I", buff.read(4))[0]
		self.superclass_idx = unpack("=I", buff.read(4))[0]
		self.interfaces_off = unpack("=I", buff.read(4))[0]
		self.source_file_idx = unpack("=I", buff.read(4))[0]
		self.annotations_off = unpack("=I", buff.read(4))[0]
		self.class_data_off = unpack("=I", buff.read(4))[0]
		self.static_values_off = unpack("=I", buff.read(4))[0]

		self.interfaces = []
		self.class_data_item = None
		self.static_values = None
		self.access_flags_string = None
		self.name = None
		self.sname = None

	def show(self):
		bytecode._PrintSubBanner("Class Def Item")
		bytecode._PrintDefault("name=%s, sname=%s, interfaces=%s, access_flag=%s\n"
			% (self.name, self.sname, self.interfaces, self.get_access_flag_string()))
		bytecode._PrintDefault("class_idx=%d, superclass_idx=%d, interfaces_off=%x, source_file_idx=%d\n"
			% (self.class_idx, self.superclass_idx, self.interfaces_off, self.source_file_idx))
		
	def get_access_flag_string(self):
		return self.access_flags_string

	def reload(self):
		self.name = self.CM.get_type(self.class_idx)
		self.sname = self.CM.get_type(self.superclass_idx)
		self.interfaces = self.CM.get_type_list(self.interfaces_off)

		if self.class_data_off != 0:
			self.class_data_item = self.CM.get_class_data_item(self.class_data_off)
			self.class_data_item.reload()

		if self.static_values_off != 0:
			self.static_values = self.CM.get_encoded_array_item(self.static_values_off)

			if self.class_data_item != None:
				self.class_data_item.set_static_fields(self.static_values.get_value())


class ClassHDefItem(object):
	"""
	"""
	def __init__(self, size, buff, cm):
		self.__CM = cm
		self.offset = buff.get_idx()

		self.classes = []
		for i in xrange(0, size):
			idx = buff.get_idx()
			class_def = ClassDefItem(buff, cm)
			self.classes.append(class_def)
			buff.set_idx(idx + calcsize("=IIIIIIII"))

	def show(self):
		bytecode._PrintSubBanner("CLASS DEF ITEM")

		for u in self.classes:
			u.show()

	def reload(self):
		for u in self.classes:
			u.reload()


class CodeItem(object):
	def __init__(self, size, buff, cm):
		self.__CM = cm
		self.offset = buff.get_idx()
		self.code = []
		self.__code_off = {}

		for i in xrange(0, size):
			x = DalvikCode(buff, cm)
			self.code.append(x)
			self.__code_off[x.get_off()] = x


	def show(self):
		print "CODE_ITEM"
		for i in self.code:
			i.show()

	def reload(self):
		for i in self.code:
			i.reload()

class ClassManager(object):
	def __init__(self, vm, config):
		self.vm = vm
		self.buff = vm

		self.decompiler_ob = None
		self.vmanalysis_ob = None
		self.gvmanalysis_ob = None
		
		self.__manage_item = {}
		self.__manage_item_off = []

		self.__strings_off = {}
		self.__obj_offset = {}
		self.__item_offset = {}
		self.__cached_proto = {}

		self.recode_ascii_string = config["RECODE_ASCII_STRING"]
		self.recode_ascii_sting_meth = None
		if config["RECODE_ASCII_STRING_METH"]:
			self.recode_ascii_sting_meth = config["RECODE_ASCII_STRING_METH"]

		self.lazy_analysis = config["LAZY_ANALYSIS"]
		self.hook_strings = {}

		self.engine = []
		self.engine.append("python")

		if self.vm != None:
			self.odex_format = self.vm.get_format_type =="ODEX"

	def get_ascii_string(self, s):
		try:
			return s.decode("ascii")
		except UnicodeDecodeError:
			d = ""
			for i in s:
				if ord(i) < 128:
					d+= i
				else:
					d += "%x" % ord(i)
				return d

	def get_odex_format(self):
		return self.odex_format

	def set_decompiler(self, decompiler):
		self.decompiler_ob = decompiler

	def get_lazy_analysis(self):
		pass

	def get_type_list(self, off):
		if off == 0:
			return []

		for i in self.__manage_item["TYPE_TYPE_LIST"]:
			if i.get_type_list_off() == off:
				return [type_.get_string() for type_ in i.get_list()]

	def get_type(self, ttype):
		_type = self.__manage_item["TYPE_TYPE_ID_ITEM"].get(ttype)
		if _type == -1:
			return "invalid type"
		return self.get_string(_type)

	def get_string(self, index):
		if index in self.hook_strings:
			return self.hook_strings[index]

		try:
			off = self.__manage_item["TYPE_STRING_ID_ITEM"][index].get_string_data_off()
		except IndexError:
			return "Invalid String"

		try:
			if self.recode_ascii_string:
				if self.recode_ascii_sting_meth:
					return self.recode_ascii_sting_meth(self.__strings_off[off].get())

				return self.get_ascii_string(self.__strings_off[off].get())
			return self.__strings_off[off].get()
		except KeyError:
			print ("unknown string item")
			return "Invalid String"

	def get_proto(self, idx):
		try:
			proto = self.__cached_proto[idx]
		except KeyError:
			proto = self.__manage_item["TYPE_PROTO_ID_ITEM"].get(idx)
			self.__cached_proto[idx] = proto

		return [proto.get_parameters_off_value(), proto.get_return_type_idx_value()]

	def add_type_item(self, type_item, c_item, item):
		self.__manage_item[type_item] = item
		self.__obj_offset[c_item.get_off()] = c_item
		self.__item_offset[c_item.get_offset()] = item

		sdi = False
		if type_item == "TYPE_STRING_DATA_ITEM":
			sdi = True

		if item != None:
			if isinstance(item, list):
				for i in item:
					goff = i.offset
					self.__manage_item_off.append(goff)
					self.__obj_offset[i.get_off()] = i

					if sdi == True:
						self.__strings_off[goff] = i
			else:
				self.__manage_item_off.append(c_item.get_offset())

	def get_next_offset_item(self, idx):
		for i in self.__manage_item_off:
			if i > idx:
				return i
		return idx

	def get_field(self, idx):
		field = self.__manage_item["TYPE_FIELD_ID_ITEM"].get(idx)
		return [field.get_class_name(), field.get_type(), field.get_name()]

	def get_field_ref(self, idx):
		return self.__manage_item["TYPE_FIELD_ID_ITEM"].get(idx)

	def get_method(self, idx):
		method = self.__manage_item["TYPE_METHOD_ID_ITEM"].get(idx)
		return method.get_list()

	def get_method_ref(self, idx):
		return self.__manage_item["TYPE_METHOD_ID_ITEM"].get(idx)

	def get_class_data_item(self, off):
		for i in self.__manage_item["TYPE_CLASS_DATA_ITEM"]:
			if i.get_off() == off:
				return i

	def get_encoded_array_item(self, off):
		for i in self.__manage_item["TYPE_ENCODED_ARRAY_ITEM"]:
			if i.get_off() == off:
				return i

	def get_raw_string(self, idx):
		try:
			off = self.__manage_item["TYPE_STRING_ID_ITEM"][idx].get_string_data_off()
		except IndexError:
			warning("unknown index")
			return "Invalid String"

		try:
			return self.__strings_off[off].get()
		except KeyError:
			warning("Unknown string item")
			return "Invalid String"


class HeaderItem(object):
	def __init__(self, size, buff, cm):
		self.__CM = cm

		self.offset = buff.get_idx()
		print "start index ", self.offset

		self.magic = unpack("=Q", buff.read(8))[0]
		self.checksum = unpack("=i", buff.read(4))[0]
		self.signature = unpack("=20s", buff.read(20))[0]
		self.file_size = unpack("=I", buff.read(4))[0]
		self.header_size = unpack("=I", buff.read(4))[0]
		self.endian_tag = unpack("=I", buff.read(4))[0]
		self.link_size = unpack("=I", buff.read(4))[0]
		self.link_off = unpack("=I", buff.read(4))[0]
		self.map_off = unpack("=I", buff.read(4))[0]
		self.string_ids_size = unpack("=I", buff.read(4))[0]
		self.string_ids_off = unpack("=I", buff.read(4))[0]
		self.type_ids_size = unpack("=I", buff.read(4))[0]
		self.type_ids_off = unpack("=I", buff.read(4))[0]
		self.proto_ids_size = unpack("=I", buff.read(4))[0]
		self.proto_ids_off = unpack("=I", buff.read(4))[0]
		self.field_ids_size = unpack("=I", buff.read(4))[0]
		self.field_ids_off = unpack("=I", buff.read(4))[0]
		self.method_ids_size = unpack("=I", buff.read(4))[0]
		self.method_ids_off = unpack("=I", buff.read(4))[0]
		self.class_defs_size = unpack("=I", buff.read(4))[0]
		self.class_defs_off = unpack("=I", buff.read(4))[0]
		self.data_size = unpack("=I", buff.read(4))[0]
		self.data_off = unpack("=I", buff.read(4))[0]

		print "end index", buff.get_idx()

		self.map_off_obj = None
		self.string_off_obj = None
		self.type_off_obj = None
		self.proto_off_obj = None
		self.field_off_obj = None
		self.method_off_obj = None
		self.class_off_obj = None
		self.data_off_obj = None

	def reload(self):
		pass

	def get_obj(self):
		if self.map_off_obj == None:
			self.map_off_obj = self.__CM.get_item_by_offset(self.map_off)

		if self.string_off_obj == None:
			self.string_off_obj = self.__CM.get_item_by_offset(self.string_ids_off)

		if self.type_off_obj == None:
			self.type_off_obj = self.__CM.get_item_by_offset(self.type_ids_off)

		if self.proto_off_obj == None:
			self.proto_off_obj = self.__CM.get_item_by_offset(self.proto_ids_off)

		if self.field_off_obj == None:
			self.field_off_obj = self.__CM.get_item_by_offset(self.field_ids_off)

		if self.method_off_obj == None:
			self.method_off_obj = self.__CM.get_item_by_offset(self.method_ids_off)

		if self.class_off_obj == None:
			self.class_off_obj = self.__CM.get_item_by_offset(self.class_defs_off)

		if self.data_off_obj == None:
			self.data_off_obj = self.__CM.get_item_by_offset(self.data_off)

		self.map_off = self.map_off_obj.get_off() 

		self.string_ids_size = len(self.string_off_obj)
		self.string_ids_off = self.string_off_obj[0].get_off()

		self.type_ids_size = len(self.type_off_obj.type)
		self.type_ids_off = self.type_off_obj[0].get_off()

		self.proto_ids_size = len(self.proto_off_obj.proto)
		self.proto_ids_off = self.proto_off_obj.get_off()

		self.field_ids_size = len(self.field_off_obj.elem)
		self.field_ids_off = self.field_off_obj.get_off()
		
		self.method_ids_size = len(self.method_off_obj.methods)
		self.method_ids_off = self.method_off_obj.get_off()

		self.class_defs_size = len(self.class_off_obj.class_def)
		self.class_defs_off = self.class_off_obj.get_off()

		self.data_size = len(self.data_off_obj)
		self.data_off = self.data_off_obj[0].get_off()

		return pack("=Q", self.magic) +				\
				pack("=I", self.checksum) +			\
				pack("=20s", self.signature) +		\
				pack("=I", self.file_size) +		\
				pack("=I", self.header_size) +		\
				pack("=I", self.endian_tag) +		\
				pack("=I", self.link_size) +		\
				pack("=I", self.link_off) +			\
				pack("=I", self.map_off) +			\
				pack("=I", self.string_ids_size) +	\
				pack("=I", self.string_ids_off) +	\
				pack("=I", self.type_ids_size) +	\
				pack("=I", self.type_ids_off) +		\
				pack("=I", self.proto_ids_size) +	\
				pack("=I", self.proto_ids_off) +	\
				pack("=I", self.field_ids_size) +	\
				pack("=I", self.field_ids_off) +	\
				pack("=I", self.method_ids_size) +	\
				pack("=I", self.method_ids_off) +	\
				pack("=I", self.class_defs_size) +	\
				pack("=I", self.class_defs_off) +	\
				pack("=I", self.data_size) +		\
				pack("=I", self.data_off)


	def get_raw():
		return self.get_obj()

	def get_length(self):
		return len(self.get_raw())

	def show(self):
		bytecode._PrintSubBanner("Header Item")
		bytecode._PrintDefault("magic=%s, checksum=%s, signature=%s\n" % (self.magic, self.checksum, self.signature))
		bytecode._PrintDefault("file_size=%x, header_size=%x, endian_tag=%x\n" % (self.file_size, self.header_size, self.endian_tag))
		bytecode._PrintDefault("link_size=%x, link_off=%x\n" % (self.link_size, self.link_off))
		bytecode._PrintDefault("map_off=%x\n" %(self.map_off))
		bytecode._PrintDefault("string_ids_size=%x, string_ids_off=%x\n" % (self.string_ids_size, self.string_ids_off))


class StringDataItem(object):
	"""
	"""
	def __init__(self, buff, cm):
		self.__CM = cm
		self.offset = buff.get_idx()
		self.utf16_size = bytecode.readuleb128(buff)

		self.data = bytecode.utf8_to_string(buff, self.utf16_size)
		expected = buff.read(1)
		if expected != '\x00':
			pass

	def get_utf16_size(self):
		return self.utf16_size

	def get_data(self):
		return self.data

	def get_off(self):
		return self.offset

	def set_off(self, off):
		self.offset = off

	def reload(self):
		pass

	def get(self):
		return self.data

	def show(self):
		bytecode._PrintSubBanner("String Data Item")
		bytecode._PrintDefault("utf16_size=%d data=%s\n" % (self.utf16_size, repr( self.data )))

class MapItem(object):
	def __init__(self, buff, cm):
		self.__CM = cm
		self.off = buff.get_idx()
		self.type = unpack("=H", buff.read(2))[0]
		self.unused = unpack("=H", buff.read(2))[0]
		self.size = unpack("=I", buff.read(4))[0]
		self.offset = unpack("=I", buff.read(4))[0]
		self.item = None
		buff.set_idx(self.offset)

		lazy_analysis = self.__CM.get_lazy_analysis()

		if lazy_analysis:
			self.next_lazy(buff, cm)
		else:
			self.next(buff, cm)

	def get_off(self):
		return self.off

	def get_offset(self):
		return self.offset

	def get_type(self):
		"""
			This function returns the item type from the map list.
		"""
		return self.type

	def get_size(self):
		return self.size

	def next(self, buff, cm):
		debug_str = "%s @ 0x%x(%d) %x %x" % (TYPE_MAP_ITEM[self.type], buff.get_idx(), buff.get_idx(), self.size, self.offset)
		print debug_str

		if TYPE_MAP_ITEM[self.type] == "TYPE_STRING_ID_ITEM":
			print "TYPE_STRING_ID_ITEM"
			self.item = [StringIdItem(buff, cm) for i in xrange(0, self.size)]

		elif TYPE_MAP_ITEM[self.type] == "TYPE_CODE_ITEM":
			print "TYPE_CODE_ITEM"
			self.item = CodeItem(self.size, buff, cm)

		elif TYPE_MAP_ITEM[self.type] == "TYPE_TYPE_ID_ITEM":
			print "TYPE_TYPE_ID_ITEM"
			self.item = TypeHIdItem(self.size, buff, cm)

		elif TYPE_MAP_ITEM[self.type] == "TYPE_PROTO_ID_ITEM":
			print "TYPE_PROTO_ID_ITEM"
			self.item = ProtoHIdItem(self.size, buff, cm)

		elif TYPE_MAP_ITEM[self.type] == "TYPE_FIELD_ID_ITEM":
			print "TYPE_FIELD_ID_ITEM"
			self.item = FieldHIdItem(self.size, buff, cm)

		elif TYPE_MAP_ITEM[self.type] == "TYPE_METHOD_ID_ITEM":
			print "TYPE_METHOD_ID_ITEM"
			self.item = MethodHIdItem(self.size, buff, cm)

		elif TYPE_MAP_ITEM[self.type] == "TYPE_CLASS_DEF_ITEM":
			print "TYPE_CLASS_DEF_ITEM"
			self.item = ClassHDefItem(self.size, buff, cm)

		elif TYPE_MAP_ITEM[self.type] == "TYPE_HEADER_ITEM":
			print "TYPE_HEADER_ITEM"
			self.item = HeaderItem(self.size, buff, cm)
		
		elif TYPE_MAP_ITEM[self.type] == "TYPE_ANNOTATION_ITEM":
			print "TYPE_ANNOTATION_ITEM"
			self.item = [dexobject.AnnotationItem(buff, cm) for i in xrange(0, self.size)]

		elif TYPE_MAP_ITEM[self.type] == "TYPE_ANNOTATION_SET_ITEM":
			print "TYPE_ANNOTATION_SET_ITEM"
			self.item = [dexobject.AnnotationSetItem(buff, cm) for i in xrange(0, self.size)]

		elif TYPE_MAP_ITEM[self.type] == "TYPE_ANNOTATIONS_DIRECTORY_ITEM":
			print "TYPE_ANNOTATIONS_DIRECTORY_ITEM"
			self.item = [dexobject.AnnotationsDirectoryItem(buff, cm) for i in xrange(0, self.size) ]

		elif TYPE_MAP_ITEM[self.type] == "TYPE_ANNOTATION_SET_REF_LIST":
			print "TYPE_ANNOTATION_SET_REF_LIST"
			self.item = [dexobject.AnnotationSetRefList(buff, cm) for i in xrange(0, self.size)]

		elif TYPE_MAP_ITEM[self.type] == "TYPE_TYPE_LIST":
			self.item = [dexobject.TypeList(buff, cm) for i in xrange(0, self.size)]

		elif TYPE_MAP_ITEM[self.type] == "TYPE_STRING_DATA_ITEM":
			print "TYPE_STRING_DATA_ITEM"
			self.item = [ StringDataItem( buff, cm ) for i in xrange(0, self.size) ]

		elif TYPE_MAP_ITEM[self.type] == "TYPE_DEBUG_INFO_ITEM":
			print "TYPE_DEBUG_INFO_ITEM"
			self.item = dexobject.DebugInfoItemEmpty(buff, cm)

		elif TYPE_MAP_ITEM[self.type] == "TYPE_ENCODED_ARRAY_ITEM":
			print "TYPE_ENCODED_ARRAY_ITEM"
			self.item = [dexobject.EncodedArrayItem(buff, cm) for i in xrange(0, self.size) ]

		elif TYPE_MAP_ITEM[self.type] == "TYPE_CLASS_DATA_ITEM":
			print "TYPE_CLASS_DATA_ITEM : ", self.size
			self.item = [dexobject.ClassDataItem(buff, cm) for i in xrange(0, self.size)]

		elif TYPE_MAP_ITEM[self.type] == "TYPE_MAP_LIST":
			print "TYPE_MAP_LIST"
		else:
			print "Find this type : ", self.type


	def get_length(self):
		return calcsize("=HHII")

	def get_item(self):
		return self.item

	def set_item(self, item):
		self.item = item

	def show(self):
		if self.item != None:
			if isinstance(self.item, list):
				for i in self.item:
					i.show()
			else:
				self.item.show()

	def reload(self):
		if self.item != None:
			if isinstance(self.item, list):
				for i in self.item:
					i.reload()
			else:
				self.item.reload()

class MapList(object):
	def __init__(self, cm, off, buff):
		self.CM = cm
		buff.set_idx(off)
		self.offset = off

		self.size = unpack("=I", buff.read(4))[0]
		self.map_item = []

		#print "inside MapList; offset : ", self.offset, " size : ", self.size
		for i in xrange(0, self.size):
			idx = buff.get_idx()
			mi = MapItem(buff, self.CM)
			
			self.map_item.append(mi)
			buff.set_idx(idx + mi.get_length())
			c_item = mi.get_item()
			if c_item is None:
				mi.set_item(self)
				c_item = mi.get_item()

			self.CM.add_type_item(TYPE_MAP_ITEM[mi.get_type()], mi, c_item)

		for i in self.map_item:
			i.reload()

	def reload(self):
		pass

	def get_item_type(self, ttype):
		for i in self.map_item:
			if TYPE_MAP_ITEM[i.get_type()] == ttype:
				return i.get_item()
		return None

	def show(self):
		"""
			Print the MapList object
		"""
		#bytecode._Print("MAP_LIST SIZE", self.size)
		for i in self.map_item:
			if i.item != self:
				i.show()

class TryItem(object):
	"""
	"""
	def __init__(self, buff, cm):
		self.offset = buff.get_idx()
		print "inside try item : ", self.offset
		self.__CM = cm
		self.start_addr = unpack("=I", buff.read(4))[0]
		self.insn_count = unpack("=H", buff.read(2))[0]
		self.handler_off = unpack("=H", buff.read(2))[0]

	def set_offset(self, off):
		self.offset = off

	def get_off(self):
		return self.offset

class EncodedTypeAddrPair(object):
	"""
	"""
	def __init__(self, buff):
		self.offset = buff.get_idx()

		print "EncodedTypeAddrPair : ", self.offset
		self.type_idx = bytecode.readuleb128(buff)
		self.addr = bytecode.readuleb128(buff)

class EncodedCatchHandler(object):
	"""
	"""
	def __init__(self, buff, cm):
		self.offset = buff.get_idx()

		self.size = bytecode.readuleb128(buff)
		if self.size > 0x3f:
			self.size = self.size - 128
		self.handlers = []

		print "EncodedCatchHandler : ", self.offset, " : ", self.size

		for i in xrange(0, abs(self.size)):
			self.handlers.append( EncodedTypeAddrPair(buff))

		if self.size <= 0:
			self.catch_all_addr = bytecode.readuleb128(buff)


class EncodedCatchHandlerList(object):
	"""
	"""
	def __init__(self, buff, cm):
		self.offset = buff.get_idx()

		print "EncodedCatchHandlerList : ", self.offset
		self.size = bytecode.readuleb128(buff)
		self.list = []

		for i in xrange(0, self.size):
			self.list.append(EncodedCatchHandler(buff, cm))

class DalvikCode(object):
	"""
		This class represents the instructions of a method
	"""
	def __init__(self, buff, cm):
		self.__CM = cm
		self.offset = buff.get_idx()

		#print "offset : ", self.offset
		
		self.int_padding = ""
		off = buff.get_idx()
		while off % 4 != 0:
			self.int_padding += '\00'
			off += 1
		buff.set_idx(off)

		self.__off = buff.get_idx()
		#print "debug offset : ", self.__off
		self.registers_size = unpack("=H", buff.read(2))[0]
		self.ins_size = unpack("=H", buff.read(2))[0]
		self.outs_size = unpack("=H", buff.read(2))[0]
		self.tries_size = unpack("=H", buff.read(2))[0]
		self.debug_info_off = unpack("=I", buff.read(4))[0]
		self.insns_size = unpack("=I", buff.read(4))[0]

		ushort = calcsize('=H')

		#print "read size : ", self.insns_size * ushort

		self.code = DCode(self.__CM, buff.get_idx(), self.insns_size, buff.read(self.insns_size * ushort))

		if (self.insns_size % 2 == 1):
			self.padding = unpack("=H", buff.read(2))[0]

		self.tries = []
		self.handlers = None
		if self.tries_size > 0:
			for i in xrange(0, self.tries_size):
				self.tries.append(TryItem(buff, self.__CM))

			self.handlers = EncodedCatchHandlerList(buff, self.__CM)

	def get_registers_size(self):
		return self.registers_size

	def get_off(self):
		return self.__off

	def _begin_show(self):
		debug("registers_size: %d" % self.registers_size)
		debug("ins_size: %d" % self.ins_size)
		debug("outs_size: %d" % self.outs_size)
		debug("tries_size: %d" % self.tries_size)
		debug("debug_info_off: %d" % self.debug_info_off)
		debug("insns_size: %d" % self.insns_size)

		bytecode._PrintBanner()

	def show(self):
		#self._begin_show()
		self.code.show()
		#self._end_show()

	def reload(self):
		self.code.reload()

class DCode(object):
	def __init__(self, cm, offset, size, buff):
		self.CM = cm
		self.insn = buff
		self.offset = offset
		self.size = size

		self.notes = {}
		self.cached_instructions = []
		self.rcache = 0
		self.idx = 0

	def get_insn(self):
		return self.insn

	def set_insn(self, insn):
		self.insn = insn
		self.size = len(self.insn)

	def set_idx(self, idx):
		self.idx = idx

	def set_instructions(self, instructions):
		self.cached_instructions = instructions

	def get_instruction(self, idx, off=None):
		if off != None:
			idx = self.off_to_pos(off)
		return [i for i in self.get_instructions()][idx]

	def get_instructions(self):
		if self.cached_instructions:
			print self.cached_instructions
			for i in self.cached_instructions:
				yield i

		else:
			if self.rcache >= 5:
				lsa = LinearSweepAlgorithm()
				for i in lsa.get_instructions(self.CM, self.size, self.insn, self.idx):
					self.cached_instructions.append(i)

				for i in self.cached_instructions:
					yield i 
			else:
				self.rcache += 1
				if self.size >= 1000:
					self.rcache = 5

				lsa = LinearSweepAlgorithm()
				for i in lsa.get_instructions(self.CM, self.size, self.insn, self.idx):
					yield i

	def get_ins_off(self, off):
		idx = 0
		for i in self.get_instructions():
			if idx == off:
				return i 
			idx += i.get_length()
		return None
	def reload(self):
		pass

	def show(self):
		nb = 0
		idx = 0
		print "offset : ", self.offset
		for i in self.get_instructions():
			print i
			print "%-8d(%08x)" % (nb, idx)
			i.show(nb)
			print 
			idx += i.get_length()
			nb += 1

	def pretty_show(self, m_a):
		bytecode.PrettyShow(m_a, m_a.basic_blocks.gets(), self.notes)
		bytecode.PrettyShowEx(m_a.exceptions.gets())

	def add_inote(self, msg, idx, off=None):
		if off != None:
			idx = self.off_to_pos(off)

		if idx not in self.notes:
			self.notes[idx] = []

		self.notes[idx].append(msg)

	def off_to_pos(self, off):
		idx = 0
		nb = 0
		for i in self.get_instructions():
			if idx == off:
				return nb
			nb += 1
			idx += i.get_length()
		return -1

	def get_raw(self):
		return ''.join(i.get_raw() for i in self.get_instructions())

	def get_length(self):
		return len(self.get_raw())

class LinearSweepAlgorithm(object):

	def get_instructions(self, cm, size, insn, idx):
		self.odex = cm.get_odex_format()

		max_idx = size * calcsize("=H")
		if max_idx > len(insn):
			max_idx = len(insn)

		while idx < max_idx:
			obj = None
			classic_instruction = True

			op_value = unpack('=B', insn[idx])[0]

			if (op_value == 0x00 or op_value == 0xff) and ((idx + 2) < max_idx):
				op_value = unpack('=H', insn[idx:idx + 2])[0]
			
				# payload instructions ?
				if op_value in DALVIK_OPCODES_PAYLOAD:
					try:
						obj = get_instruction_payload(op_value, insn[idx:])
						classic_instruction = False
					except struct.error:
						warning("error while decoding instruction ...")

				elif op_value in dexinstructions.DALVIK_OPCODES_EXTENDED_WIDTH:
					try:
						obj = get_extented_instruction(cm, op_value, insn[idx:])
						classic_instruction = False
					except struct.error, why:
						warning("error while decoding instruction ..." + why.__str__())
            
				# optimized instructions ?
				elif self.odex and (op_value in DALVIK_OPCODES_OPTIMIZED):
					obj = get_optimized_instruction(cm, op_value, insn[idx:])
					classic_instruction = False

          	# classical instructions
			if classic_instruction:
				op_value = unpack('=B', insn[idx])[0]
				obj = get_instruction(cm, op_value, insn[idx:], self.odex)

          	# emit instruction
			yield obj
			idx = idx + obj.get_length()


class DalvikVMFormat(bytecode._Bytecode):
	def __init__(self, buff, decompiler=None, config=None):
		super(DalvikVMFormat, self).__init__(buff)

		self.config = config
		if not self.config:
			self.config = { "RECODE_ASCII_STRING": CONF["RECODE_ASCII_STRING"],
							"RECODE_ASCII_STRING_METH": CONF["RECODE_ASCII_STRING_METH"],
							"LAZY_ANALYSIS": CONF["LAZY_ANALYSIS"]}

		self.CM = ClassManager(self, self.config)
		self.CM.set_decompiler(decompiler)

		self._preload(buff)
		self._load(buff)

	def _preload(self, buff):
		pass

	def _load(self, buff):
		print "inside _load (DalvikVMFormat)"
		self.__header = HeaderItem(0, self, ClassManager(None, self.config))

		if self.__header.map_off == 0:
			bytecode.Warning("no map list ...")
		else:
			self.map_list = MapList(self.CM, self.__header.map_off, self)

			self.classes = self.map_list.get_item_type("TYPE_CLASS_DEF_ITEM")
			self.methods = self.map_list.get_item_type("TYPE_METHOD_ID_ITEM")
			self.fields = self.map_list.get_item_type("TYPE_FIELD_ID_ITEM")
			self.codes = self.map_list.get_item_type("TYPE_CODE_ITEM")
			self.strings = self.map_list.get_item_type("TYPE_STRING_DATA_ITEM")
			self.debug = self.map_list.get_item_type("TYPE_DEBUG_INFO_ITEM")
			self.header = self.map_list.get_item_type("TYPE_HEADER_ITEM")
		
		self.classes_name = None
		self.__cache_methods = None
		self.__cached_methods_idx = None

	def get_classes_def_item(self):
		return self.classes

	def get_methods_id_item(self):
		return self.methods

	def get_fields_id_item(self):
		return self.fields

	def get_codes_item(self):
		return self.codes

	def get_string_data_item(self):
		return self.stings

	def get_debug_info_item(self):
		return self.debug

	def get_header_item(self):
		return self.header

	def get_class_manager(self):
		return self.CM

	def get_format_type(self):
		return "DEX"

	def show(self):
		self.map_list.show()

	def pretty_show(self):
		self.map_list.pretty_show()
