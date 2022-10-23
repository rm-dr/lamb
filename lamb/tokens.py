import enum
import lamb.utils as utils

class ReductionError(Exception):
	"""
	Raised when we encounter an error while reducing.

	These should be caught and elegantly presented to the user.
	"""
	def __init__(self, msg: str):
		self.msg = msg

class ReductionType(enum.Enum):
	MACRO_EXPAND	= enum.auto()
	MACRO_TO_FREE	= enum.auto()
	FUNCTION_APPLY	= enum.auto()
	AUTOCHURCH		= enum.auto()


class ReductionStatus:
	"""
	This object helps organize reduction output.
	An instance is returned after every reduction step.
	"""

	def __init__(
		self,
		*,
		output,
		was_reduced: bool,
		reduction_type: ReductionType | None = None
	):
		# The new expression
		self.output = output

		# What did we do?
		# Will be None if was_reduced is false.
		self.reduction_type = reduction_type

		# Did this reduction change anything?
		# If we try to reduce an irreducible expression,
		# this will be false.
		self.was_reduced = was_reduced

class LambdaToken:
	"""
	Base class for all lambda tokens.
	"""

	def set_runner(self, runner):
		self.runner = runner

	def bind_variables(self, *, ban_macro_name: str | None = None) -> None:
		pass

	def reduce(self) -> ReductionStatus:
		return ReductionStatus(
			was_reduced = False,
			output = self
		)

class church_num(LambdaToken):
	"""
	Represents a Church numeral.
	"""
	@staticmethod
	def from_parse(result):
		return church_num(
			int(result[0]),
		)

	def __init__(self, val):
		self.val = val
	def __repr__(self):
		return f"<{self.val}>"
	def __str__(self):
		return f"{self.val}"

	def to_church(self):
		"""
		Return this number as an expanded church numeral.
		"""
		f = bound_variable("f", runner = self.runner)
		a = bound_variable("a", runner = self.runner)
		chain = a

		for i in range(self.val):
			chain = lambda_apply(f, chain)

		return lambda_func(
			f,
			lambda_func(a, chain)
		)

	def reduce(self, *, force_substitute = False) -> ReductionStatus:
		if force_substitute: # Only expand macros if we NEED to
			return ReductionStatus(
				output = self.to_church(),
				was_reduced = True,
				reduction_type = ReductionType.AUTOCHURCH
			)
		else: # Otherwise, do nothing.
			return ReductionStatus(
				output = self,
				was_reduced = False
			)


class free_variable(LambdaToken):
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

class command(LambdaToken):
	@staticmethod
	def from_parse(result):
		return command(
			result[0],
			result[1:]
		)

	def __init__(self, name, args):
		self.name = name
		self.args = args

