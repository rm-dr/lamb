import lamb_engine
import lamb_engine.nodes as lbn

def print_node(node: lbn.Node, *, export: bool = False) -> str:
	if not isinstance(node, lbn.Node):
		raise TypeError(f"I don't know how to print a {type(node)}")

	out = ""

	bound_subs = {}

	for s, n in node:
		if isinstance(n, lbn.EndNode):
			if isinstance(n, lbn.Bound):
				out += bound_subs[n.identifier]
			else:
				out += n.print_value(export = export)

		elif isinstance(n, lbn.Func):
			# This should never be true, but
			# keep this here to silence type checker.
			if not isinstance(n.input, lbn.Bound):
				raise Exception("input is macro, something is wrong.")

			if s == lbn.Direction.UP:
				o = n.input.print_value(export = export)
				if o in bound_subs.values():
					i = -1
					p = o
					while o in bound_subs.values():
						o = p + lamb_engine.utils.subscript(i := i + 1)
					bound_subs[n.input.identifier] = o
				else:
					bound_subs[n.input.identifier] = n.input.print_value()

				if isinstance(n.parent, lbn.Call):
					out += "("

				if isinstance(n.parent, lbn.Func):
					out += bound_subs[n.input.identifier]
				else:
					out += "λ" + bound_subs[n.input.identifier]
				if not isinstance(n.left, lbn.Func):
					out += "."

			elif s == lbn.Direction.LEFT:
				if isinstance(n.parent, lbn.Call):
					out += ")"
				del bound_subs[n.input.identifier]

		elif isinstance(n, lbn.Call):
			if s == lbn.Direction.UP:
				out += "("
			elif s == lbn.Direction.LEFT:
				out += " "
			elif s == lbn.Direction.RIGHT:
				out += ")"

	return out


def clone(node: lbn.Node):
	if not isinstance(node, lbn.Node):
		raise TypeError(f"I don't know what to do with a {type(node)}")

	macro_map = {}
	if isinstance(node, lbn.Func):
		c = node.copy()
		macro_map[node.input.identifier] = c.input.identifier # type: ignore
	else:
		c = node.copy()

	out = c
	out_ptr = out # Stays one step behind ptr, in the new tree.
	ptr = node
	from_side = lbn.Direction.UP


	if isinstance(node, lbn.EndNode):
		return out

	# We're not using a TreeWalker here because
	# we need more control over our pointer when cloning.
	while True:
		if isinstance(ptr, lbn.EndNode):
			from_side, ptr = ptr.go_up()
			_, out_ptr = out_ptr.go_up()
		elif isinstance(ptr, lbn.Func) or isinstance(ptr, lbn.Root):
			if from_side == lbn.Direction.UP:
				from_side, ptr = ptr.go_left()

				if isinstance(ptr, lbn.Func):
					c = ptr.copy()
					macro_map[ptr.input.identifier] = c.input.identifier # type: ignore
				elif isinstance(ptr, lbn.Bound):
					c = ptr.copy()
					if c.identifier in macro_map:
						c.identifier = macro_map[c.identifier]
				else:
					c = ptr.copy()
				out_ptr.set_side(ptr.parent_side, c)

				_, out_ptr = out_ptr.go_left()
			elif from_side == lbn.Direction.LEFT:
				from_side, ptr = ptr.go_up()
				_, out_ptr = out_ptr.go_up()
		elif isinstance(ptr, lbn.Call):
			if from_side == lbn.Direction.UP:
				from_side, ptr = ptr.go_left()

				if isinstance(ptr, lbn.Func):
					c = ptr.copy()
					macro_map[ptr.input.identifier] = c.input.identifier # type: ignore
				elif isinstance(ptr, lbn.Bound):
					c = ptr.copy()
					if c.identifier in macro_map:
						c.identifier = macro_map[c.identifier]
				else:
					c = ptr.copy()
				out_ptr.set_side(ptr.parent_side, c)

				_, out_ptr = out_ptr.go_left()
			elif from_side == lbn.Direction.LEFT:
				from_side, ptr = ptr.go_right()

				if isinstance(ptr, lbn.Func):
					c = ptr.copy()
					macro_map[ptr.input.identifier] = c.input.identifier # type: ignore
				elif isinstance(ptr, lbn.Bound):
					c = ptr.copy()
					if c.identifier in macro_map:
						c.identifier = macro_map[c.identifier]
				else:
					c = ptr.copy()
				out_ptr.set_side(ptr.parent_side, c)

				_, out_ptr = out_ptr.go_right()
			elif from_side == lbn.Direction.RIGHT:
				from_side, ptr = ptr.go_up()
				_, out_ptr = out_ptr.go_up()

		if ptr is node.parent:
			break
	return out

