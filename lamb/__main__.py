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

class TreeWalker:
	def __init__(self, expr):
		self.expr = expr
		self.ptr = expr
		self.from_side = Direction.UP

	def __next__(self):
		if self.ptr is self.expr.parent:
			raise StopIteration

		out = self.ptr
		out_side = self.from_side
		if isinstance(self.ptr, EndNode):
			self.from_side, self.ptr = self.ptr.go_up()

		elif isinstance(self.ptr, Func):
			if self.from_side == Direction.UP:
				self.from_side, self.ptr = self.ptr.go_left()
			elif self.from_side == Direction.LEFT:
				self.from_side, self.ptr = self.ptr.go_up()

		elif isinstance(self.ptr, Call):
			if self.from_side == Direction.UP:
				self.from_side, self.ptr = self.ptr.go_left()
			elif self.from_side == Direction.LEFT:
				self.from_side, self.ptr = self.ptr.go_right()
			elif self.from_side == Direction.RIGHT:
				self.from_side, self.ptr = self.ptr.go_up()

		else:
			raise TypeError(f"I don't know how to iterate a {type(self.ptr)}")

		return out_side, out

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
		self._left: Node | None = None
		self._right: Node | None = None

	def __iter__(self):
		return TreeWalker(self)

	@property
	def left(self):
		return self._left

	@left.setter
	def left(self, node):
		if node is not None:
			node.set_parent(self, Direction.LEFT)
		self._left = node

	@property
	def right(self):
		return self._right

	@right.setter
	def right(self, node):
		if node is not None:
			node.set_parent(self, Direction.RIGHT)
		self._right = node



	def set_parent(self, parent, side):
		if (parent is not None) and (side is None):
			raise Exception("If a node has a parent, it must have a direction.")
		if (parent is None) and (side is not None):
			raise Exception("If a node has no parent, it cannot have a direction.")
		self.parent = parent
		self.parent_side = side
		return self

	def go_left(self):
		if self._left is None:
			raise Exception("Can't go left when left is None")
		return Direction.UP, self._left

	def go_right(self):
		if self._right is None:
			raise Exception("Can't go right when right is None")
		return Direction.UP, self._right

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
			return clone(macro_table[self.name])
		else:
			f = FreeVar(self.name)
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
			chain = Call(clone(f), clone(chain))

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
	else:
		out.right = ptr.clone()

def clone(expr: Node):
	if not isinstance(expr, Node):
		raise TypeError(f"I don't know what to do with a {type(expr)}")

	out = expr.clone()
	out_ptr = out # Stays one step behind ptr, in the new tree.
	ptr = expr
	from_side = Direction.UP

	if isinstance(expr, EndNode):
		return out

	# We're not using a TreeWalker here because
	# we need more control over our pointer when cloning.
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

		if ptr is expr.parent:
			break
	return out

def print_expr(expr) -> str:
	# Type check
	if isinstance(expr, MacroDef):
		out = expr.label + " = "
		expr = expr.expr
	elif not isinstance(expr, Node):
		raise TypeError(f"I don't know what to do with a {type(expr)}")
	else:
		out = ""

	for s, n in expr:
		if isinstance(n, EndNode):
			out += n.print_value()

		elif isinstance(n, Func):
			if s == Direction.UP:
				if isinstance(n.parent, Func):
					out += n.input.name
				else:
					out += "λ" + n.input.name
				if not isinstance(n.left, Func):
					out += "."

		elif isinstance(n, Call):
			if s == Direction.UP:
				out += "("
			elif s == Direction.LEFT:
				out += " "
			elif s == Direction.RIGHT:
				out += ")"

	return out

def bind_variables(expr) -> None:

	# Type check
	if isinstance(expr, MacroDef):
		expr = expr.expr
	elif not isinstance(expr, Node):
		raise TypeError(f"I don't know what to do with a {type(expr)}")

	bound_variables = {}

	for s, n in expr:
		if isinstance(n, Func):
			if s == Direction.UP:
				# Add this function's input to the table of bound variables.
				# If it is already there, raise an error.
				if (n.input.name in bound_variables):
					raise ReductionError(f"Bound variable name conflict: \"{n.input.name}\"")
				else:
					bound_variables[n.input.name] = Bound(n.input.name)
					n.input = bound_variables[n.input.name]

				# If output is a macro, swap it with a bound variable.
				if isinstance(n.left, Macro):
					if n.left.name in bound_variables:
						n.left = clone(bound_variables[n.left.name])

			elif s == Direction.LEFT:
				del bound_variables[n.input.name]

		elif isinstance(n, Call):
			if s == Direction.UP:
				# Bind macros
				if isinstance(n.left, Macro):
					if n.left.name in bound_variables:
						n.left = clone(bound_variables[n.left.name])
				if isinstance(n.right, Macro):
					if n.right.name in bound_variables:
						n.right = clone(bound_variables[n.right.name])


# Apply a function.
# Returns the function's output.
def call_func(fn: Func, arg: Node):
	for s, n in fn:
		if isinstance(n, Bound):
			if n == fn.input:
				if n.parent is None:
					raise Exception("Tried to substitute a None bound variable.")

				if n.parent_side == Direction.LEFT:
					n.parent.left = clone(arg)
				else:
					n.parent.right = clone(arg)
	return fn.left


# Do a single reduction step
def reduce(expr) -> tuple[bool, Node]:

	if not isinstance(expr, Node):
		raise TypeError(f"I can't reduce a {type(expr)}")

	reduced = False

	for s, n in expr:
		if isinstance(n, Call):
			if s == Direction.UP:
				if isinstance(n.left, Func):
					if n.parent is None:
						expr = call_func(n.left, n.right)
						expr.set_parent(None, None)
					else:
						n.parent.left = call_func(n.left, n.right)
					reduced = True
					break
				elif isinstance(n.left, ExpandableEndNode):
					n.left = n.left.expand()
					reduced = True
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
	"3 NOT T"
]:
	n = p.parse_line(l)
	bind_variables(n)


	if isinstance(n, MacroDef):
		macro_table[n.label] = n.expr
		print(print_expr(n))
	else:
		for i in range(100):
			r, n = reduce(n)
			if not r:
				break
		print(print_expr(n))