from prompt_toolkit import PromptSession
from prompt_toolkit.completion import WordCompleter
from prompt_toolkit import print_formatted_text as printf
from prompt_toolkit.formatted_text import FormattedText
from prompt_toolkit.formatted_text import to_plain_text
from prompt_toolkit.key_binding import KeyBindings
from prompt_toolkit.lexers import Lexer

from pyparsing import exceptions as ppx
import enum

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

class Direction(enum.Enum):
	UP		= enum.auto()
	LEFT	= enum.auto()
	RIGHT	= enum.auto()

class ReductionError(Exception):
	"""
	Raised when we encounter an error while reducing.

	These should be caught and elegantly presented to the user.
	"""
	def __init__(self, msg: str):
		self.msg = msg

class Node:
	def __init__(self):
		# The node this one is connected to.
		# None if this is the top node.
		self.parent: Node | None = None

		# What direction this is relative to the parent.
		# Left of Right.
		self.parent_side: Direction | None = None

		# Left and right nodes, None if empty
		self.left: Node | None = None
		self.right: Node | None = None

	def set_parent(self, parent, side: Direction):
		self.parent = parent
		self.parent_side = side

	def go_left(self):
		if self.left is None:
			raise Exception("Can't go left when left is None")
		return Direction.UP, self.left

	def go_right(self):
		if self.right is None:
			raise Exception("Can't go right when right is None")
		return Direction.UP, self.right

	def go_up(self):
		if self.parent is None:
			raise Exception("Can't go up when parent is None")
		return self.parent_side, self.parent

class EndNode:
	def print_value(self):
		raise NotImplementedError("EndNodes MUST have a print_value method!")

class Macro(Node, EndNode):
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

	def print_value(self):
		return self.name

class Church(Node, EndNode):
	@staticmethod
	def from_parse(results):
		return Church(results[0])

	def __init__(self, value: int) -> None:
		super().__init__()
		self.value = value
		self.left = None
		self.right = None

	def __repr__(self):
		return f"<church {self.value}>"

	def print_value(self):
		return str(self.value)

	def to_church(self):
		"""
		Return this number as an expanded church numeral.
		"""
		f = Bound("f")
		a = Bound("a")
		chain = a

		for i in range(self.value):
			chain = Call(f, chain)

		return Func(
			f,
			Func(a, chain)
		)


bound_counter = 0
class Bound(Node, EndNode):
	def __init__(self, name: str, *, forced_id = None):
		self.name = name
		global bound_counter

		if forced_id is None:
			self.identifier = bound_counter
			bound_counter += 1
		else:
			self.identifier = forced_id

	def clone(self):
		"""
		Return a new bound variable equivalent to this one.
		"""
		return Bound(
			self.name,
			forced_id = self.identifier
		)

	def __eq__(self, other):
		if not isinstance(other, Bound):
			raise TypeError(f"Cannot compare bound_variable with {type(other)}")
		return self.identifier == other.identifier

	def __repr__(self):
		return f"<{self.name} {self.identifier}>"

	def print_value(self):
		return self.name

class Func(Node):
	@staticmethod
	def from_parse(result):
		if len(result[0]) == 1:
			i = result[0][0]
			below = result[1]
			this = Func(i, below) # type: ignore

			below.set_parent(this, Direction.LEFT)
			return this
		else:
			i = result[0].pop(0)
			below = Func.from_parse(result)
			this = Func(i, below) # type: ignore

			below.set_parent(this, Direction.LEFT)
			return this

	def __init__(self, input: Macro | Bound, output: Node) -> None:
		super().__init__()
		self.input: Macro | Bound = input
		self.left: Node = output
		self.right: None = None

	def __repr__(self):
		return f"<func {self.input!r} {self.left!r}>"

class Call(Node):
	@staticmethod
	def from_parse(results):
		if len(results) == 2:
			left = results[0]
			right = results[1]
			this = Call(left, right)

			left.set_parent(this, Direction.LEFT)
			right.set_parent(this, Direction.RIGHT)
			return this
		else:
			left = results[0]
			right = results[1]
			this = Call(left, right)

			left.set_parent(this, Direction.LEFT)
			right.set_parent(this, Direction.RIGHT)
			return Call.from_parse(
				[this] + results[2:]
			)

	def __init__(self, fn: Node, arg: Node) -> None:
		super().__init__()
		self.left: Node = fn
		self.right: Node = arg

	def __repr__(self):
		return f"<call {self.left!r} {self.right!r}>"

