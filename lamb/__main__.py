from prompt_toolkit import PromptSession
from prompt_toolkit.completion import WordCompleter
from prompt_toolkit import print_formatted_text as printf
from prompt_toolkit.formatted_text import FormattedText
from prompt_toolkit.formatted_text import to_plain_text
from prompt_toolkit.key_binding import KeyBindings
from prompt_toolkit.lexers import Lexer

from pyparsing import exceptions as ppx

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


utils.show_greeting()


# Replace "\" with pretty "λ"s
bindings = KeyBindings()
@bindings.add("\\")
def _(event):
	event.current_buffer.insert_text("λ")


r = runner.Runner(
	prompt_session = PromptSession(
		style = utils.style,
		lexer = LambdaLexer(),
		key_bindings = bindings
	),

	prompt_message = FormattedText([
		("class:prompt", "~~> ")
	]),
)

r.run_lines([
	"T = λab.a",
	"F = λab.b",
	"NOT = λa.(a F T)",
	"AND = λab.(a F b)",
	"OR = λab.(a T b)",
	"XOR = λab.(a (NOT a b) b)",
	"M = λx.(x x)",
	"W = M M",
	"Y = λf.( (λx.(f (x x))) (λx.(f (x x))) )",
	"PAIR = λabi.( i a b )",
	"S = λnfa.(f (n f a))",
	"Z = λn.n (λa.F) T",
	"MULT = λnmf.n (m f)",
	"H = λp.((PAIR (p F)) (S (p F)))",
	"D = λn.n H (PAIR 0 0) T",
	"FAC = λyn.(Z n)(1)(MULT n (y (D n)))"
])


while True:
	try:
		i = r.prompt()

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
		l = len(to_plain_text(r.prompt_session.message))
		printf(FormattedText([
			("class:err", " "*(e.loc + l) + "^\n"),
			("class:err", f"Syntax error at char {e.loc}."),
			("class:text", "\n")
		]), style = utils.style)
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
		pass

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
