import enum
import lamb

class Direction(enum.Enum):
	UP		= enum.auto()
	LEFT	= enum.auto()
	RIGHT	= enum.auto()

class ReductionType(enum.Enum):
	# Nothing happened. This implies that
	# an expression cannot be reduced further.
	NOTHING			= enum.auto()

	# We replaced a macro with an expression.
	MACRO_EXPAND	= enum.auto()

	# We expanded a history reference
	HIST_EXPAND 	= enum.auto()

	# We turned a church numeral into an expression
	AUTOCHURCH		= enum.auto()

	# We applied a function.
	# This is the only type of "formal" reduction step.
	FUNCTION_APPLY	= enum.auto()

class ReductionError(Exception):
	"""
	Raised when we encounter an error while reducing.

	These should be caught and elegantly presented to the user.
	"""
	def __init__(self, msg: str):
		self.msg = msg

class TreeWalker:
	"""
	An iterator that walks the "outline" of a tree
	defined by a chain of nodes.

	It returns a tuple: (out_side, out)

	out is the node we moved to,
	out_side is the direction we came to the node from.
	"""

	def __init__(self, expr):
		self.expr = expr
		self.ptr = expr
		self.first_step = True
		self.from_side = Direction.UP

	def __iter__(self):
		return self

	def __next__(self):
		# This could be implemented without checking the node type,
		# but there's no reason to do that.
		# Maybe later?


		if self.first_step:
			self.first_step = False
			return self.from_side, self.ptr

		if isinstance(self.ptr, Root):
			if self.from_side == Direction.UP:
				self.from_side, self.ptr = self.ptr.go_left()
		elif isinstance(self.ptr, EndNode):
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

		# Stop conditions
		if isinstance(self.expr, Root):
			if self.ptr is self.expr:
				raise StopIteration
		else:
			if self.ptr is self.expr.parent:
				raise StopIteration

		return self.from_side, self.ptr

class Node:
	"""
	Generic class for an element of an expression tree.
	All nodes are subclasses of this.
	"""

	def __init__(self):
		# The node this one is connected to.
		# None if this is the top objects.
		self.parent: Node = None # type: ignore

		# What direction this is relative to the parent.
		# Left of Right.
		self.parent_side: Direction = None # type: ignore

		# Left and right nodes, None if empty
		self._left: Node | None = None
		self._right: Node | None = None

		# The runner this node is attached to.
		# Set by Node.set_runner()
		self.runner: lamb.runner.Runner = None # type: ignore

	def __iter__(self):
		return TreeWalker(self)

	def _set_parent(self, parent, side):
		"""
		Set this node's parent and parent side.
		This method shouldn't be called explicitly unless
		there's no other option. Use self.left and self.right instead.
		"""

		if (parent is not None) and (side is None):
			raise Exception("If a node has a parent, it must have a direction.")
		if (parent is None) and (side is not None):
			raise Exception("If a node has no parent, it cannot have a direction.")
		self.parent = parent
		self.parent_side = side
		return self

	@property
	def left(self):
		return self._left

	@left.setter
	def left(self, node):
		if node is not None:
			node._set_parent(self, Direction.LEFT)
		self._left = node

	@property
	def right(self):
		return self._right

	@right.setter
	def right(self, node):
		if node is not None:
			node._set_parent(self, Direction.RIGHT)
		self._right = node


	def set_side(self, side: Direction, node):
		"""
		A wrapper around Node.left and Node.right that
		automatically selects a side.
		"""

		if side == Direction.LEFT:
			self.left = node
		elif side == Direction.RIGHT:
			self.right = node
		else:
			raise TypeError("Can only set left or right side.")

	def get_side(self, side: Direction):
		if side == Direction.LEFT:
			return self.left
		elif side == Direction.RIGHT:
			return self.right
		else:
			raise TypeError("Can only get left or right side.")


	def go_left(self):
		"""
		Go down the left branch of this node.
		Returns a tuple (from_dir, node)

		from_dir is the direction from which we came INTO the next node.
		node is the node on the left of this one.
		"""

		if self._left is None:
			raise Exception("Can't go left when left is None")
		return Direction.UP, self._left

	def go_right(self):
		"""
		Go down the right branch of this node.
		Returns a tuple (from_dir, node)

		from_dir is the direction from which we came INTO the next node.
		node is the node on the right of this one.
		"""
		if self._right is None:
			raise Exception("Can't go right when right is None")
		return Direction.UP, self._right

	def go_up(self):
		"""
		Go up th the parent of this node.
		Returns a tuple (from_dir, node)

		from_dir is the direction from which we came INTO the parent.
		node is the node above of this one.
		"""
		return self.parent_side, self.parent

	def copy(self):
		"""
		Return a copy of this node.
		parent, parent_side, left, and right should be left
		as None, and will be filled later.
		"""
		raise NotImplementedError("Nodes MUST provide a `copy` method!")

	def __str__(self) -> str:
		return print_node(self)

	def export(self) -> str:
		"""
		Convert this tree to a parsable string.
		"""
		return print_node(self, export = True)

	def set_runner(self, runner):
		for s, n in self:
			if s == Direction.UP:
				n.runner = runner # type: ignore
		return self

