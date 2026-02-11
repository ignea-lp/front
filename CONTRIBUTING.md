# Contributing Guidelines

## Code Style

All common, lexical and syntactic code in the library must follow this code style. Type hints, assertions, comments and documentation must be updated whenever the related code changes.

### Formatting

Code must be formatted using `black -l 79`.

### Linting

Code must pass `flake8` and `pylint`, with the only exceptions being due to changes made by `black`.

### Type Checking

Code must pass `mypy`, with the only exceptions being due to the limitations of the tool itself.

#### Type Hints

Global variables, class attributes and function/method signatures must be annotated. Local variables must only be annotated whenever `mypy` cannot infer the correct type.

#### Assertions

Assertions must be used to provide `mypy` with extra type information that type hints alone cannot. They must also be used to make explicit the implicit invariants in the code.

### Comments

Comments must be provided whenever a statement needs clarification of its purpose or how it works. They must also be used to document code that garantees invariants in the code.

### Documentation

Docstrings must be provided for all modules, classes and functions/methods, regardless of whether they are public/private. They must describe all attributes, arguments, return values and exceptions raised, regardless of whether they are public/private. They must also describe all invariants relevant across the code interfaces. They must use the Google-style format with Markdown markup.

## Reproducibility

To ensure this project is and remains [reproducible](https://reproducible-builds.org/), it is essential to ensure the collections iterated over when generating the output are ordered. In particular, sets and frozen sets must only be used if doing so would not change the output. Instead, use dictionaries, lists or tuples.
