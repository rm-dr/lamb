# Lamb: A Lambda Calculus Engine

![Lamb screenshot](./misc/screenshot.png)

## Installation

### Method 1: PyPi (not yet)
1. Put this on PyPi
2. Write these instructions

### Method 2: Git
1. Clone this repository.
2. Make and enter a [virtual environment](https://docs.python.org/3/library/venv.html).
3. ``cd`` into this directory
4. Run ``pip install .``
5. Run ``python .``

-------------------------------------------------

## Usage


Type lambda expressions into the prompt, and Lamb will evaluate them. \
Use your `\` (backslash) key to type a `λ`. \
To define macros, use `=`. For example,
```
==> T = λab.a
==> F = λab.a
==> NOT = λa.a F T
```

Note that there are spaces in `λa.a F T`. With no spaces, `aFT` will be parsed as one variable. \
Lambda functions can only take single-letter, lowercase arguments. `λA.A` is not valid syntax. \
Free variables will be shown with a `'`, like `a'`.

Macros are case-sensitive. If you define a macro `MAC` and accidentally write `mac` in the prompt, `mac` will become a free variable.

Numbers will automatically be converted to Church numerals. For example, the following line will reduce to `T`.
```
==> 3 NOT F
```

If an expression takes too long to evaluate, you may interrupt reduction with `Ctrl-C`. \
Exit the prompt with `Ctrl-C` or `Ctrl-D`.

There are many useful macros in [macros.lamb](./macros.lamb). Load them with the `:load` command:
```
==> :load macros.lamb
```

Have fun!

-------------------------------------------------

## Commands

Lamb understands many commands. Prefix them with a `:` in the prompt.

`:help` Prints a help message

`:clear` Clear the screen

`:rlimit [int | None]` Set maximum reduction limit. `:rlimit none` sets no limit.

`:macros` List macros in the current environment.

`:mdel [macro]` Delete a macro

`:clearmacros` Delete all macros

`:save [filename]` \
`:load [filename]` \
Save or load macros from a file.
The lines in a file look exactly the same as regular entries in the prompt, but can only contain macro definitions. See [macros.lamb](./macros.lamb) for an example.

-------------------------------------------------


## Todo (pre-release, in this order):
 - Cleanup warnings
 - Truncate long expressions in warnings
 - Prevent macro-chaining recursion
 - Full-reduce option (expand all macros)
 - step-by-step reduction
 - Update screenshot
 - Update documentation
 - Write "how it works"
 - PyPi package


## Todo:
 - History queue + indexing
 - Show history command
 - Loop detection
 - $\alpha$-equivalence check
 - Command-line options (load a file)
 - Unchurch command: make church numerals human-readable
 - Better Syntax highlighting
 - Syntax highlight printouts
 - Tests