class EndNode(Node):
	def print_value(self, *, export: bool = False) -> str:
		raise NotImplementedError("EndNodes MUST provide a `print_value` method!")

class ExpandableEndNode(EndNode):
	always_expand = False
	def expand(self) -> tuple[ReductionType, Node]:
		raise NotImplementedError("ExpandableEndNodes MUST provide an `expand` method!")

class FreeVar(EndNode):
	def __init__(self, name: str, *, runner = None):
		super().__init__()
		self.name = name
		self.runner = runner # type: ignore

	def __repr__(self):
		return f"<freevar {self.name}>"

	def print_value(self, *, export: bool = False) -> str:
		if export:
			return f"{self.name}'"
		else:
			return f"{self.name}'"

	def copy(self):
		return FreeVar(self.name)

class Macro(ExpandableEndNode):
	@staticmethod
	def from_parse(results):
		return Macro(results[0])

	def __init__(self, name: str, *, runner = None) -> None:
		super().__init__()
		self.name = name
		self.left = None
		self.right = None
		self.runner = runner # type: ignore

	def __repr__(self):
		return f"<macro {self.name}>"

	def print_value(self, *, export: bool = False) -> str:
		return self.name

	def expand(self) -> tuple[ReductionType, Node]:
		if self.name in self.runner.macro_table:
			# The element in the macro table will be a Root node,
			# so we clone its left element.
			return (
				ReductionType.MACRO_EXPAND,
				clone(self.runner.macro_table[self.name].left)
			)
		else:
			raise Exception(f"Macro {self.name} is not defined")

	def to_freevar(self):
		return FreeVar(self.name, runner = self.runner)

	def copy(self):
		return Macro(self.name, runner = self.runner)

class Church(ExpandableEndNode):
	@staticmethod
	def from_parse(results):
		return Church(int(results[0]))

	def __init__(self, value: int, *, runner = None) -> None:
		super().__init__()
		self.value = value
		self.left = None
		self.right = None
		self.runner = runner # type: ignore

	def __repr__(self):
		return f"<church {self.value}>"

	def print_value(self, *, export: bool = False) -> str:
		return str(self.value)

	def expand(self) -> tuple[ReductionType, Node]:
		f = Bound("f")
		a = Bound("a")
		chain = a

		for i in range(self.value):
			chain = Call(clone(f), clone(chain))

		return (
			ReductionType.AUTOCHURCH,
			Func(f, Func(a, chain)).set_runner(self.runner)
		)

	def copy(self):
		return Church(self.value, runner = self.runner)

class History(ExpandableEndNode):
	always_expand = True

	@staticmethod
	def from_parse(results):
		return History()

	def __init__(self, *, runner = None) -> None:
		super().__init__()
		self.left = None
		self.right = None
		self.runner = runner # type: ignore

	def __repr__(self):
		return f"<$>"

	def print_value(self, *, export: bool = False) -> str:
		return "$"

	def expand(self) -> tuple[ReductionType, Node]:
		if len(self.runner.history) == 0:
			raise ReductionError(f"There isn't any history to reference.")
		# .left is VERY important!
		# self.runner.history will contain Root nodes,
		# and we don't want those *inside* our tree.
		return ReductionType.HIST_EXPAND, clone(self.runner.history[-1].left)

	def copy(self):
		return History(runner = self.runner)

