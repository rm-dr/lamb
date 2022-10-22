from prompt_toolkit import PromptSession
from prompt_toolkit.completion import WordCompleter
from prompt_toolkit import print_formatted_text as printf
from prompt_toolkit.formatted_text import FormattedText
from prompt_toolkit.formatted_text import to_plain_text
from prompt_toolkit.key_binding import KeyBindings
from prompt_toolkit.lexers import Lexer

from pyparsing import exceptions as ppx

from lamb.parser import Parser
import lamb.runner as runner
import lamb.runstatus as rs
import lamb.tokens as tokens
import lamb.utils as utils


# Simple lexer for highlighting.
# Improve this later.
class LambdaLexer(Lexer):
	def lex_document(self, document):
		def inner(line_no):
			return [("class:text", str(document.lines[line_no]))]
		return inner

# Replace "\" with a pretty "λ" in the prompt
bindings = KeyBindings()
@bindings.add("\\")
def _(event):
	event.current_buffer.insert_text("λ")

session = PromptSession(
	message = FormattedText([
		("class:prompt", "~~> ")
	]),
	style = utils.style,
	lexer = LambdaLexer(),
	key_bindings = bindings
)


utils.show_greeting()


r = runner.Runner()

r.run_lines([
	"T = λab.a",
	"F = λab.b",
	"NOT = λa.(a F T)",
	"AND = λab.(a F b)",
	"OR = λab.(a T b)",
	"XOR = λab.(a (NOT a b) b)",
	"w = λx.(x x)",
	"W = w w",
	"Y = λf.( (λx.(f (x x))) (λx.(f (x x))) )",
	"PAIR = λabi.( i a b )",
	"inc = λnfa.(f (n f a))",
	"zero = λax.x",
	"one = λfx.(f x)"
])


while True:
	try:
		i = session.prompt()

	# Catch Ctrl-C and Ctrl-D
	except KeyboardInterrupt:
		printf("\n\nGoodbye.\n")
		break
	except EOFError:
		printf("\n\nGoodbye.\n")
		break

	# Skip empty lines
	if i.strip() == "":
		continue


	# Try to run an input line.
	# Catch parse errors and point them out.
	try:
		x = r.run(i)
	except ppx.ParseException as e:
		l = len(to_plain_text(session.message))
		printf(FormattedText([
			("class:err", " "*(e.loc + l) + "^\n"),
			("class:err", f"Syntax error at char {e.loc}."),
			("class:text", "\n")
		]))
		continue
	except tokens.ReductionError as e:
		printf(FormattedText([
			("class:err", f"{e.msg}\n")
		]), style = utils.style)
		continue

	# If this line defined a macro, print nothing.
	if isinstance(x, rs.MacroStatus):
		printf(FormattedText([
			("class:text", "Set "),
			("class:syn_macro", x.macro_label),
			("class:text", " to "),
			("class:text", str(x.macro_expr))
		]), style = utils.style)


	if isinstance(x, rs.CommandStatus):
		printf(x.formatted_text, style = utils.style)

	# If this line was an expression, print reduction status
	elif isinstance(x, rs.ReduceStatus):
		printf(FormattedText([
			("class:result_header", f"\nExit reason: "),
			x.stop_reason.value,

			("class:result_header", f"\nReduction count: "),
			("class:text", str(x.reduction_count)),


			("class:result_header", "\n\n    => "),
			("class:text", str(x.result)),
		]), style = utils.style)

	printf("")
