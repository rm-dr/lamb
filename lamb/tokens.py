import enum
import lamb.utils as utils



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


class church_num(LambdaToken):
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

class macro(LambdaToken):
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


class lambda_func(LambdaToken):
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