bound_counter = 0
class Bound(EndNode):
	def __init__(self, name: str, *, forced_id = None, runner = None):
		self.name = name
		global bound_counter
		self.runner = runner # type: ignore

		if forced_id is None:
			self.identifier = bound_counter
			bound_counter += 1
		else:
			self.identifier = forced_id

	def copy(self):
		return Bound(self.name, forced_id = self.identifier, runner = self.runner)

	def __eq__(self, other):
		if not isinstance(other, Bound):
			raise TypeError(f"Cannot compare bound_variable with {type(other)}")
		return self.identifier == other.identifier

	def __repr__(self):
		return f"<{self.name} {self.identifier}>"

	def print_value(self, *, export: bool = False) -> str:
		return self.name

class Func(Node):
	@staticmethod
	def from_parse(result):
		if len(result[0]) == 1:
			return Func(
				result[0][0],
				result[1]
			)
		else:
			return Func(
				result[0].pop(0),
				Func.from_parse(result)
			)

	def __init__(self, input: Macro | Bound, output: Node, *, runner = None) -> None:
		super().__init__()
		self.input: Macro | Bound = input
		self.left: Node = output
		self.right: None = None
		self.runner = runner # type: ignore

	def __repr__(self):
		return f"<func {self.input!r} {self.left!r}>"

	def copy(self):
		return Func(self.input, None, runner = self.runner) # type: ignore

class Root(Node):
	"""
	Root node.
	Used at the top of an expression.
	"""

	def __init__(self, left: Node, *, runner = None) -> None:
		super().__init__()
		self.left: Node = left
		self.runner = runner # type: ignore

	def __repr__(self):
		return f"<Root {self.left!r}>"

	def copy(self):
		return Root(None, runner = self.runner) # type: ignore

class Call(Node):
	@staticmethod
	def from_parse(results):
		if len(results) == 2:
			return Call(
				results[0],
				results[1]
			)
		else:
			this = Call(
				results[0],
				results[1]
			)

			return Call.from_parse(
				[Call(
					results[0],
					results[1]
				)] + results[2:]
			)

	def __init__(self, fn: Node, arg: Node, *, runner = None) -> None:
		super().__init__()
		self.left: Node = fn
		self.right: Node = arg
		self.runner = runner # type: ignore

	def __repr__(self):
		return f"<call {self.left!r} {self.right!r}>"

	def copy(self):
		return Call(None, None, runner = self.runner) # type: ignore


def print_node(node: Node, *, export: bool = False) -> str:
	if not isinstance(node, Node):
		raise TypeError(f"I don't know how to print a {type(node)}")

	out = ""

	bound_subs = {}

	for s, n in node:
		if isinstance(n, EndNode):
			if isinstance(n, Bound):
				if n.identifier not in bound_subs.keys():
					o = n.print_value(export = export)
					if o in bound_subs.items():
						i = 1
						while o in bound_subs.items():
							o = lamb.utils.subscript(i := i + 1)
						bound_subs[n.identifier] = o
					else:
						bound_subs[n.identifier] = n.print_value()


				out += bound_subs[n.identifier]
			else:
				out += n.print_value(export = export)

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

def clone(node: Node):
	if not isinstance(node, Node):
		raise TypeError(f"I don't know what to do with a {type(node)}")

	out = node.copy()
	out_ptr = out # Stays one step behind ptr, in the new tree.
	ptr = node
	from_side = Direction.UP

	if isinstance(node, EndNode):
		return out

	# We're not using a TreeWalker here because
	# we need more control over our pointer when cloning.
	while True:
		if isinstance(ptr, EndNode):
			from_side, ptr = ptr.go_up()
			_, out_ptr = out_ptr.go_up()
		elif isinstance(ptr, Func) or isinstance(ptr, Root):
			if from_side == Direction.UP:
				from_side, ptr = ptr.go_left()
				out_ptr.set_side(ptr.parent_side, ptr.copy())
				_, out_ptr = out_ptr.go_left()
			elif from_side == Direction.LEFT:
				from_side, ptr = ptr.go_up()
				_, out_ptr = out_ptr.go_up()
		elif isinstance(ptr, Call):
			if from_side == Direction.UP:
				from_side, ptr = ptr.go_left()
				out_ptr.set_side(ptr.parent_side, ptr.copy())
				_, out_ptr = out_ptr.go_left()
			elif from_side == Direction.LEFT:
				from_side, ptr = ptr.go_right()
				out_ptr.set_side(ptr.parent_side, ptr.copy())
				_, out_ptr = out_ptr.go_right()
			elif from_side == Direction.RIGHT:
				from_side, ptr = ptr.go_up()
				_, out_ptr = out_ptr.go_up()

		if ptr is node.parent:
			break
	return out

