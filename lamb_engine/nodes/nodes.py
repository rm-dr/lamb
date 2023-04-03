import lamb_engine
import lamb_engine.nodes as lbn

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
		self.from_side = lbn.Direction.UP

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
			if self.from_side == lbn.Direction.UP:
				self.from_side, self.ptr = self.ptr.go_left()
		elif isinstance(self.ptr, EndNode):
			self.from_side, self.ptr = self.ptr.go_up()
		elif isinstance(self.ptr, Func):
			if self.from_side == lbn.Direction.UP:
				self.from_side, self.ptr = self.ptr.go_left()
			elif self.from_side == lbn.Direction.LEFT:
				self.from_side, self.ptr = self.ptr.go_up()
		elif isinstance(self.ptr, Call):
			if self.from_side == lbn.Direction.UP:
				self.from_side, self.ptr = self.ptr.go_left()
			elif self.from_side == lbn.Direction.LEFT:
				self.from_side, self.ptr = self.ptr.go_right()
			elif self.from_side == lbn.Direction.RIGHT:
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
		self._left = None
		self._right = None

		# The runner this node is attached to.
		# Set by Node.set_runner()
		self.runner: lamb_engine.runner.Runner = None # type: ignore

	def __iter__(self):
		return TreeWalker(self)

	def _set_parent(self, parent, side):
		"""
		Set this node's parent and parent side.
		This method shouldn't be called explicitly unless
		there's no other option. Use self.left and self.right instead.
		"""

		if (parent is not None) and (side is None):
			raise Exception("If a node has a parent, it must have a lbn.direction.")
		if (parent is None) and (side is not None):
			raise Exception("If a node has no parent, it cannot have a lbn.direction.")
		self.parent = parent
		self.parent_side = side
		return self

	@property
	def left(self):
		return self._left

	@left.setter
	def left(self, node):
		if node is not None:
			node._set_parent(self, lbn.Direction.LEFT)
		self._left = node

	@property
	def right(self):
		return self._right

	@right.setter
	def right(self, node):
		if node is not None:
			node._set_parent(self, lbn.Direction.RIGHT)
		self._right = node


	def set_side(self, side: lbn.Direction, node):
		"""
		A wrapper around Node.left and Node.right that
		automatically selects a side.
		"""

		if side == lbn.Direction.LEFT:
			self.left = node
		elif side == lbn.Direction.RIGHT:
			self.right = node
		else:
			raise TypeError("Can only set left or right side.")

	def get_side(self, side: lbn.Direction):
		if side == lbn.Direction.LEFT:
			return self.left
		elif side == lbn.Direction.RIGHT:
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
		return lbn.Direction.UP, self._left

	def go_right(self):
		"""
		Go down the right branch of this node.
		Returns a tuple (from_dir, node)

		from_dir is the direction from which we came INTO the next node.
		node is the node on the right of this one.
		"""
		if self._right is None:
			raise Exception("Can't go right when right is None")
		return lbn.Direction.UP, self._right

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
		return lbn.print_node(self)

	def export(self) -> str:
		"""
		Convert this tree to a parsable string.
		"""
		return lbn.print_node(self, export = True)

	def set_runner(self, runner):
		for s, n in self:
			if s == lbn.Direction.UP:
				n.runner = runner # type: ignore
		return self

class EndNode(Node):
	def print_value(self, *, export: bool = False) -> str:
		raise NotImplementedError("EndNodes MUST provide a `print_value` method!")

class ExpandableEndNode(EndNode):
	always_expand = False
	def expand(self) -> tuple[lbn.ReductionType, Node]:
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

	def expand(self) -> tuple[lbn.ReductionType, Node]:
		if self.name in self.runner.macro_table:
			# The element in the macro table will be a Root node,
			# so we clone its left element.
			return (
				lbn.ReductionType.MACRO_EXPAND,
				lbn.clone(self.runner.macro_table[self.name].left)
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

	def expand(self) -> tuple[lbn.ReductionType, Node]:
		f = Bound("f")
		a = Bound("a")
		chain = a

		for i in range(self.value):
			chain = Call(lbn.clone(f), lbn.clone(chain))

		return (
			lbn.ReductionType.AUTOCHURCH,
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

	def expand(self) -> tuple[lbn.ReductionType, Node]:
		# We shouldn't ever get here, prepare()
		# catches empty history.
		if self.runner.history[0] == None:
			raise Exception(f"Tried to expand empty history.")
		# .left is VERY important!
		# self.runner.history will contain Root nodes,
		# and we don't want those *inside* our tree.
		return lbn.ReductionType.HIST_EXPAND, lbn.clone(self.runner.history[0].left)

	def copy(self):
		return History(runner = self.runner)

bound_counter = 0
class Bound(EndNode):
	def __init__(self, name: str, *, forced_id = None, runner = None, macro_name = None):
		self.name = name
		global bound_counter
		self.runner = runner # type: ignore

		# The name of the macro this bound came from.
		# Always equal to self.name, unless the macro
		# this came from had a subscript.
		self.macro_name = macro_name

		if forced_id is None:
			self.identifier = bound_counter
			bound_counter += 1
		else:
			self.identifier = forced_id

	def copy(self):
		return Bound(
			self.name,
			forced_id = self.identifier,
			runner = self.runner
		)

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

	def __init__(self, input, output: Node, *, runner = None) -> None:
		super().__init__()
		self.input = input
		self.left: Node = output
		self.right: None = None
		self.runner = runner # type: ignore

	def __repr__(self):
		return f"<func {self.input!r} {self.left!r}>"

	def copy(self):
		return Func(
			Bound(
				self.input.name,
				runner = self.runner
			),
			None, # type: ignore
			runner = self.runner
		)

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