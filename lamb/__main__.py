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

macro_table = {}

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

	def set_parent(self, parent, side):
		if (parent is not None) and (side is None):
			raise Exception("If a node has a parent, it must have a direction.")
		if (parent is None) and (side is not None):
			raise Exception("If a node has no parent, it cannot have a direction.")
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
		return self.parent_side, self.parent

	def clone(self):
		raise NotImplementedError("Nodes MUST provide a `clone` method!")

class EndNode(Node):
	def print_value(self):
		raise NotImplementedError("EndNodes MUST provide a `print_value` method!")

class ExpandableEndNode(EndNode):
	def expand(self):
		raise NotImplementedError("ExpandableEndNodes MUST provide an `expand` method!")

class FreeVar(EndNode):
	def __init__(self, name: str):
		self.name = name

	def __repr__(self):
		return f"<freevar {self.name}>"

	def print_value(self):
		return f"{self.name}"

	def clone(self):
		return FreeVar(self.name)

class Macro(ExpandableEndNode):
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

	def expand(self):
		if self.name in macro_table:
			return macro_table[self.name]
		else:
			f = FreeVar(self.name)
			f.set_parent(self.parent, self.parent_side) # type: ignore
			return f

	def clone(self):
		return Macro(self.name)

class Church(ExpandableEndNode):
	@staticmethod
	def from_parse(results):
		return Church(int(results[0]))

	def __init__(self, value: int) -> None:
		super().__init__()
		self.value = value
		self.left = None
		self.right = None

	def __repr__(self):
		return f"<church {self.value}>"

	def print_value(self):
		return str(self.value)

	def expand(self):
		f = Bound("f")
		a = Bound("a")
		chain = a

		for i in range(self.value):
			chain = Call(f, chain)

		return Func(
			f,
			Func(a, chain)
		)

	def clone(self):
		return Church(self.value)

bound_counter = 0
class Bound(EndNode):
	def __init__(self, name: str, *, forced_id = None):
		self.name = name
		global bound_counter

		if forced_id is None:
			self.identifier = bound_counter
			bound_counter += 1
		else:
			self.identifier = forced_id

	def clone(self):
		return Bound(self.name, forced_id = self.identifier)

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

	def clone(self):
		return Func(self.input, None) # type: ignore

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

	def clone(self):
		return Call(None, None)  # type: ignore

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



def clone_one(ptr, out):
	if ptr.parent_side == Direction.LEFT:
		out.left = ptr.clone()
		out.left.set_parent(out, Direction.LEFT)
	else:
		out.right = ptr.clone()
		out.right.set_parent(out, Direction.RIGHT)

def clone(expr: Node):
	if not isinstance(expr, Node):
		raise TypeError(f"I don't know what to do with a {type(expr)}")

	# Disconnect parent while cloning
	old_parent = expr.parent
	expr.parent = None

	out = expr.clone()
	out_ptr = out # Stays one step behind ptr, in the new tree.
	ptr = expr
	from_side = Direction.UP

	if isinstance(expr, EndNode):
		return out

	while True:
		if isinstance(ptr, EndNode):
			from_side, ptr = ptr.go_up()
			_, out_ptr = out_ptr.go_up()
		elif isinstance(ptr, Func):
			if from_side == Direction.UP:
				from_side, ptr = ptr.go_left()
				clone_one(ptr, out_ptr)
				_, out_ptr = out_ptr.go_left()
			elif from_side == Direction.LEFT:
				from_side, ptr = ptr.go_up()
				_, out_ptr = out_ptr.go_up()
		elif isinstance(ptr, Call):
			if from_side == Direction.UP:
				from_side, ptr = ptr.go_left()
				clone_one(ptr, out_ptr)
				_, out_ptr = out_ptr.go_left()
			elif from_side == Direction.LEFT:
				from_side, ptr = ptr.go_right()
				clone_one(ptr, out_ptr)
				_, out_ptr = out_ptr.go_right()
			elif from_side == Direction.RIGHT:
				from_side, ptr = ptr.go_up()
				_, out_ptr = out_ptr.go_up()
		if ptr is None:
			break

	expr.parent = old_parent
	return out

