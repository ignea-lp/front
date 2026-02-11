# Version 0.5.0

- Remove deprecated APIs.
- Improve lexical error diagnostics by providing closest match information whenever possible.
- Add string representation to `IgneaMeta`.
- Support generic location string besides `IgneaPosition` in `IgneaException`.
- Support omiting location information in `IgneaException`.
- Add `IgneaError` to group errors.
- Add `IgneaConditionsError` and `IgneaConditionsWarning` to group runtime conditions errors and warnings.
- Update exception classes to use new APIs.
- Provide grammar symbol as location to conditions errors.
- Raise `IgneaSpecifierNotExclusiveError` when other specifiers are provided with indent/dedent.

# Version 0.4.0

- Add support of off-side rule.

# Version 0.3.0

- Remove deprecated APIs.
- Rename APIs to reflect project renaming.
- Deprecate `TransmuterConditions`, `TransmuterCondition`, `TransmuterPosition`, `TransmuterException`, `TransmuterExceptionHandler`, `TransmuterWarning`, `transmuter_init_warnings`, `TransmuterLexingState`, `TransmuterTerminalTag`, `TransmuterTerminal`, `TransmuterLexer`, `TransmuterLexicalError`, `TransmuterNoTerminalTagError`, `transmuter_selection`, `transmuter_compute_sccs`, `TransmuterNonterminalType`, `TransmuterParsingState`, `TransmuterEPN`, `TransmuterBSR`, `TransmuterParser`, `TransmuterSyntacticError`, `TransmuterNoStartError`, `TransmuterMultipleStartsError`, `TransmuterNoDerivationError` and `TransmuterDerivationException`.

# Version 0.2.0

- Add comments to code.
- Improve variable names.
- Memoize NFAs in lexer.
- Split lexer cache data into separate object.
- Optimize update of accepted terminal tags in `_get_terminal`.
- Store lexer transient containers into separate object so it can be reused.
- Simplify syntactic internal error.
- Move `transmuter_compute_sccs` to syntactic module.
- Add docstrings to code.
- Improve internal exception and method names.
- Define module public APIs.
- Deprecate `TransmuterNoTerminalError`, `TransmuterParser.call` and `TransmuterInternalError`.

# Version 0.1.0

Initial release.