def prepare(root: lbn.Root, *, ban_macro_name = None) -> list:
	"""
	Prepare an expression for expansion.
	This will does the following:
		- Binds variables
		- Turns unbound macros into free variables
		- Generates warnings
	"""

	if not isinstance(root, lbn.Root):
		raise TypeError(f"I don't know what to do with a {type(root)}")

	bound_variables = {}

	warnings = []

	it = iter(root)
	for s, n in it:
		if isinstance(n, lbn.History):
			if root.runner.history[0] == None:
				raise lbn.ReductionError("There isn't any history to reference.")
			else:
				warnings += [
					("class:code", "$"),
					("class:warn", " will be expanded to ")
				] + lamb_engine.utils.lex_str(str(n.expand()[1]))

		# If this expression is part of a macro,
		# make sure we don't reference it inside itself.
		elif isinstance(n, lbn.Macro):
			if (n.name == ban_macro_name) and (ban_macro_name is not None):
				raise lbn.ReductionError("Macro cannot reference self")

			# Bind variables
			if n.name in bound_variables:
				n.parent.set_side(
					n.parent_side,
					clone(bound_variables[n.name])
				)
				it.ptr = n.parent.get_side(n.parent_side)

			# Turn undefined macros into free variables
			elif n.name not in root.runner.macro_table:
				warnings += [
					("class:warn", "Name "),
					("class:code", n.name),
					("class:warn", " is a free variable\n"),
				]
				n.parent.set_side(
					n.parent_side,
					n.to_freevar()
				)
				it.ptr = n.parent.get_side(n.parent_side)


		# Save bound variables when we enter a function's sub-tree,
		# delete them when we exit it.
		elif isinstance(n, lbn.Func):
			if s == lbn.Direction.UP:
				# Add this function's input to the table of bound variables.
				# If it is already there, raise an error.
				if (n.input.name in bound_variables):
					raise lbn.ReductionError(f"Bound variable name conflict: \"{n.input.name}\"")
				else:
					bound_variables[n.input.name] = lbn.Bound(
						lamb_engine.utils.remove_sub(n.input.name),
						macro_name = n.input.name
					)
					n.input = bound_variables[n.input.name]

			elif s == lbn.Direction.LEFT:
				del bound_variables[n.input.macro_name] # type: ignore

	return warnings

# Apply a function.
# Returns the function's output.
def call_func(fn: lbn.Func, arg: lbn.Node):
	for s, n in fn:
		if isinstance(n, lbn.Bound) and (s == lbn.Direction.UP):
			if n == fn.input:
				if n.parent is None:
					raise Exception("Tried to substitute a None bound variable.")

				n.parent.set_side(n.parent_side, clone(arg)) # type: ignore
	return fn.left

# Do a single reduction step
def reduce(root: lbn.Root) -> tuple[lbn.ReductionType, lbn.Root]:
	if not isinstance(root, lbn.Root):
		raise TypeError(f"I can't reduce a {type(root)}")

	out = root
	for s, n in out:
		if isinstance(n, lbn.Call) and (s == lbn.Direction.UP):
			if isinstance(n.left, lbn.Func):
				n.parent.set_side(
					n.parent_side, # type: ignore
					call_func(n.left, n.right)
				)

				return lbn.ReductionType.FUNCTION_APPLY, out

			elif isinstance(n.left, lbn.ExpandableEndNode):
				r, n.left = n.left.expand()
				return r, out
	return lbn.ReductionType.NOTHING, out


def expand(root: lbn.Root, *, force_all = False) -> tuple[int, lbn.Root]:
	"""
	Expands expandable nodes in the given tree.

	If force_all is false, this only expands
	ExpandableEndnodes that have "always_expand" set to True.

	If force_all is True, this expands ALL
	ExpandableEndnodes.
	"""

	if not isinstance(root, lbn.Root):
		raise TypeError(f"I don't know what to do with a {type(root)}")

	out = root
	macro_expansions = 0

	it = iter(root)
	for s, n in it:
		if (
				isinstance(n, lbn.ExpandableEndNode) and
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