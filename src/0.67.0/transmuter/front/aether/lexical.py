# Ignea front-end, front-end libraries and utilities for the
# Ignea language processing infrastructure
# Copyright (C) 2024  Natan Junges <natanajunges@gmail.com>
# Copyright (C) 2024  The Ignea Project
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

from ..common import TransmuterConditions
from ..lexical import TransmuterLexingState, TransmuterTerminalTag, TransmuterLexer
from .common import Conditions


class Whitespace(TransmuterTerminalTag):
    # S0 | S1 | S2
    STATES_START = 7

    @staticmethod
    def ignore(conditions: TransmuterConditions) -> bool:
        return True

    @staticmethod
    def nfa(current_states: TransmuterLexingState, char: str) -> tuple[bool, TransmuterLexingState]:
        state_accept = False
        next_states = 0

        # 1:22
        # S0
        if 1 & current_states and (char in "\t "):
            state_accept = True
            # S0 | S1 | S2
            next_states |= 7

        # 1:30
        # S1
        if 2 & current_states and (char == "\r"):
            # S2
            next_states |= 4

        # 1:34
        # S2
        if 4 & current_states and (char == "\n"):
            state_accept = True
            # S0 | S1 | S2
            next_states |= 7

        return (state_accept, next_states)


class Identifier(TransmuterTerminalTag):
    @staticmethod
    def positives(conditions: TransmuterConditions) -> set[type[TransmuterTerminalTag]]:
        positives = {OrdChar}
        return positives

    @staticmethod
    def nfa(current_states: TransmuterLexingState, char: str) -> tuple[bool, TransmuterLexingState]:
        state_accept = False
        next_states = 0

        # 3:23
        # S0
        if 1 & current_states and ("A" <= char <= "Z" or char == "_" or "a" <= char <= "z"):
            state_accept = True
            # S1
            next_states |= 2

        # 3:33
        # S1
        if 2 & current_states and ("0" <= char <= "9" or "A" <= char <= "Z" or char == "_" or "a" <= char <= "z"):
            state_accept = True
            # S1
            next_states |= 2

        return (state_accept, next_states)


class Colon(TransmuterTerminalTag):
    @staticmethod
    def positives(conditions: TransmuterConditions) -> set[type[TransmuterTerminalTag]]:
        positives = {OrdChar}
        return positives

    @staticmethod
    def nfa(current_states: TransmuterLexingState, char: str) -> tuple[bool, TransmuterLexingState]:
        state_accept = False
        next_states = 0

        # 5:18
        if char == ":":
            state_accept = True

        return (state_accept, next_states)


class Semicolon(TransmuterTerminalTag):
    @staticmethod
    def nfa(current_states: TransmuterLexingState, char: str) -> tuple[bool, TransmuterLexingState]:
        state_accept = False
        next_states = 0

        # 7:12
        if char == ";":
            state_accept = True

        return (state_accept, next_states)


class CommercialAt(TransmuterTerminalTag):
    @staticmethod
    def positives(conditions: TransmuterConditions) -> set[type[TransmuterTerminalTag]]:
        positives = {OrdChar}
        return positives

    @staticmethod
    def nfa(current_states: TransmuterLexingState, char: str) -> tuple[bool, TransmuterLexingState]:
        state_accept = False
        next_states = 0

        # 9:25
        if char == "@":
            state_accept = True

        return (state_accept, next_states)


class LeftParenthesis(TransmuterTerminalTag):
    @staticmethod
    def nfa(current_states: TransmuterLexingState, char: str) -> tuple[bool, TransmuterLexingState]:
        state_accept = False
        next_states = 0

        # 11:18
        if char == "(":
            state_accept = True

        return (state_accept, next_states)


class RightParenthesis(TransmuterTerminalTag):
    @staticmethod
    def nfa(current_states: TransmuterLexingState, char: str) -> tuple[bool, TransmuterLexingState]:
        state_accept = False
        next_states = 0

        # 13:19
        if char == ")":
            state_accept = True

        return (state_accept, next_states)