def prepare(root: Root, *, ban_macro_name = None) -> dict:
	"""
	Prepare an expression for expansion.
	This will does the following:
		- Binds variables
		- Turns unbound macros into free variables
		- Generates warnings
	"""

	if not isinstance(root, Root):
		raise TypeError(f"I don't know what to do with a {type(root)}")

	bound_variables = {}

	output = {
		"has_history": False,
		"free_variables": set()
	}

	it = iter(root)
	for s, n in it:
		if isinstance(n, History):
			output["has_history"] = True

		# If this expression is part of a macro,
		# make sure we don't reference it inside itself.
		elif isinstance(n, Macro):
			if (n.name == ban_macro_name) and (ban_macro_name is not None):
				raise ReductionError("Macro cannot reference self")

			# Bind variables
			if n.name in bound_variables:
				n.parent.set_side(
					n.parent_side,
					clone(bound_variables[n.name])
				)
				it.ptr = n.parent.get_side(n.parent_side)

			# Turn undefined macros into free variables
			elif n.name not in root.runner.macro_table:
				output["free_variables"].add(n.name)
				n.parent.set_side(
					n.parent_side,
					n.to_freevar()
				)
				it.ptr = n.parent.get_side(n.parent_side)


		# Save bound variables when we enter a function's sub-tree,
		# delete them when we exit it.
		elif isinstance(n, Func):
			if s == Direction.UP:
				# Add this function's input to the table of bound variables.
				# If it is already there, raise an error.
				if (n.input.name in bound_variables):
					raise ReductionError(f"Bound variable name conflict: \"{n.input.name}\"")
				else:
					bound_variables[n.input.name] = Bound(n.input.name)
					n.input = bound_variables[n.input.name]

			elif s == Direction.LEFT:
				del bound_variables[n.input.name]

	return output

# Apply a function.
# Returns the function's output.
def call_func(fn: Func, arg: Node):
	for s, n in fn:
		if isinstance(n, Bound) and (s == Direction.UP):
			if n == fn.input:
				if n.parent is None:
					raise Exception("Tried to substitute a None bound variable.")

				n.parent.set_side(n.parent_side, clone(arg)) # type: ignore
	return fn.left

# Do a single reduction step
def reduce(root: Root) -> tuple[ReductionType, Root]:
	if not isinstance(root, Root):
		raise TypeError(f"I can't reduce a {type(root)}")

	out = root
	for s, n in out:
		if isinstance(n, Call) and (s == Direction.UP):
			if isinstance(n.left, Func):
				n.parent.set_side(
					n.parent_side, # type: ignore
					call_func(n.left, n.right)
				)

				return ReductionType.FUNCTION_APPLY, out

			elif isinstance(n.left, ExpandableEndNode):
				r, n.left = n.left.expand()
				return r, out
	return ReductionType.NOTHING, out


def expand(root: Root, *, force_all = False) -> tuple[int, Root]:
	"""
	Expands expandable nodes in the given tree.

	If force_all is false, this only expands
	ExpandableEndnodes that have "always_expand" set to True.

	If force_all is True, this expands ALL
	ExpandableEndnodes.
	"""

	if not isinstance(root, Root):
		raise TypeError(f"I don't know what to do with a {type(root)}")

	out = root
	macro_expansions = 0

	it = iter(root)
	for s, n in it:
		if (
				isinstance(n, ExpandableEndNode) and
				(force_all or n.always_expand)
			):

			n.parent.set_side(
				n.parent_side, # type: ignore
				n.expand()[1]
			)
			it.ptr = n.parent.get_side(
				n.parent_side # type: ignore
			)
			macro_expansions += 1
	return macro_expansions, out