class macro(LambdaToken):
	"""
	Represents a "macro" in lambda calculus,
	a variable that reduces to an expression.

	These don't have any inherent logic, they
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

	def bind_variables(self, *, ban_macro_name=None) -> None:
		if self.name == ban_macro_name:
			raise ReductionError(f"Cannot use macro \"{ban_macro_name}\" here.")

	def reduce(
			self,
			*,
			# To keep output readable, we avoid expanding macros as often as possible.
			# Macros are irreducible if force_substitute is false.
			force_substitute = False,

			# If this is false, error when macros aren't defined instead of
			# invisibly making a free variable.
			auto_free_vars = True
		) -> ReductionStatus:

		if (self.name in self.runner.macro_table) and force_substitute:
			if force_substitute: # Only expand macros if we NEED to
				return ReductionStatus(
					output = self.runner.macro_table[self.name],
					reduction_type = ReductionType.MACRO_EXPAND,
					was_reduced = True
				)
			else: # Otherwise, do nothing.
				return ReductionStatus(
					output = self,
					was_reduced = False
				)

		elif not auto_free_vars:
			raise ReductionError(f"Macro {self.name} is not defined")

		else:
			return ReductionStatus(
				output = free_variable(self.name),
				reduction_type = ReductionType.MACRO_TO_FREE,
				was_reduced = True
			)

class macro_expression(LambdaToken):
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

	def set_runner(self, runner):
		self.expr.set_runner(runner)

	def bind_variables(self, *, ban_macro_name: str | None = None):
		self.expr.bind_variables(ban_macro_name = ban_macro_name)

	def __init__(self, label: str, expr: LambdaToken):
		self.label = label
		self.expr = expr

	def __repr__(self):
		return f"<{self.label} := {self.expr!r}>"

	def __str__(self):
		return f"{self.label} := {self.expr}"


class bound_variable(LambdaToken):
	def __init__(self, name: str, *, runner, forced_id = None):
		self.original_name = name
		self.runner = runner

		if forced_id is None:
			self.identifier = self.runner.bound_variable_counter
			self.runner.bound_variable_counter += 1
		else:
			self.identifier = forced_id

	def __eq__(self, other):
		if not isinstance(other, bound_variable):
			raise TypeError(f"Cannot compare bound_variable with {type(other)}")
		return self.identifier == other.identifier

	def __repr__(self):
		return f"<{self.original_name} {self.identifier}>"

	def __str__(self):
		return self.original_name

class lambda_func(LambdaToken):
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
		if len(result[0]) == 1:
			return lambda_func(
				result[0][0],
				result[1]
			)
		else:
			return lambda_func(
				result[0].pop(0),
				lambda_func.from_parse(result)
			)

	def set_runner(self, runner):
		self.runner = runner
		self.input.set_runner(runner)
		self.output.set_runner(runner)

	def __init__(
			self,
			input_var: macro | bound_variable,
			output: LambdaToken
		):
		self.input: macro | bound_variable = input_var
		self.output: LambdaToken = output

	def __repr__(self) -> str:
		return f"<{self.input!r} → {self.output!r}>"

	def __str__(self) -> str:
		return f"λ{self.input}.{self.output}"

	def bind_variables(
			self,
			placeholder: macro | None = None,
			val: bound_variable | None = None,
			*,
			binding_self: bool = False,
			ban_macro_name: str | None = None
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
		if placeholder is not None:
			if not binding_self and isinstance(self.input, macro):
				if self.input == placeholder:
					raise ReductionError(f"Bound variable name conflict: \"{self.input.name}\"")

				if self.input.name in self.runner.macro_table:
					raise ReductionError(f"Bound variable name conflict: \"{self.input.name}\" is a macro")


		# If this function's variables haven't been bound yet,
		# bind them BEFORE binding the outer function's.
		#
		# If we bind inner functions' variables before outer
		# functions' variables, we won't be able to detect
		# name conflicts.
		if isinstance(self.input, macro) and not binding_self:
			new_bound_var = bound_variable(
				self.input.name,
				runner = self.runner
			)
			self.bind_variables(
				self.input,
				new_bound_var,
				binding_self = True,
				ban_macro_name = ban_macro_name
			)
			self.input = new_bound_var


		# Bind variables inside this function.
		if isinstance(self.output, macro) and placeholder is not None:
			if self.output.name == ban_macro_name:
				raise ReductionError(f"Cannot use macro \"{ban_macro_name}\" here.")
			if self.output == placeholder:
				self.output = val # type: ignore
		elif isinstance(self.output, lambda_func):
			self.output.bind_variables(placeholder, val, ban_macro_name = ban_macro_name)
		elif isinstance(self.output, lambda_apply):
			self.output.bind_variables(placeholder, val, ban_macro_name = ban_macro_name)

	def reduce(self) -> ReductionStatus:

		r = self.output.reduce()

		return ReductionStatus(
			was_reduced = r.was_reduced,
			reduction_type = r.reduction_type,
			output = lambda_func(
				self.input,
				r.output
			)
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
			bound_var = self.input # type: ignore
		new_out = self.output
		if isinstance(self.output, bound_variable):
			if self.output == bound_var:
				new_out = val
		elif isinstance(self.output, lambda_func):
			new_out = self.output.apply(val, bound_var = bound_var)
		elif isinstance(self.output, lambda_apply):
			new_out = self.output.sub_bound_var(val, bound_var = bound_var) # type: ignore

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


class lambda_apply(LambdaToken):
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

	def set_runner(self, runner):
		self.runner = runner
		self.fn.set_runner(runner)
		self.arg.set_runner(runner)

	def __init__(
			self,
			fn: LambdaToken,
			arg: LambdaToken
		):
		self.fn: LambdaToken = fn
		self.arg: LambdaToken = arg

	def __repr__(self) -> str:
		return f"<{self.fn!r} | {self.arg!r}>"

	def __str__(self) -> str:
		return f"({self.fn} {self.arg})"

	def bind_variables(
			self,
			placeholder: macro | None = None,
			val: bound_variable | None = None,
			*,
			ban_macro_name: str | None = None
		) -> None:
		"""
		Does exactly what lambda_func.bind_variables does,
		but acts on applications instead.
		"""

		if (placeholder is None) and (val != placeholder):
			raise Exception(
				"Error while binding variables: placeholder and val are both None."
			)

		# If val and placeholder are None,
		# everything below should still work as expected.
		if isinstance(self.fn, macro) and placeholder is not None:
			if self.fn.name == ban_macro_name:
				raise ReductionError(f"Cannot use macro \"{ban_macro_name}\" here.")
			if self.fn == placeholder:
				self.fn = val # type: ignore
		elif isinstance(self.fn, lambda_func):
			self.fn.bind_variables(placeholder, val, ban_macro_name = ban_macro_name)
		elif isinstance(self.fn, lambda_apply):
			self.fn.bind_variables(placeholder, val, ban_macro_name = ban_macro_name)

		if isinstance(self.arg, macro) and placeholder is not None:
			if self.arg.name == ban_macro_name:
				raise ReductionError(f"Cannot use macro \"{ban_macro_name}\" here.")
			if self.arg == placeholder:
				self.arg = val # type: ignore
		elif isinstance(self.arg, lambda_func):
			self.arg.bind_variables(placeholder, val, ban_macro_name = ban_macro_name)
		elif isinstance(self.arg, lambda_apply):
			self.arg.bind_variables(placeholder, val, ban_macro_name = ban_macro_name)

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

	def reduce(self) -> ReductionStatus:

		# If we can directly apply self.fn, do so.
		if isinstance(self.fn, lambda_func):
			return ReductionStatus(
				was_reduced = True,
				reduction_type = ReductionType.FUNCTION_APPLY,
				output = self.fn.apply(self.arg)
			)

		# Otherwise, try to reduce self.fn.
		# If that is impossible, try to reduce self.arg.
		else:
			if isinstance(self.fn, macro) or isinstance(self.fn, church_num):
				# Macros must be reduced before we apply them as functions.
				# This is the only place we force substitution.
				r = self.fn.reduce(
					force_substitute = True
				)
			else:
				r = self.fn.reduce()

			if r.was_reduced:
				return ReductionStatus(
					was_reduced = True,
					reduction_type = r.reduction_type,
					output = lambda_apply(
						r.output,
						self.arg
					)
				)

			else:
				r = self.arg.reduce()

				return ReductionStatus(
					was_reduced = r.was_reduced,
					reduction_type = r.reduction_type,
					output = lambda_apply(
						self.fn,
						r.output
					)
				)