class VerticalLine(TransmuterTerminalTag):
    @staticmethod
    def nfa(current_states: TransmuterLexingState, char: str) -> tuple[bool, TransmuterLexingState]:
        state_accept = False
        next_states = 0

        # 15:15
        if char == "|":
            state_accept = True

        return (state_accept, next_states)


class Solidus(TransmuterTerminalTag):
    @staticmethod
    def start(conditions: TransmuterConditions) -> bool:
        return Conditions.syntactic in conditions

    @staticmethod
    def nfa(current_states: TransmuterLexingState, char: str) -> tuple[bool, TransmuterLexingState]:
        state_accept = False
        next_states = 0

        # 17:20
        if char == "/":
            state_accept = True

        return (state_accept, next_states)


class DoubleVerticalLine(TransmuterTerminalTag):
    @staticmethod
    def nfa(current_states: TransmuterLexingState, char: str) -> tuple[bool, TransmuterLexingState]:
        state_accept = False
        next_states = 0

        # 19:21
        # S0
        if 1 & current_states and (char == "|"):
            # S1
            next_states |= 2

        # 19:24
        # S1
        if 2 & current_states and (char == "|"):
            state_accept = True

        return (state_accept, next_states)


class Comma(TransmuterTerminalTag):
    @staticmethod
    def positives(conditions: TransmuterConditions) -> set[type[TransmuterTerminalTag]]:
        positives = {OrdChar}
        return positives

    @staticmethod
    def nfa(current_states: TransmuterLexingState, char: str) -> tuple[bool, TransmuterLexingState]:
        state_accept = False
        next_states = 0

        # 21:18
        if char == ",":
            state_accept = True

        return (state_accept, next_states)


class DoubleAmpersand(TransmuterTerminalTag):
    @staticmethod
    def positives(conditions: TransmuterConditions) -> set[type[TransmuterTerminalTag]]:
        positives = {OrdChar}
        return positives

    @staticmethod
    def nfa(current_states: TransmuterLexingState, char: str) -> tuple[bool, TransmuterLexingState]:
        state_accept = False
        next_states = 0

        # 23:28
        # S0
        if 1 & current_states and (char == "&"):
            # S1
            next_states |= 2

        # 23:29
        # S1
        if 2 & current_states and (char == "&"):
            state_accept = True

        return (state_accept, next_states)


class PlusSign(TransmuterTerminalTag):
    @staticmethod
    def start(conditions: TransmuterConditions) -> bool:
        return Conditions.lexical in conditions

    @staticmethod
    def nfa(current_states: TransmuterLexingState, char: str) -> tuple[bool, TransmuterLexingState]:
        state_accept = False
        next_states = 0

        # 25:19
        if char == "+":
            state_accept = True

        return (state_accept, next_states)


class HyphenMinus(TransmuterTerminalTag):
    @staticmethod
    def start(conditions: TransmuterConditions) -> bool:
        return Conditions.lexical in conditions

    @staticmethod
    def positives(conditions: TransmuterConditions) -> set[type[TransmuterTerminalTag]]:
        positives = {OrdChar}
        return positives

    @staticmethod
    def nfa(current_states: TransmuterLexingState, char: str) -> tuple[bool, TransmuterLexingState]:
        state_accept = False
        next_states = 0

        # 27:32
        if char == "-":
            state_accept = True

        return (state_accept, next_states)


