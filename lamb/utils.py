from prompt_toolkit.styles import Style
from prompt_toolkit.formatted_text import HTML
from prompt_toolkit import print_formatted_text as printf
from importlib.metadata import version


style = Style.from_dict({ # type: ignore
	# Basic formatting
	"text": "#FFFFFF",
	"warn": "#FFFF00",
	"err": "#FF0000",
	"prompt": "#00FFFF",
	"ok": "#B4EC85",
	"muted": "#AAAAAA",

	# Syntax
	"syn_macro": "#FF00FF",
	"syn_lambda": "#FF00FF",
	"syn_bound": "#FF00FF",

	# Titles for reduction results
	"result_header": "#B4EC85 bold",

	# Command formatting
	# cmd_h:    section titles
	# cmd_code: example snippets
	# cmd_text: regular text
	# cmd_key:  keyboard keys, usually one character
	"cmd_h": "#FF6600 bold",
	"cmd_code": "#AAAAAA italic",
	"cmd_text": "#FFFFFF",
	"cmd_key": "#B4EC85 bold",

	# Only used in greeting
	"_v": "#B4EC85 bold",
	"_l": "#FF6600 bold",
	"_s": "#B4EC85 bold",
	"_p": "#AAAAAA"
})


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
		f"        <_v>{version('lamb')}</_v>",
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

def subscript(num: int):
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
		[sup[x] for x in str(num)]
	)