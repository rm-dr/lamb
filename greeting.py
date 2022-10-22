from prompt_toolkit.styles import Style
from prompt_toolkit.formatted_text import HTML, to_formatted_text
from prompt_toolkit import print_formatted_text as printf



#   |  _.._ _.|_
#   |_(_|| | ||_)
#       1.1.0
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


style = Style.from_dict({
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
})

html = HTML(f"""
<_h>    |  _.._ _.|_
    |_(_|| | ||_)</_h>
        <_v>1.1.0</_v>
        __  __
     ,-`  ``  `,
    (`   <_l>\\</_l>      )
   (`     <_l>\\</_l>     `)
   (,    <_l>/ \\</_l>    _)
    (`  <_l>/   \\</_l>   )
     `'._.--._.'

<_s> A λ calculus engine</_s>
<_p> Type :help for help</_p>

"""[1:-1])

def show():
	printf(html, style = style)