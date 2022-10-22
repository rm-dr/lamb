import tokens

def autochurch(results):
	"""
	Makes a church numeral from an integer.
	"""

	num = int(results[0])

	f = tokens.bound_variable()
	a = tokens.bound_variable()

	chain = a

	for i in range(num):
		chain = tokens.lambda_apply(f, chain)

	return tokens.lambda_func(
		f,
		tokens.lambda_func(
			a,
			chain
		)
	)