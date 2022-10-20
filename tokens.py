from typing import Type


class free_variable:
	"""
	Represents a free variable.

	This object does not reduce to
	anything, since it has no meaning.

	Any name in an expression that isn't
	a macro or a bound variable is assumed
	to be a free variable.
	"""

	def __init__(self, label: str):
		self.label = label

	def __repr__(self):
		return f"<freevar {self.label}>"

	def __str__(self):
		return f"{self.label}"


class macro:
	"""
	Represents a "macro" in lambda calculus,
	a variable that expands to an expression.

	These don't have inherent logic, they
	just make writing and reading expressions
	easier.

	These are defined as follows:
	<macro name> = <expression>
	"""

	@staticmethod
	def from_parse(result):
		return macro(
			result[0],
		)

	def __init__(self, name):
		self.name = name
	def __repr__(self):
		return f"<{self.name}>"
	def __str__(self):
		return self.name

	def __eq__(self, other):
		if not isinstance(other, macro):
			raise TypeError("Can only compare macro with macro")
		return self.name == other.name

	def expand(self, macro_table = {}, *, auto_free_vars = True):
		if self.name in macro_table:
			return macro_table[self.name]
		elif not auto_free_vars:
			raise NameError(f"Name {self.name} is not defined!")
		else:
			return free_variable(self.name)


class macro_expression:
	"""
	Represents a line that looks like
		<name> = <expression>

	Doesn't do anything particularly interesting,
	just holds an expression until it is stored
	in the runner's macro table.
	"""

	@staticmethod
	def from_parse(result):
		return macro_expression(
			result[0].name,
			result[1]
		)

	def __init__(self, label, exp):
		self.label = label
		self.exp = exp

	def __repr__(self):
		return f"<{self.label} := {self.exp!r}>"

	def __str__(self):
		return f"{self.label} := {self.exp}"





bound_variable_counter = 0
class bound_variable:
	def __init__(self, forced_id = None):
		global bound_variable_counter

		if forced_id is None:
			self.identifier = bound_variable_counter
			bound_variable_counter += 1
		else:
			self.identifier = forced_id

	def __eq__(self, other):
		if not isinstance(other, bound_variable):
			raise TypeError(f"Cannot compare bound_variable with {type(other)}")
		return self.identifier == other.identifier

	def __repr__(self):
		return f"<in {self.identifier}>"

class lambda_func:
	"""
	Represents a function.
		Defined like λa.aa

	After being created by the parser, a function
	needs to have its variables bound. This cannot
	happen during parsing, since the parser creates
	functions "inside-out," and we need all inner
	functions before we bind variables.
	"""

	@staticmethod
	def from_parse(result):
		return lambda_func(
			result[0],
			result[1]
		)

	def __init__(self, input_var, output):
		self.input = input_var
		self.output = output

	def __repr__(self) -> str:
		return f"<{self.input!r} → {self.output!r}>"

	def __str__(self) -> str:
		return f"λ{self.input}.{self.output}"


	def bind_variables(
			self,
			placeholder: macro | None = None,
			val: bound_variable | None = None,
			*,
			binding_self: bool = False
		) -> None:
		"""
		Go through this function and all the functions inside it,
		and replace the strings generated by the parser with bound
		variables or free variables.

		If values are passed to `placeholder` and `val,`
		we're binding the variable of a function containing
		this one. If they are both none, start the binding
		chain with this function.

		If only one of those arguments is None, something is very wrong.

		`placeholder` is a macro, NOT A STRING!
		The parser assumes all names are macros at first, variable
		binding fixes those that are actually bound variables.

		If `binding_self` is True, don't throw an error on a name conflict
		and don't bind this function's input variable.
		This is used when we're calling this method to bind this function's
		variable.
		"""


		if (placeholder is None) and (val != placeholder):
			raise Exception(
				"Error while binding variables: placeholder and val are both None."
			)

		# We only need to check for collisions if we're
		# binding another function's variable. If this
		# function starts the bind chain, skip that step.
		if not ((placeholder is None) and (val is None)):
			if not binding_self and isinstance(self.input, macro):
				if self.input == placeholder:
					raise NameError("Bound variable name conflict.")

		# If this function's variables haven't been bound yet,
		# bind them BEFORE binding the outer function's.
		#
		# If we bind inner functions' variables before outer
		# functions' variables, we won't be able to detect
		# name conflicts.
		if isinstance(self.input, macro) and not binding_self:
			new_bound_var = bound_variable()
			self.bind_variables(
				self.input,
				new_bound_var,
				binding_self = True
			)
			self.input = new_bound_var


		# Bind variables inside this function.
		if isinstance(self.output, macro):
			if self.output == placeholder:
				self.output = val
		elif isinstance(self.output, lambda_func):
			self.output.bind_variables(placeholder, val)
		elif isinstance(self.output, lambda_apply):
			self.output.bind_variables(placeholder, val)

	# Expand this function's output.
	# For functions, this isn't done unless
	# its explicitly asked for.
	def expand(self, macro_table = {}):
		new_out = self.output
		if isinstance(self.output, macro):
			new_out = self.output.expand(macro_table)

			# If the macro becomes a free variable, expand again.
			if isinstance(new_out, free_variable):
				lambda_func(
					self.input,
					new_out
				).expand(macro_table)

		elif isinstance(self.output, lambda_func):
			new_out = self.output.expand(macro_table)
		elif isinstance(self.output, lambda_apply):
			new_out = self.output.expand(macro_table)
		return lambda_func(
			self.input,
			new_out
		)

	def apply(
			self,
			val,
			*,
			bound_var: bound_variable | None = None
		):
		"""
		Substitute `bound_var` into all instances of a bound variable `var`.
		If `bound_var` is none, use this functions bound variable.
		Returns a new object.
		"""

		calling_self = False
		if bound_var is None:
			calling_self = True
			bound_var = self.input
		new_out = self.output
		if isinstance(self.output, bound_variable):
			if self.output == bound_var:
				new_out = val
		elif isinstance(self.output, lambda_func):
			new_out = self.output.apply(val, bound_var = bound_var)
		elif isinstance(self.output, lambda_apply):
			new_out = self.output.sub_bound_var(val, bound_var = bound_var)
		else:
			raise TypeError("Cannot apply a function to {self.output!r}")

		# If we're applying THIS function,
		# just give the output
		if calling_self:
			return new_out

		# If we're applying another function,
		# return this one with substitutions
		else:
			return lambda_func(
				self.input,
				new_out
			)