class MacroDef:
	@staticmethod
	def from_parse(result):
		return MacroDef(
			result[0].name,
			result[1]
		)

	def __init__(self, label: str, expr: Node):
		self.label = label
		self.expr = expr

	def __repr__(self):
		return f"<{self.label} := {self.expr!r}>"

	def __str__(self):
		return f"{self.label} := {self.expr}"

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
	action_func = Func.from_parse,
	action_bound = Macro.from_parse,
	action_macro = Macro.from_parse,
	action_call = Call.from_parse,
	action_church = Church.from_parse,
	action_macro_def = MacroDef.from_parse,
	action_command = Command.from_parse
)


def print_expr(expr) -> str:

	if isinstance(expr, MacroDef):
		return f"{expr.label} = {print_expr(expr.expr)}"

	elif isinstance(expr, Node):
		ptr = expr
		from_side = Direction.UP

		out = ""

		while True:
			if isinstance(ptr, EndNode):
				out += ptr.print_value()
				if ptr.parent is not None:
						from_side, ptr = ptr.go_up()

			elif isinstance(ptr, Func):
				if from_side == Direction.UP:
					if isinstance(ptr.parent, Func):
						out += ptr.input.name
					else:
						out += "λ" + ptr.input.name
					if not isinstance(ptr.left, Func):
						out += "."
					from_side, ptr = ptr.go_left()
				elif from_side == Direction.LEFT:
					if ptr.parent is not None:
						from_side, ptr = ptr.go_up()

			elif isinstance(ptr, Call):
				if from_side == Direction.UP:
					out += "("
					from_side, ptr = ptr.go_left()
				elif from_side == Direction.LEFT:
					out += " "
					from_side, ptr = ptr.go_right()
				elif from_side == Direction.RIGHT:
					out += ")"
					if ptr.parent is not None:
						from_side, ptr = ptr.go_up()

			if ptr.parent is None:
				break
		return out

	else:
		raise TypeError(f"I don't know what to do with a {type(expr)}")

def bind_variables(expr) -> None:

	if isinstance(expr, MacroDef):
		bind_variables(expr.expr)

	elif isinstance(expr, Node):
		ptr = expr
		from_side = Direction.UP

		bound_variables = {}

		while True:
			if isinstance(ptr, Func):
				if from_side == Direction.UP:
					# Add this function's input to the table of bound variables.
					# If it is already there, raise an error.
					if (ptr.input.name in bound_variables):
						raise ReductionError(f"Bound variable name conflict: \"{ptr.input.name}\"")
					else:
						bound_variables[ptr.input.name] = Bound(ptr.input.name)
						ptr.input = bound_variables[ptr.input.name]

					# If output is a macro, swap it with a bound variable.
					if isinstance(ptr.left, Macro):
						if ptr.left.name in bound_variables:
							ptr.left = bound_variables[ptr.left.name].clone()
							ptr.left.set_parent(ptr, Direction.LEFT)

					# If we can't move down the tree, move up.
					if isinstance(ptr.left, EndNode):
						del bound_variables[ptr.input.name]
						if ptr.parent is not None:
							from_side, ptr = ptr.go_up()
					else:
						from_side, ptr = ptr.go_left()

				elif from_side == Direction.LEFT:
					del bound_variables[ptr.input.name]
					if ptr.parent is not None:
						from_side, ptr = ptr.go_up()

			elif isinstance(ptr, Call):
				if from_side == Direction.UP:
					# Bind macros
					if isinstance(ptr.left, Macro):
						if ptr.left.name in bound_variables:
							ptr.left = bound_variables[ptr.left.name].clone()
							ptr.left.set_parent(ptr, Direction.LEFT)
					if isinstance(ptr.right, Macro):
						if ptr.right.name in bound_variables:
							ptr.right = bound_variables[ptr.right.name].clone()
							ptr.right.set_parent(ptr, Direction.RIGHT)

					if not isinstance(ptr.left, EndNode):
						from_side, ptr = ptr.go_left()
					elif not isinstance(ptr.right, EndNode):
						from_side, ptr = ptr.go_right()
					elif ptr.parent is not None:
						from_side, ptr = ptr.go_up()

				elif from_side == Direction.LEFT:
					if isinstance(ptr.right, Macro):
						if ptr.right.name in bound_variables:
							ptr.right = bound_variables[ptr.right.name].clone()
							ptr.right.set_parent(ptr, Direction.RIGHT)

					if not isinstance(ptr.right, EndNode):
						from_side, ptr = ptr.go_right()
					elif ptr.parent is not None:
						from_side, ptr = ptr.go_up()

				elif from_side == Direction.RIGHT:
					if ptr.parent is not None:
						from_side, ptr = ptr.go_up()

			if ptr.parent is None:
				break

	else:
		raise TypeError(f"I don't know what to do with a {type(expr)}")

for l in [
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
	"H = λp.((PAIR (p F)) (S (p F)))"
]:
	n = p.parse_line(l)
	bind_variables(n)
	print(print_expr(n))