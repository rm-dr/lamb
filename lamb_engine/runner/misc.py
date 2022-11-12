import enum
import lamb_engine

class StopReason(enum.Enum):
	BETA_NORMAL		= ("class:text", "β-normal form")
	LOOP_DETECTED	= ("class:warn", "Loop detected")
	MAX_EXCEEDED	= ("class:err", "Too many reductions")
	INTERRUPT		= ("class:warn", "User interrupt")
	SHOW_MACRO		= ("class:text", "Displaying macro content")

class MacroDef:
	@staticmethod
	def from_parse(result):
		return MacroDef(
			result[0].name,
			result[1]
		)

	def __init__(self, label: str, expr: lamb_engine.nodes.Node):
		self.label = label
		self.expr = expr

	def __repr__(self):
		return f"<{self.label} := {self.expr!r}>"

	def __str__(self):
		return f"{self.label} := {self.expr}"

	def set_runner(self, runner):
		return self.expr.set_runner(runner)

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
