# Things the analyser must do:
# - Name resolution: turn names into an index, plus a measure of 'non-locality'; basically how many times an outer scope must be entered to find the binding
# - Type analysis: every expression must be assigned its type so that consistency constraints can be checked
# - Multiple dispatch: sort of as a corollary to the above, expressions that resolve to functions need to determine which definition to use, based on the call signature, and *maybe* also the return type, so far as that can be inferred. Might be a feature to defer, though.
# - Output the AST ready for compiling to bytecode
# Optional features:
# - Compile-time computation: one possible optimisation to the compiled bytecode would be to perform some of the computations statically during this phase - e.g, numeric arithmetic
# - Another optimisation could be to alter the program structure to eliminate unnecessary elements of the bytecode
