from subprocess import call
from prompt_toolkit import PromptSession
from prompt_toolkit.completion import WordCompleter
from prompt_toolkit import print_formatted_text as printf
from prompt_toolkit.formatted_text import FormattedText
from prompt_toolkit.formatted_text import to_plain_text
from prompt_toolkit.key_binding import KeyBindings
from prompt_toolkit.lexers import Lexer

from pyparsing import exceptions as ppx
import enum

import lamb.node
import lamb.parser
import lamb.utils as utils


# Simple lexer for highlighting.
# Improve this later.
class LambdaLexer(Lexer):
	def lex_document(self, document):
		def inner(line_no):
			return [("class:text", str(document.lines[line_no]))]
		return inner


utils.show_greeting()


# Replace "\" with pretty "λ"s
bindings = KeyBindings()
@bindings.add("\\")
def _(event):
	event.current_buffer.insert_text("λ")


"""
r = runner.Runner(
	prompt_session = PromptSession(
		style = utils.style,
		lexer = LambdaLexer(),
		key_bindings = bindings
	),

	prompt_message = FormattedText([
		("class:prompt", "~~> ")
	]),
)
"""

macro_table = {}

class MacroDef:
	@staticmethod
	def from_parse(result):
		return MacroDef(
			result[0].name,
			result[1]
		)

	def __init__(self, label: str, expr: lamb.node.Node):
		self.label = label
		self.expr = expr

	def __repr__(self):
		return f"<{self.label} := {self.expr!r}>"

	def __str__(self):
		return f"{self.label} := {self.expr}"

	def bind_variables(self):
		return self.expr.bind_variables()

class Command:
	@staticmethod
	def from_parse(result):
		return Command(
			result[0],
			result[1:]
		)

	def __init__(self, name, args):
		self.name = name
		self.args = args

p = lamb.parser.LambdaParser(
	action_func = lamb.node.Func.from_parse,
	action_bound = lamb.node.Macro.from_parse,
	action_macro = lamb.node.Macro.from_parse,
	action_call = lamb.node.Call.from_parse,
	action_church = lamb.node.Church.from_parse,
	action_macro_def = MacroDef.from_parse,
	action_command = Command.from_parse
)


for l in [
	"T = λab.a",
	"F = λab.b",
	"NOT = λa.(a F T)",
	"AND = λab.(a F b)",
	"OR = λab.(a T b)",
	"XOR = λab.(a (NOT a b) b)",
	"M = λx.(x x)",
	"W = M M",
	"Y = λf.( (λx.(f (x x))) (λx.(f (x x))) )",
	"PAIR = λabi.( i a b )",
	"S = λnfa.(f (n f a))",
	"Z = λn.n (λa.F) T",
	"MULT = λnmf.n (m f)",
	"H = λp.((PAIR (p F)) (S (p F)))",
	"D = λn.n H (PAIR 0 0) T",
	"FAC = λyn.(Z n)(1)(MULT n (y (D n)))",
	"3 NOT T"
]:
	n = p.parse_line(l)
	n.bind_variables()


	if isinstance(n, MacroDef):
		macro_table[n.label] = n.expr
		print(n)
	else:
		for i in range(100):
			r, n = lamb.node.reduce(
				n,
				macro_table = macro_table
			)
			if not r:
				break
		print(n)