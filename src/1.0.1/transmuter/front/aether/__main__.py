# Ignea front-end, front-end libraries and utilities for the
# Ignea language processing infrastructure
# Copyright (C) 2025  The Ignea Project
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program.  If not, see <https://www.gnu.org/licenses/>.

from argparse import ArgumentParser
from os import path

from ..common import TransmuterExceptionHandler
from ..semantic.common import (
    TransmuterBSRDisambiguator,
    TransmuterBSRToTreeConverter,
)
from . import __version__
from .common import Conditions
from .lexical import Lexer
from .syntactic import Parser
from .semantic import LexicalSymbolTableBuilder, SyntacticSymbolTableBuilder


def main():
    arg_parser = ArgumentParser(
        prog="aether",
        description="The front-end generator for the Transmuter language processing infrastructure.",
    )
    arg_parser.add_argument(
        "-v",
        "--version",
        action="version",
        version=f"%(prog)s {__version__.src_version} (spec {__version__.spec_version} / lib {__version__.lib_version})",
    )
    arg_parser.add_argument(
        "-L",
        "--language",
        default="python",
        choices=["python"],
        help="The programming language the output files will be generated in.",
    )
    arg_parser.add_argument(
        "-o", "--output", default=".", help="The path of the output folder."
    )
    arg_parser.add_argument(
        "input",
        help="The path of the input folder. It must contain `lexical.aether` and `syntactic.aether`.",
    )
    args = arg_parser.parse_args()

    with open(
        path.join(args.input, "lexical.aether"), encoding="UTF-8"
    ) as lexical_file:
        lexical_input = lexical_file.read()

    with open(
        path.join(args.input, "syntactic.aether"), encoding="UTF-8"
    ) as syntactic_file:
        syntactic_input = syntactic_file.read()

    with TransmuterExceptionHandler():
        lexical_lexer = Lexer(
            path.join(args.input, "lexical.aether"),
            lexical_input,
            Conditions.lexical,
        )
        syntactic_lexer = Lexer(
            path.join(args.input, "syntactic.aether"),
            syntactic_input,
            Conditions.syntactic,
        )
        lexical_parser = Parser(lexical_lexer)
        syntactic_parser = Parser(syntactic_lexer)
        lexical_parser.parse()
        syntactic_parser.parse()
        TransmuterBSRDisambiguator.get(lexical_parser.bsr).visit()
        TransmuterBSRDisambiguator.get(syntactic_parser.bsr).visit()
        tree_converter = TransmuterBSRToTreeConverter.get(lexical_parser.bsr)
        tree_converter.visit()
        lexical_tree = tree_converter.tree
        tree_converter = TransmuterBSRToTreeConverter.get(syntactic_parser.bsr)
        tree_converter.visit()
        syntactic_tree = tree_converter.tree
        lexical_table_builder = LexicalSymbolTableBuilder(lexical_tree)
        lexical_table_builder.visit()
        syntactic_table_builder = SyntacticSymbolTableBuilder(
            syntactic_tree,
            lexical_table_builder.condition_table,
            lexical_table_builder.terminal_table,
        )
        syntactic_table_builder.visit()

        if args.language == "python":
            from .back.python import (
                CommonFileFold,
                ConditionFold,
                LexicalFileFold,
                ExpressionFold,
                SyntacticFileFold,
            )

            common_fold = CommonFileFold(lexical_table_builder.condition_table)
            lexical_fold = LexicalFileFold(
                lexical_table_builder.terminal_table, ConditionFold
            )
            syntactic_fold = SyntacticFileFold(
                syntactic_table_builder.nonterminal_table,
                ConditionFold,
                ExpressionFold,
            )
            common_output = common_fold.fold()
            lexical_output = lexical_fold.fold()
            syntactic_output = syntactic_fold.fold()

            with open(
                path.join(args.output, "common.py"), mode="w", encoding="UTF-8"
            ) as common_file:
                common_file.write(common_output)

            with open(
                path.join(args.output, "lexical.py"),
                mode="w",
                encoding="UTF-8",
            ) as lexical_file:
                lexical_file.write(lexical_output)

            with open(
                path.join(args.output, "syntactic.py"),
                mode="w",
                encoding="UTF-8",
            ) as syntactic_file:
                syntactic_file.write(syntactic_output)


main()
