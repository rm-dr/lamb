from prompt_toolkit import PromptSession
from prompt_toolkit.completion import WordCompleter
from prompt_toolkit import print_formatted_text as printf
from prompt_toolkit.formatted_text import FormattedText
from prompt_toolkit.formatted_text import to_plain_text
from prompt_toolkit.key_binding import KeyBindings
from prompt_toolkit.lexers import Lexer

from pyparsing import exceptions as ppx

import lamb.parser
import lamb.runner as runner
import lamb.tokens as tokens
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

class Node:
	def __init__(self):
		# The node this one is connected to.
		# None if this is the top node.
		self.parent: Node | None = None

		# True if we're connected to the left side
		# of the parent, False otherwise.
		self.parent_left: bool | None = None

		# Left and right nodes, None if empty
		self.left: Node | None = None
		self.right: Node | None = None

	def set_parent(self, parent, is_left):
		self.parent = parent
		self.parent_left = is_left

	def go_left(self):
		if self.left is None:
			raise Exception("Can't go left when left is None")
		return None, self.left

	def go_right(self):
		if self.right is None:
			raise Exception("Can't go right when right is None")
		return None, self.right

	def go_up(self):
		if self.parent is None:
			raise Exception("Can't go up when parent is None")
		return self.parent_left, self.parent

def to_node(result_pair) -> Node:
	return result_pair[0].from_parse(result_pair[1])


class Macro(Node):
	@staticmethod
	def from_parse(results):
		return Macro(results[0])

	def __init__(self, name: str) -> None:
		super().__init__()
		self.name = name
		self.left = None
		self.right = None

	def __repr__(self):
		return f"<macro {self.name}>"

class Func(Node):
	@staticmethod
	def from_parse(result):
		if len(result[0]) == 1:
			i = to_node(result[0][0])
			below = to_node(result[1])
			this = Func(i, below) # type: ignore

			below.set_parent(this, True)
			return this
		else:
			i = to_node(result[0].pop(0))
			below = Func.from_parse(result)
			this = Func(i, below) # type: ignore

			below.set_parent(this, True)
			return this

	def __init__(self, input: Macro, output: Node) -> None:
		super().__init__()
		self.input = input
		self.left = output
		self.right = None

	def __repr__(self):
		return f"<func {self.input!r} {self.left!r}>"

class Call(Node):
	@staticmethod
	def from_parse(results):
		if len(results) == 2:
			left = results[0]
			if not isinstance(left, Node):
				left = to_node(left)

			right = to_node(results[1])
			this = Call(left, right)

			left.set_parent(this, True)
			right.set_parent(this, False)
			return this
		else:
			left = results[0]
			if not isinstance(left, Node):
				left = to_node(left)

			right = to_node(results[1])
			this = Call(left, right)

			left.set_parent(this, True)
			right.set_parent(this, False)
			return Call.from_parse(
				[this] + results[2:]
			)

	def __init__(self, fn: Node, arg: Node) -> None:
		super().__init__()
		self.left = fn
		self.right = arg

	def __repr__(self):
		return f"<call {self.left!r} {self.right!r}>"

p = lamb.parser.LambdaParser(
	action_func = lambda x: (Func, x),
	action_bound = lambda x: (Macro, x),
	action_macro = lambda x: (Macro, x),
	action_call = lambda x: (Call, x)
)


def traverse(node: Node):
	ptr = node
	back_from_left = None

	out = ""

	while True:
		if isinstance(ptr, Macro):
			out += ptr.name
			back_from_left, ptr = ptr.go_up()
		if isinstance(ptr, Func):
			if back_from_left is None:
				if isinstance(ptr.parent, Func):
					out += ptr.input.name
				else:
					out += "λ" + ptr.input.name
				if not isinstance(ptr.left, Func):
					out += "."
				back_from_left, ptr = ptr.go_left()
			elif back_from_left is True:
				back_from_left, ptr = ptr.go_up()
		if isinstance(ptr, Call):
			if back_from_left is None:
				out += "("
				back_from_left, ptr = ptr.go_left()
			elif back_from_left is True:
				out += " "
				back_from_left, ptr = ptr.go_right()
			elif back_from_left is False:
				out += ")"
				back_from_left, ptr = ptr.go_up()

		if ptr.parent is None:
			break
	return out

for l in [
	"λab.(a (NOT a b) b)",
	"λnmf.n (m f)",
	"λf.(λx. f(x x))(λx.f(x x))",
]:
	i = p.parse_line(l)
	#print(i)
	n = to_node(i)
	#print(n)
	print(traverse(n))

"""
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
])"""
