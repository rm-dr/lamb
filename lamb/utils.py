from prompt_toolkit.styles import Style
from prompt_toolkit.formatted_text import HTML
from prompt_toolkit import print_formatted_text as printf
from importlib.metadata import version

import lamb.tokens as tokens


def autochurch(results):
	"""
	Makes a church numeral from an integer.
	"""

	num = int(results[0])

	f = tokens.bound_variable()
	a = tokens.bound_variable()

	chain = a

	for i in range(num):
		chain = tokens.lambda_apply(f, chain)

	return tokens.lambda_func(
		f,
		tokens.lambda_func(
			a,
			chain
		)
	)


style = Style.from_dict({
	# Basic formatting
	"text": "#FFFFFF",
	"warn": "#FFFF00",
	"err": "#FF0000",
	"prompt": "#00FFFF",

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