class Ignore(TransmuterTerminalTag):
    @staticmethod
    def start(conditions: TransmuterConditions) -> bool:
        return Conditions.lexical in conditions

    @staticmethod
    def positives(conditions: TransmuterConditions) -> set[type[TransmuterTerminalTag]]:
        positives = {OrdChar}
        return positives

    @staticmethod
    def negatives(conditions: TransmuterConditions) -> set[type[TransmuterTerminalTag]]:
        negatives = {Identifier}
        return negatives

    @staticmethod
    def nfa(current_states: TransmuterLexingState, char: str) -> tuple[bool, TransmuterLexingState]:
        state_accept = False
        next_states = 0

        # 29:40
        # S0
        if 1 & current_states and (char == "i"):
            # S1
            next_states |= 2

        # 29:41
        # S1
        if 2 & current_states and (char == "g"):
            # S2
            next_states |= 4

        # 29:42
        # S2
        if 4 & current_states and (char == "n"):
            # S3
            next_states |= 8

        # 29:43
        # S3
        if 8 & current_states and (char == "o"):
            # S4
            next_states |= 16

        # 29:44
        # S4
        if 16 & current_states and (char == "r"):
            # S5
            next_states |= 32

        # 29:45
        # S5
        if 32 & current_states and (char == "e"):
            state_accept = True

        return (state_accept, next_states)


class Start(TransmuterTerminalTag):
    @staticmethod
    def start(conditions: TransmuterConditions) -> bool:
        return Conditions.syntactic in conditions

    @staticmethod
    def negatives(conditions: TransmuterConditions) -> set[type[TransmuterTerminalTag]]:
        negatives = {Identifier}
        return negatives

    @staticmethod
    def nfa(current_states: TransmuterLexingState, char: str) -> tuple[bool, TransmuterLexingState]:
        state_accept = False
        next_states = 0

        # 31:31
        # S0
        if 1 & current_states and (char == "s"):
            # S1
            next_states |= 2

        # 31:32
        # S1
        if 2 & current_states and (char == "t"):
            # S2
            next_states |= 4

        # 31:33
        # S2
        if 4 & current_states and (char == "a"):
            # S3
            next_states |= 8

        # 31:34
        # S3
        if 8 & current_states and (char == "r"):
            # S4
            next_states |= 16

        # 31:35
        # S4
        if 16 & current_states and (char == "t"):
            state_accept = True

        return (state_accept, next_states)


class Asterisk(TransmuterTerminalTag):
    @staticmethod
    def start(conditions: TransmuterConditions) -> bool:
        return Conditions.lexical in conditions

    @staticmethod
    def nfa(current_states: TransmuterLexingState, char: str) -> tuple[bool, TransmuterLexingState]:
        state_accept = False
        next_states = 0

        # 33:19
        if char == "*":
            state_accept = True

        return (state_accept, next_states)


class QuestionMark(TransmuterTerminalTag):
    @staticmethod
    def start(conditions: TransmuterConditions) -> bool:
        return Conditions.lexical in conditions

    @staticmethod
    def nfa(current_states: TransmuterLexingState, char: str) -> tuple[bool, TransmuterLexingState]:
        state_accept = False
        next_states = 0

        # 35:23
        if char == "?":
            state_accept = True

        return (state_accept, next_states)


class ExpressionRange(TransmuterTerminalTag):
    @staticmethod
    def start(conditions: TransmuterConditions) -> bool:
        return Conditions.lexical in conditions

    @staticmethod
    def nfa(current_states: TransmuterLexingState, char: str) -> tuple[bool, TransmuterLexingState]:
        state_accept = False
        next_states = 0

        # 37:26
        # S0
        if 1 & current_states and (char == "{"):
            # S1 | S2
            next_states |= 6

        # 37:30
        # S1
        if 2 & current_states and (char == "0"):
            # S4 | S8
            next_states |= 272

        # 37:34
        # S2
        if 4 & current_states and ("1" <= char <= "9"):
            # S3 | S4 | S8
            next_states |= 280

        # 37:40
        # S3
        if 8 & current_states and ("0" <= char <= "9"):
            # S3 | S4 | S8
            next_states |= 280

        # 37:49
        # S4
        if 16 & current_states and (char == ","):
            # S5 | S6 | S8
            next_states |= 352

        # 37:52
        # S5
        if 32 & current_states and (char == "0"):
            # S8
            next_states |= 256

        # 37:56
        # S6
        if 64 & current_states and ("1" <= char <= "9"):
            # S7 | S8
            next_states |= 384

        # 37:62
        # S7
        if 128 & current_states and ("0" <= char <= "9"):
            # S7 | S8
            next_states |= 384

        # 37:73
        # S8
        if 256 & current_states and (char == "}"):
            state_accept = True

        return (state_accept, next_states)


