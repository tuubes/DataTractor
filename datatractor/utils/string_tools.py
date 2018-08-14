import re


def to_camel_case(snake_str: str) -> str:
	# Converts snake_case to camelCase by capitalizing the first letter of each part except the first one
	parts = snake_str.split('_')
	return parts[0] + ''.join(x.title() for x in parts[1:])


def to_pascal_case(snake_str: str) -> str:
	# Converts snake_case to PascalCase by capitalizing the first letter of each part
	parts = snake_str.split('_')
	return ''.join(x.title() for x in parts)


def to_snake_case(s: str) -> str:
	return s.lower().replace(" ", "_")


def to_snake_varname(name: str):
	rep = {"/": "_or_", "-": "minus", "+": "plus", "type": "typ", " ": "_"}
	return multireplace(name.lower(), rep)

def to_snake_classname(name: str):
	rep = {"/": "_or_", "-": "", "+": "", " ": "_"}
	return multireplace(re.sub("\(.*?\)", "", name), rep)


def parametrize(val: str, placeholder: str, param: str) -> str:
	if param:
		return val.replace(placeholder, param)
	else:
		return val


def multireplace(string, replacements) -> str:
	"""
	<From: https://gist.github.com/bgusach/a967e0587d6e01e889fd1d776c5f3729>
	Given a string and a replacement map, it returns the replaced string.
	:param str string: string to execute replacements on
	:param dict replacements: replacement dictionary {value to find: value to replace}
	:rtype: str
	"""
	# Place longer ones first to keep shorter substrings from matching where the longer ones should take place
	# For instance given the replacements {'ab': 'AB', 'abc': 'ABC'} against the string 'hey abc', it should produce
	# 'hey ABC' and not 'hey ABc'
	substrs = sorted(replacements, key=len, reverse=True)

	# Create a big OR regex that matches any of the substrings to replace
	regexp = re.compile('|'.join(map(re.escape, substrs)))

	# For each match, look up the new string in the replacements
	return regexp.sub(lambda match: replacements[match.group(0)], string)
