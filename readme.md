# What???

Drake is a toy programming language based originally on Python with influence from functional programming paradigms.
It's strongly-typed, with a type inference system (once we work out type theory), makes generous use of lambda expressions,
and does some fun stuff with scopes and mutability.

# Outline

Source -> AST -> bytecode?

* Source -> *lexer* -> token stream
* token stream -> *parser* -> AST
* AST -> *evaluator* -> running program
* AST -> *compiler* -> bytecode
* bytecode -> *executor* -> running program