class LeftCurlyBracket(TransmuterTerminalTag):
    @staticmethod
    def start(conditions: TransmuterConditions) -> bool:
        return Conditions.syntactic in conditions

    @staticmethod
    def nfa(current_states: TransmuterLexingState, char: str) -> tuple[bool, TransmuterLexingState]:
        state_accept = False
        next_states = 0

        # 39:29
        if char == "{":
            state_accept = True

        return (state_accept, next_states)


class LeftCurlyBracketSolidus(TransmuterTerminalTag):
    @staticmethod
    def start(conditions: TransmuterConditions) -> bool:
        return Conditions.syntactic in conditions

    @staticmethod
    def nfa(current_states: TransmuterLexingState, char: str) -> tuple[bool, TransmuterLexingState]:
        state_accept = False
        next_states = 0

        # 41:36
        # S0
        if 1 & current_states and (char == "{"):
            # S1
            next_states |= 2

        # 41:39
        # S1
        if 2 & current_states and (char == "/"):
            state_accept = True

        return (state_accept, next_states)


class RightCurlyBracket(TransmuterTerminalTag):
    @staticmethod
    def start(conditions: TransmuterConditions) -> bool:
        return Conditions.syntactic in conditions

    @staticmethod
    def nfa(current_states: TransmuterLexingState, char: str) -> tuple[bool, TransmuterLexingState]:
        state_accept = False
        next_states = 0

        # 43:30
        if char == "}":
            state_accept = True

        return (state_accept, next_states)


class OrdChar(TransmuterTerminalTag):
    @staticmethod
    def start(conditions: TransmuterConditions) -> bool:
        return Conditions.lexical in conditions

    @staticmethod
    def nfa(current_states: TransmuterLexingState, char: str) -> tuple[bool, TransmuterLexingState]:
        state_accept = False
        next_states = 0

        # 45:18
        if not ("\000" <= char <= "\037" or char in " $()*+.;?[\\^{|\177"):
            state_accept = True

        return (state_accept, next_states)


class QuotedChar(TransmuterTerminalTag):
    @staticmethod
    def start(conditions: TransmuterConditions) -> bool:
        return Conditions.lexical in conditions

    @staticmethod
    def nfa(current_states: TransmuterLexingState, char: str) -> tuple[bool, TransmuterLexingState]:
        state_accept = False
        next_states = 0

        # 47:21
        # S0
        if 1 & current_states and (char == "\\"):
            # S1 | S2
            next_states |= 6

        # 47:25
        # S1
        if 2 & current_states and (char in " $()*+.;?[\\^abfnrtv{|"):
            state_accept = True

        # 47:52
        # S2
        if 4 & current_states and (char in "01"):
            # S3
            next_states |= 8

        # 47:57:1
        # S3
        if 8 & current_states and ("0" <= char <= "7"):
            # S4
            next_states |= 16

        # 47:57:2
        # S4
        if 16 & current_states and ("0" <= char <= "7"):
            state_accept = True

        return (state_accept, next_states)


class FullStop(TransmuterTerminalTag):
    @staticmethod
    def start(conditions: TransmuterConditions) -> bool:
        return Conditions.lexical in conditions

    @staticmethod
    def nfa(current_states: TransmuterLexingState, char: str) -> tuple[bool, TransmuterLexingState]:
        state_accept = False
        next_states = 0

        # 49:19
        if char == ".":
            state_accept = True

        return (state_accept, next_states)