def print_expr(expr) -> str:

	out = ""

	# Type check
	if isinstance(expr, MacroDef):
		out = expr.label + " = "
		expr = expr.expr
	elif not isinstance(expr, Node):
		raise TypeError(f"I don't know what to do with a {type(expr)}")

	ptr = expr
	from_side = Direction.UP

	while True:
		print(ptr)
		if isinstance(ptr, EndNode):
			out += ptr.print_value()
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
				from_side, ptr = ptr.go_up()

		if ptr is None:
			break
	return out

def bind_variables(expr) -> None:

	# Type check
	if isinstance(expr, MacroDef):
		expr = expr.expr
	elif not isinstance(expr, Node):
		raise TypeError(f"I don't know what to do with a {type(expr)}")

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
					from_side, ptr = ptr.go_up()
				else:
					from_side, ptr = ptr.go_left()

			elif from_side == Direction.LEFT:
				del bound_variables[ptr.input.name]
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
				else:
					from_side, ptr = ptr.go_up()

			elif from_side == Direction.LEFT:
				if not isinstance(ptr.right, EndNode):
					from_side, ptr = ptr.go_right()
				else:
					from_side, ptr = ptr.go_up()

			elif from_side == Direction.RIGHT:
				from_side, ptr = ptr.go_up()

		if ptr is None:
			break


# Apply a function.
# Returns the function's output.
def call_func(fn: Func, arg: Node):
	ptr = fn

	# Temporarily disconnect this function's
	# parent to keep our pointer inside this
	# subtree.
	old_parent = fn.parent
	fn.parent = None

	from_side = Direction.UP

	while True:
		if isinstance(ptr, Bound):
			if ptr == fn.input:
				if ptr.parent is None:
					raise Exception("Tried to substitute a None bound variable.")

				if ptr.parent_side == Direction.LEFT:
					ptr.parent.left = clone(arg)
					ptr.parent.left.set_parent(ptr, Direction.LEFT)
				else:
					ptr.parent.right = clone(arg)
					ptr.parent.right.set_parent(ptr, Direction.RIGHT)

			from_side, ptr = ptr.go_up()

		elif isinstance(ptr, Func):
			if from_side == Direction.UP:
				from_side, ptr = ptr.go_left()
			elif from_side == Direction.LEFT:
				from_side, ptr = ptr.go_up()

		elif isinstance(ptr, Call):
			if from_side == Direction.UP:
				from_side, ptr = ptr.go_left()
			elif from_side == Direction.LEFT:
				from_side, ptr = ptr.go_right()
			elif from_side == Direction.RIGHT:
				from_side, ptr = ptr.go_up()
		else:
			from_side, ptr = ptr.go_up()

		if ptr is None:
			break

	fn.parent = old_parent
	return fn.left


# Do a single reduction step
def reduce(expr) -> tuple[bool, Node]:

	if not isinstance(expr, Node):
		raise TypeError(f"I can't reduce a {type(expr)}")

	ptr = expr
	from_side = Direction.UP
	reduced = False

	while True:
		print("redu", ptr)

		if isinstance(ptr, Call):
			if from_side == Direction.UP:
				if isinstance(ptr.left, Func):
					if ptr.parent is None:
						expr = call_func(ptr.left, ptr.right)
						expr.set_parent(None, None)
					else:
						ptr.parent.left = call_func(ptr.left, ptr.right)
						ptr.parent.left.set_parent(ptr.parent, Direction.LEFT)
					reduced = True
					break
				elif isinstance(ptr.left, ExpandableEndNode):
					ptr.left = ptr.left.expand()
					reduced = True
					break
				elif isinstance(ptr.left, Call):
					from_side, ptr = ptr.go_left()
				else:
					from_side, ptr = ptr.go_right()

			else:
				from_side, ptr = ptr.go_up()

		elif isinstance(ptr, Func):
			if from_side == Direction.UP:
				from_side, ptr = ptr.go_left()
			else:
				from_side, ptr = ptr.go_up()

		elif isinstance(ptr, EndNode):
			from_side, ptr = ptr.go_up()

		if ptr is None:
			break

	return reduced, expr


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
	"S (λfa.f a)"
]:
	n = p.parse_line(l)
	bind_variables(n)

	if isinstance(n, MacroDef):
		macro_table[n.label] = n.expr
		print(print_expr(n))
	else:
		for i in range(10):
			r, n = reduce(n)
			if not r:
				break
		print(print_expr(n))
		#print(print_expr(clone(n)))