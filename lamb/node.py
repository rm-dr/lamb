import enum

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

class Node:
	def __init__(self):
		# The node this one is connected to.
		# None if this is the top objects.
		self.parent: Node | None = None

		# What direction this is relative to the parent.
		# Left of Right.
		self.parent_side: Direction | None = None

		# Left and right nodes, None if empty
		self._left: Node | None = None
		self._right: Node | None = None

	def __iter__(self):
		return TreeWalker(self)

	def _set_parent(self, parent, side):
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
		if side == Direction.LEFT:
			self.left = node
		elif side == Direction.RIGHT:
			self.right = node
		else:
			raise TypeError("Can only set left or right side.")


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

	def __str__(self) -> str:
		return print_node(self)

	def bind_variables(self):
		return bind_variables(self)

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

	def expand(self, *, macro_table = {}):
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
			return Func(
				result[0][0],
				result[1]
			)
		else:
			return Func(
				result[0].pop(0),
				Func.from_parse(result)
			)

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

	def __init__(self, fn: Node, arg: Node) -> None:
		super().__init__()
		self.left: Node = fn
		self.right: Node = arg

	def __repr__(self):
		return f"<call {self.left!r} {self.right!r}>"

	def clone(self):
		return Call(None, None)  # type: ignore



def print_node(node: Node) -> str:
	if not isinstance(node, Node):
		raise TypeError(f"I don't know what to do with a {type(node)}")
	else:
		out = ""

	for s, n in node:
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

def clone(node: Node):
	if not isinstance(node, Node):
		raise TypeError(f"I don't know what to do with a {type(node)}")

	out = node.clone()
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
		elif isinstance(ptr, Func):
			if from_side == Direction.UP:
				from_side, ptr = ptr.go_left()
				out_ptr.set_side(ptr.parent_side, ptr.clone())
				_, out_ptr = out_ptr.go_left()
			elif from_side == Direction.LEFT:
				from_side, ptr = ptr.go_up()
				_, out_ptr = out_ptr.go_up()
		elif isinstance(ptr, Call):
			if from_side == Direction.UP:
				from_side, ptr = ptr.go_left()
				out_ptr.set_side(ptr.parent_side, ptr.clone()
)
				_, out_ptr = out_ptr.go_left()
			elif from_side == Direction.LEFT:
				from_side, ptr = ptr.go_right()
				out_ptr.set_side(ptr.parent_side, ptr.clone())
				_, out_ptr = out_ptr.go_right()
			elif from_side == Direction.RIGHT:
				from_side, ptr = ptr.go_up()
				_, out_ptr = out_ptr.go_up()

		if ptr is node.parent:
			break
	return out

def bind_variables(node: Node) -> None:

	if not isinstance(node, Node):
		raise TypeError(f"I don't know what to do with a {type(node)}")

	bound_variables = {}

	for s, n in node:
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
def reduce(node: Node, *, macro_table = {}) -> tuple[bool, Node]:

	if not isinstance(node, Node):
		raise TypeError(f"I can't reduce a {type(node)}")

	reduced = False

	out = node
	for s, n in out:
		if isinstance(n, Call):
			if s == Direction.UP:
				if isinstance(n.left, Func):
					if n.parent is None:
						out = call_func(n.left, n.right)
						out._set_parent(None, None)
					else:
						n.parent.left = call_func(n.left, n.right)
					reduced = True
					break
				elif isinstance(n.left, ExpandableEndNode):
					if isinstance(n.left, Macro):
						n.left = n.left.expand(macro_table = macro_table)
					else:
						n.left = n.left.expand()
					reduced = True
					break

	return reduced, out