class BracketExpression(TransmuterTerminalTag):
    @staticmethod
    def start(conditions: TransmuterConditions) -> bool:
        return Conditions.lexical in conditions

    @staticmethod
    def nfa(current_states: TransmuterLexingState, char: str) -> tuple[bool, TransmuterLexingState]:
        state_accept = False
        next_states = 0

        # 51:28
        # S0
        if 1 & current_states and (char == "["):
            # S1 | S2 | S3 | S8
            next_states |= 270

        # 51:32
        # S1
        if 2 & current_states and (char == "^"):
            # S2 | S3
            next_states |= 12

        # 51:37
        # S2
        if 4 & current_states and (not ("\000" <= char <= "\037" or char in "\\^\177")):
            # S10 | S17 | S18 | S30 | S31
            next_states |= 3221619712

        # 51:59
        # S3
        if 8 & current_states and (char == "\\"):
            # S4 | S5
            next_states |= 48

        # 51:63
        # S4
        if 16 & current_states and (char in "\\abfnrtv"):
            # S10 | S17 | S18 | S30 | S31
            next_states |= 3221619712

        # 51:77
        # S5
        if 32 & current_states and (char in "01"):
            # S6
            next_states |= 64

        # 51:82:1
        # S6
        if 64 & current_states and ("0" <= char <= "7"):
            # S7
            next_states |= 128

        # 51:82:2
        # S7
        if 128 & current_states and ("0" <= char <= "7"):
            # S10 | S17 | S18 | S30 | S31
            next_states |= 3221619712

        # 51:95
        # S8
        if 256 & current_states and (char == "^"):
            # S9
            next_states |= 512

        # 51:98
        # S9
        if 512 & current_states and (char == "^"):
            # S10 | S17 | S18 | S30 | S31
            next_states |= 3221619712

        # 51:103
        # S10
        if 1024 & current_states and (char == "-"):
            # S11 | S12
            next_states |= 6144

        # 51:106
        # S11
        if 2048 & current_states and (not (char == "]" or "\000" <= char <= "\037" or char in "\\\177")):
            # S17 | S18 | S30 | S31
            next_states |= 3221618688

        # 51:128
        # S12
        if 4096 & current_states and (char == "\\"):
            # S13 | S14
            next_states |= 24576

        # 51:132
        # S13
        if 8192 & current_states and (char in "\\abfnrtv"):
            # S17 | S18 | S30 | S31
            next_states |= 3221618688

        # 51:146
        # S14
        if 16384 & current_states and (char in "01"):
            # S15
            next_states |= 32768

        # 51:151:1
        # S15
        if 32768 & current_states and ("0" <= char <= "7"):
            # S16
            next_states |= 65536

        # 51:151:2
        # S16
        if 65536 & current_states and ("0" <= char <= "7"):
            # S17 | S18 | S30 | S31
            next_states |= 3221618688

        # 51:166
        # S17
        if 131072 & current_states and (not (char == "]" or "\000" <= char <= "\037" or char in "\\\177-")):
            # S17 | S18 | S23 | S30 | S31
            next_states |= 3230007296

        # 51:189
        # S18
        if 262144 & current_states and (char == "\\"):
            # S19 | S20
            next_states |= 1572864

        # 51:193
        # S19
        if 524288 & current_states and (char in "\\abfnrtv"):
            # S17 | S18 | S23 | S30 | S31
            next_states |= 3230007296

        # 51:207
        # S20
        if 1048576 & current_states and (char in "01"):
            # S21
            next_states |= 2097152

        # 51:212:1
        # S21
        if 2097152 & current_states and ("0" <= char <= "7"):
            # S22
            next_states |= 4194304

        # 51:212:2
        # S22
        if 4194304 & current_states and ("0" <= char <= "7"):
            # S17 | S18 | S23 | S30 | S31
            next_states |= 3230007296

        # 51:224
        # S23
        if 8388608 & current_states and (char == "-"):
            # S24 | S25
            next_states |= 50331648

        # 51:227
        # S24
        if 16777216 & current_states and (not (char == "]" or "\000" <= char <= "\037" or char in "\\\177")):
            # S17 | S18 | S30 | S31
            next_states |= 3221618688

        # 51:249
        # S25
        if 33554432 & current_states and (char == "\\"):
            # S26 | S27
            next_states |= 201326592

        # 51:253
        # S26
        if 67108864 & current_states and (char in "\\abfnrtv"):
            # S17 | S18 | S30 | S31
            next_states |= 3221618688

        # 51:267
        # S27
        if 134217728 & current_states and (char in "01"):
            # S28
            next_states |= 268435456

        # 51:272:1
        # S28
        if 268435456 & current_states and ("0" <= char <= "7"):
            # S29
            next_states |= 536870912

        # 51:272:2
        # S29
        if 536870912 & current_states and ("0" <= char <= "7"):
            # S17 | S18 | S30 | S31
            next_states |= 3221618688

        # 51:287
        # S30
        if 1073741824 & current_states and (char == "-"):
            # S31
            next_states |= 2147483648

        # 51:290
        # S31
        if 2147483648 & current_states and (char == "]"):
            state_accept = True

        return (state_accept, next_states)


