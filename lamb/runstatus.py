from prompt_toolkit.formatted_text import FormattedText
from prompt_toolkit.formatted_text import HTML
import enum

import lamb.tokens as tokens


class NotAMacro(Exception):
	"""
	Raised when we try to run a non-macro line
	while enforcing macro_only in Runner.run().

	This should be caught and elegantly presented to the user.
	"""
	pass

class RunStatus:
	"""
	Base class for run status.
	These are returned whenever the runner does something.
	"""
	pass

class MacroStatus(RunStatus):
	"""
	Returned when a macro is defined.

	Values:
	`was_rewritten`:	If true, an old macro was replaced.
	`macro_label`:		The name of the macro we just made.
	`macro_expr`:		The expr of the macro we just made.
	"""

	def __init__(
		self,
		*,
		was_rewritten: bool,
		macro_label: str,
		macro_expr
	):
		self.was_rewritten = was_rewritten
		self.macro_label = macro_label
		self.macro_expr = macro_expr


class StopReason(enum.Enum):
	BETA_NORMAL		= ("class:text", "β-normal form")
	LOOP_DETECTED	= ("class:warn", "loop detected")
	MAX_EXCEEDED	= ("class:err", "too many reductions")
	INTERRUPT		= ("class:warn", "user interrupt")


class ReduceStatus(RunStatus):
	"""
	Returned when an expression is reduced.

	Values:
	`reduction_count`:	How many reductions were made.
	`stop_reason`:		Why we stopped. See `StopReason`.
	"""

	def __init__(
		self,
		*,
		reduction_count: int,
		stop_reason: StopReason,
		result: tokens.LambdaToken
	):
		self.reduction_count = reduction_count
		self.stop_reason = stop_reason
		self.result = result


class CommandStatus(RunStatus):
	"""
	Returned when a command is executed.
	Doesn't do anything interesting.

	Values:
	`cmd`: The command that was run, without a colon.
	"""

	def __init__(self, *, cmd: str):
		self.cmd = cmd