class lambda_apply:
	"""
	Represents a function application.
	Has two elements: fn, the function,
	and arg, the thing it acts upon.

	Parentheses are handled by the parser, and
	chained functions are handled by from_parse.
	"""

	@staticmethod
	def from_parse(result):
		if len(result) == 2:
			return lambda_apply(
				result[0],
				result[1]
			)
		elif len(result) > 2:
			return lambda_apply.from_parse([
				lambda_apply(
					result[0],
					result[1]
				)] + result[2:]
			)

	def __init__(
			self,
			fn,
			arg
		):
		self.fn = fn
		self.arg = arg

	def __repr__(self) -> str:
		return f"<{self.fn!r} | {self.arg!r}>"

	def __str__(self) -> str:
		return f"({self.fn} {self.arg})"

	def bind_variables(
			self,
			placeholder: macro | None = None,
			val: bound_variable | None = None
		) -> None:
		"""
		Does exactly what lambda_func.bind_variables does,
		but acts on applications instead.

		There will be little documentation in this method,
		see lambda_func.bind_variables.
		"""

		if (placeholder is None) and (val != placeholder):
			raise Exception(
				"Error while binding variables: placeholder and val are both None."
			)

		# If val and placeholder are None,
		# everything below should still work as expected.
		if isinstance(self.fn, macro) and placeholder is not None:
			if self.fn == placeholder:
				self.fn = val
		elif isinstance(self.fn, lambda_func):
			self.fn.bind_variables(placeholder, val)
		elif isinstance(self.fn, lambda_apply):
			self.fn.bind_variables(placeholder, val)

		if isinstance(self.arg, macro) and placeholder is not None:
			if self.arg == placeholder:
				self.arg = val
		elif isinstance(self.arg, lambda_func):
			self.arg.bind_variables(placeholder, val)
		elif isinstance(self.arg, lambda_apply):
			self.arg.bind_variables(placeholder, val)

	def sub_bound_var(
		self,
		val,
		*,
		bound_var: bound_variable
	):

		new_fn = self.fn
		if isinstance(self.fn, bound_variable):
			if self.fn == bound_var:
				new_fn = val
		elif isinstance(self.fn, lambda_func):
			new_fn = self.fn.apply(val, bound_var = bound_var)
		elif isinstance(self.fn, lambda_apply):
			new_fn = self.fn.sub_bound_var(val, bound_var = bound_var)

		new_arg = self.arg
		if isinstance(self.arg, bound_variable):
			if self.arg == bound_var:
				new_arg = val
		elif isinstance(self.arg, lambda_func):
			new_arg = self.arg.apply(val, bound_var = bound_var)
		elif isinstance(self.arg, lambda_apply):
			new_arg = self.arg.sub_bound_var(val, bound_var = bound_var)

		return lambda_apply(
			new_fn,
			new_arg
		)

	def expand(self, macro_table = {}):
		# If fn is a function, apply it.
		if isinstance(self.fn, lambda_func):
			return self.fn.apply(self.arg)
		# If fn is an application or macro, expand it.
		elif isinstance(self.fn, macro):
			f = lambda_apply(
				m := self.fn.expand(macro_table),
				self.arg
			)

			# If a macro becomes a free variable,
			# expand twice.
			if isinstance(m, free_variable):
				return f.expand(macro_table)
			else:
				return f

		elif isinstance(self.fn, lambda_apply):
			return lambda_apply(
				self.fn.expand(macro_table),
				self.arg
			)

		# If we get to this point, the function we're applying
		# can't be expanded. That means it's a free or bound
		# variable. If that happens, expand the arg instead.
		elif (
			isinstance(self.arg, lambda_apply) or
			isinstance(self.arg, lambda_func)
		):
			return lambda_apply(
				self.fn,
				self.arg.expand(macro_table)
			)

		return self