class ExclamationMark(TransmuterTerminalTag):
    @staticmethod
    def positives(conditions: TransmuterConditions) -> set[type[TransmuterTerminalTag]]:
        positives = {OrdChar}
        return positives

    @staticmethod
    def nfa(current_states: TransmuterLexingState, char: str) -> tuple[bool, TransmuterLexingState]:
        state_accept = False
        next_states = 0

        # 53:28
        if char == "!":
            state_accept = True

        return (state_accept, next_states)


class LeftSquareBracket(TransmuterTerminalTag):
    @staticmethod
    def start(conditions: TransmuterConditions) -> bool:
        return Conditions.syntactic in conditions

    @staticmethod
    def nfa(current_states: TransmuterLexingState, char: str) -> tuple[bool, TransmuterLexingState]:
        state_accept = False
        next_states = 0

        # 55:30
        if char == "[":
            state_accept = True

        return (state_accept, next_states)


class LeftSquareBracketSolidus(TransmuterTerminalTag):
    @staticmethod
    def start(conditions: TransmuterConditions) -> bool:
        return Conditions.syntactic in conditions

    @staticmethod
    def nfa(current_states: TransmuterLexingState, char: str) -> tuple[bool, TransmuterLexingState]:
        state_accept = False
        next_states = 0

        # 57:37
        # S0
        if 1 & current_states and (char == "["):
            # S1
            next_states |= 2

        # 57:40
        # S1
        if 2 & current_states and (char == "/"):
            state_accept = True

        return (state_accept, next_states)


class RightSquareBracket(TransmuterTerminalTag):
    @staticmethod
    def start(conditions: TransmuterConditions) -> bool:
        return Conditions.syntactic in conditions

    @staticmethod
    def nfa(current_states: TransmuterLexingState, char: str) -> tuple[bool, TransmuterLexingState]:
        state_accept = False
        next_states = 0

        # 59:31
        if char == "]":
            state_accept = True

        return (state_accept, next_states)


class Lexer(TransmuterLexer):
    TERMINAL_TAGS = [Whitespace, Identifier, Colon, Semicolon, CommercialAt, LeftParenthesis, RightParenthesis, VerticalLine, Solidus, DoubleVerticalLine, Comma, DoubleAmpersand, PlusSign, HyphenMinus, Ignore, Start, Asterisk, QuestionMark, ExpressionRange, LeftCurlyBracket, LeftCurlyBracketSolidus, RightCurlyBracket, OrdChar, QuotedChar, FullStop, BracketExpression, ExclamationMark, LeftSquareBracket, LeftSquareBracketSolidus, RightSquareBracket]
