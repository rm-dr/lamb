import enum

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
