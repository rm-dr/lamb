from prompt_toolkit.styles import Style
from prompt_toolkit.formatted_text import HTML
from prompt_toolkit.lexers import Lexer
from prompt_toolkit.key_binding import KeyBindings
from prompt_toolkit import print_formatted_text as printf
from importlib.metadata import version
from prompt_toolkit.document import Document

import re


style = Style.from_dict({ # type: ignore
	# Basic formatting
	"text": "#FFFFFF",
	"warn": "#FFA700",
	"err": "#FF3809",
	"prompt": "#05CFFF",
	"ok": "#00EF7C",
	"code": "#AAAAAA italic",
	"muted": "#AAAAAA",

	# Syntax highlighting colors
	"syn_cmd": "#FFFFFF italic",
	"syn_lambda": "#AAAAAA",
	"syn_paren": "#AAAAAA",

	# Command formatting
	# cmd_h:    section titles
	# cmd_key:  keyboard keys, usually one character
	"cmd_h": "#FF3809 bold",
	"cmd_key": "#00EF7C bold",

	# Only used in greeting
	"_v": "#00EF7C bold",
	"_l": "#FF3809 bold",
	"_s": "#00EF7C bold",
	"_p": "#AAAAAA"
})


# Replace "\" with pretty "λ"s
bindings = KeyBindings()
@bindings.add("\\")
def _(event):
	event.current_buffer.insert_text("λ")

# Simple lexer for highlighting.
# Improve this later.
class LambdaLexer(Lexer):
	def lex_document(self, document):
		def inner(line_no):
			out = []
			tmp_str = []
			d = str(document.lines[line_no])

			if d.startswith(":"):
				return [
					("class:syn_cmd", d)
				]

			for c in d:
				if c in "\\λ.":
					if len(tmp_str) != 0:
						out.append(("class:text", "".join(tmp_str)))
					out.append(("class:syn_lambda", c))
					tmp_str = []
				elif c in "()":
					if len(tmp_str) != 0:
						out.append(("class:text", "".join(tmp_str)))
					out.append(("class:syn_paren", c))
					tmp_str = []
				else:
					tmp_str.append(c)

			if len(tmp_str) != 0:
				out.append(("class:text", "".join(tmp_str)))
			return out
		return inner



def lex_str(s: str) -> list[tuple[str, str]]:
	return LambdaLexer().lex_document(Document(s))(0)

def show_greeting():
	#   |  _.._ _.|_
	#   |_(_|| | ||_)
	#       0.0.0
	#
	#       __  __
	#    ,-`  ``  `,
	#   (`   \      )
	#  (`     \     `)
	#  (,    / \    _)
	#   (`  /   \   )
	#    `'._.--._.'
	#
	# A λ calculus engine

	printf(HTML("\n".join([
		"",
		"<_h>    |  _.._ _.|_",
		"    |_(_|| | ||_)</_h>",
		f"        <_v>{version('lamb_engine')}</_v>",
		"        __  __",
		"     ,-`  ``  `,",
		"    (`   <_l>\\</_l>      )",
		"   (`     <_l>\\</_l>     `)",
		"   (,    <_l>/ \\</_l>    _)",
		"    (`  <_l>/   \\</_l>   )",
		"     `'._.--._.'",
		"",
		"<_s> A λ calculus engine</_s>",
		"<_p> Type :help for help</_p>",
		""
	])), style = style)

def remove_sub(s: str):
	return re.sub("[₀₁₂₃₄₅₆₈₉]*", "", s)

def base4(n: int):
	if n == 0:
		return [0]
	digits = []
	while n:
		digits.append(n % 4)
		n //= 4
	return digits[::-1]

def subscript(num: int):

	# unicode subscripts  ₀₁₂₃ and ₄₅₆₈₉
	# usually look different,
	# so we'll use base 4.
	qb = base4(num)

	sub = {
		"0": "₀",
		"1": "₁",
		"2": "₂",
		"3": "₃",
		"4": "₄",
		"5": "₅",
		"6": "₆",
		"7": "₇",
		"8": "₈",
		"9": "₉"
	}

	sup = {
		"0": "⁰",
		"1": "¹",
		"2": "²",
		"3": "³",
		"4": "⁴",
		"5": "⁵",
		"6": "⁶",
		"7": "⁷",
		"8": "⁸",
		"9": "⁹"
	}

	return "".join(
		[sub[str(x)] for x in qb]
	)