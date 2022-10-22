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
	])), style = Style.from_dict({
		# Heading
		"_h": "#FFFFFF bold",

		# Version
		"_v": "#B4EC85 bold",

		# Lambda
		"_l": "#FF6600 bold",

		# Subtitle
		"_s": "#B4EC85 bold",

		# :help message
		"_p": "#AAAAAA"
	}))