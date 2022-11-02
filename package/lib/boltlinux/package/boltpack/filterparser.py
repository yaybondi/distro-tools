# -*- encoding: utf-8 -*-
#
# The MIT License (MIT)
#
# Copyright (c) 2016-2018 Tobias Koch <tobias.koch@gmail.com>
#
# Permission is hereby granted, free of charge, to any person obtaining a copy
# of this software and associated documentation files (the "Software"), to deal
# in the Software without restriction, including without limitation the rights
# to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
# copies of the Software, and to permit persons to whom the Software is
# furnished to do so, subject to the following conditions:
#
# The above copyright notice and this permission notice shall be included in
# all copies or substantial portions of the Software.
#
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
# IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
# FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
# AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
# LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
# OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN
# THE SOFTWARE.
#

import re
import sys
import textwrap

from typing import List

class FilterParser:

    NEXT_TOKEN = 0
    TOKEN_TYPE = 0

    class Error(Exception):
        pass

    class SyntaxError(Error):
        pass

    def __init__(self, true_terms: List[str]):
        token_dict = {
            "open":
                re.escape("("),
            "close":
                re.escape(")"),
            "word":
                r"[a-z][-0-9a-z_]*",
            "not":
                re.escape("!"),
            "whitespace":
                r"\s+",
            "unknown":
                r".+?"
        }

        parts = []

        for token_type, token_regex in token_dict.items():
            parts.append(r"(?P<{}>{})".format(token_type, token_regex))

        self.regex = re.compile(r"|".join(parts))

        self.symbols = {
            "true":
                True,
            "false":
                False
        }

        for term in true_terms:
            self.symbols[term] = True
    #end function

    def tokenize(self, expr):
        tokens = []

        for match in self.regex.finditer(expr):
            token_type, token, token_start = (
                match.lastgroup, match.group(), match.start() + 1
            )

            if token_type == "whitespace":
                continue
            elif token_type == "word" and token in ("and", "or"):
                token_type = token
            elif token_type == "unknown":
                raise FilterParser.SyntaxError(
                    'invalid token "{}" at position {}.'
                    .format(token, token_start)
                )
            #end if

            tokens.append(
                (token_type, token, token_start)
            )
        #end for

        return tokens
    #end function

    def parse(self, expr):
        result = self._p_expr(self.tokenize(expr))
        if result is None:
            return True
        return result
    #end function

    # PARSER IMPLEMENTATION

    def _p_expr(self, tokens, lvl=0, short_cut=False):
        if lvl > 64:
            raise FilterParser.Error(
                "expression generates too many levels of recursion."
            )
        #end if

        result = None

        while tokens:
            typ, tok, pos = tokens[0]

            if typ == "not":
                tokens.pop(FilterParser.NEXT_TOKEN)

                if result is not None:
                    raise FilterParser.SyntaxError(
                        "syntax error at position {}".format(pos)
                    )

                expr_val = self._p_expr(tokens, lvl+1, short_cut=True)

                if expr_val is None:
                    raise FilterParser.SyntaxError(
                        "operator '!' requires an operand at position {}"
                        .format(pos)
                    )

                result = not expr_val
                if short_cut:
                    break
            elif typ == "and":
                tokens.pop(FilterParser.NEXT_TOKEN)

                if result is None:
                    raise FilterParser.SyntaxError(
                        'operator "and" at position {} is missing its left hand operand'  # noqa
                        .format(pos)
                    )

                expr_val = self._p_expr(tokens, lvl+1, short_cut=True)

                if expr_val is None:
                    raise FilterParser.SyntaxError(
                        'operator "and" at position {} is missing its right hand operand'  # noqa
                        .format(pos)
                    )

                result = result and expr_val
            elif typ == "or":
                tokens.pop(FilterParser.NEXT_TOKEN)

                if result is None:
                    raise FilterParser.SyntaxError(
                        'operator "or" at position {} is missing its left hand operand'  # noqa
                        .format(pos)
                    )

                expr_val = self._p_expr(tokens, lvl+1)

                if expr_val is None:
                    raise FilterParser.SyntaxError(
                        'operator "or" at position {} is missing its right hand operand'  # noqa
                        .format(pos)
                    )

                result = result or expr_val
            elif typ == "word":
                tokens.pop(FilterParser.NEXT_TOKEN)

                if result is not None:
                    raise FilterParser.SyntaxError(
                        "syntax error at position {}".format(pos)
                    )

                result = self.symbols.get(tok, False)
                if short_cut:
                    break
            elif typ == "open":
                tokens.pop(FilterParser.NEXT_TOKEN)

                if result is not None:
                    raise FilterParser.SyntaxError(
                        "syntax error at position {}".format(pos)
                    )

                expr_val = self._p_expr(tokens, lvl+1)

                if not tokens or tokens[FilterParser.NEXT_TOKEN] \
                        [FilterParser.TOKEN_TYPE] != "close":  # noqa
                    raise FilterParser.SyntaxError(
                        'missing closing parenthesis for parenthesis at position {}'  # noqa
                        .format(pos)
                    )

                tokens.pop(FilterParser.NEXT_TOKEN)

                result = expr_val
                if short_cut:
                    break
            elif typ == "close":
                if lvl == 0:
                    raise FilterParser.SyntaxError(
                        'missing opening parenthesis for parenthesis at position {}'  # noqa
                        .format(pos)
                    )
                # Pop happens one level up.
                break
        #end while

        # Ensure that all tokens have been processed.
        if lvl == 0:
            assert not tokens

        return result
    #end function

    # TEST

    @staticmethod
    def _test():
        parser = FilterParser(true_terms=["aarch64", "musl", "cross-tools"])

        tests = [
            {
                "description":
                    "Test that a True symbol is True.",
                "expression":
                    "aarch64",
                "expected":
                    True
            },
            {
                "description":
                    "Test that a False symbol is False.",
                "expression":
                    "s390x",
                "expected":
                    False
            },
            {
                "description":
                    "Test that a negated True symbol is False.",
                "expression":
                    "!aarch64",
                "expected":
                    False
            },
            {
                "description":
                    "Test that a negated False symbol is True.",
                "expression":
                    "!s390x",
                "expected":
                    True
            },
            {
                "description":
                    "Test that a negated True symbol is False.",
                "expression":
                    "!aarch64",
                "expected":
                    False
            },
            {
                "description":
                    "Test that double-negation works correctly.",
                "expression":
                    "!!aarch64",
                "expected":
                    True
            },
            {
                "description":
                    "Test that True and False are False.",
                "expression":
                    "aarch64 and !aarch64",
                "expected":
                    False
            },
            {
                "description":
                    "Test and/or operator precedence (1).",
                "expression":
                    "aarch64 or musl and s390x",
                "expected":
                    True
            },
            {
                "description":
                    "Test and/or operator precedence (2).",
                "expression":
                    "s390x and aarch64 or musl",
                "expected":
                    True
            },
            {
                "description":
                    "Test parenthesis overriding and/or precedence (1).",
                "expression":
                    "(aarch64 or musl) and s390x",
                "expected":
                    False
            },
            {
                "description":
                    "Test parenthesis overriding and/or precedence (2).",
                "expression":
                    "s390x and (aarch64 or musl)",
                "expected":
                    False
            },
            {
                "description":
                    "Test syntax error misplaced not.",
                "expression":
                    "s390x !aarch64",
                "expected":
                    """syntax error at position 7"""
            },
            {
                "description":
                    "Test syntax error misplaced symbol.",
                "expression":
                    "s390x aarch64",
                "expected":
                    """syntax error at position 7"""
            },
            {
                "description":
                    "Test syntax error not without operand.",
                "expression":
                    "s390x and !",
                "expected":
                    """operator '!' requires an operand at position 11"""
            },
            {
                "description":
                    "Test syntax error and without left-hand operand. (1)",
                "expression":
                    "s390x or !and",
                "expected":
                    """operator "and" at position 11 is missing its left hand operand"""  # noqa
            },
            {
                "description":
                    "Test syntax error and without left-hand operand. (2)",
                "expression":
                    "s390x or and !aarch64",
                "expected":
                    """operator "and" at position 10 is missing its left hand operand"""  # noqa
            },
            {
                "description":
                    "Test syntax error and without left-hand operand. (3)",
                "expression":
                    "and",
                "expected":
                    """operator "and" at position 1 is missing its left hand operand"""  # noqa
            },
            {
                "description":
                    "Test syntax error or without left-hand operand. (1)",
                "expression":
                    "s390x and !or",
                "expected":
                    """operator "or" at position 12 is missing its left hand operand"""  # noqa
            },
            {
                "description":
                    "Test syntax error or without left-hand operand. (2)",
                "expression":
                    "s390x and or !aarch64",
                "expected":
                    """operator "or" at position 11 is missing its left hand operand"""  # noqa
            },
            {
                "description":
                    "Test syntax error or without left-hand operand. (3)",
                "expression":
                    "or",
                "expected":
                    """operator "or" at position 1 is missing its left hand operand"""  # noqa
            },
            {
                "description":
                    "Test syntax error and without right-hand operand. (1)",
                "expression":
                    "s390x and",
                "expected":
                    """operator "and" at position 7 is missing its right hand operand"""  # noqa
            },
            {
                "description":
                    "Test syntax error and without right-hand operand. (2)",
                "expression":
                    "s390x and ()",
                "expected":
                    """operator "and" at position 7 is missing its right hand operand"""  # noqa
            },
            {
                "description":
                    "Test syntax error or without right-hand operand. (1)",
                "expression":
                    "s390x or",
                "expected":
                    """operator "or" at position 7 is missing its right hand operand"""  # noqa
            },
            {
                "description":
                    "Test syntax error or without right-hand operand. (2)",
                "expression":
                    "s390x or ()",
                "expected":
                    """operator "or" at position 7 is missing its right hand operand"""  # noqa
            },
            {
                "description":
                    "Test syntax error missing closing parenthesis.",
                "expression":
                    "(()()",
                "expected":
                    """missing closing parenthesis for parenthesis at position 1"""  # noqa
            },
            {
                "description":
                    "Test syntax error missing opening parenthesis.",
                "expression":
                    ")",
                "expected":
                    """missing opening parenthesis for parenthesis at position 1"""  # noqa
            },
            {
                "description":
                    "Test syntax error misplaced parenthesis.",
                "expression":
                    "aarch64 ()",
                "expected":
                    """syntax error at position 9"""
            },
            {
                "description":
                    "Test true is True.",
                "expression":
                    "true",
                "expected":
                    True
            },
            {
                "description":
                    "Test false is False.",
                "expression":
                    "false",
                "expected":
                    False
            },
            {
                "description":
                    "Test 'cross-tools' is a valid identifier.",
                "expression":
                    "cross-tools",
                "expected":
                    True
            },
        ]

        success = True

        for testcase in tests:
            description     = testcase["description"]
            expression      = testcase["expression"]
            expected_result = testcase["expected"]

            print(textwrap.dedent(
                """\
                ================================================
                {}
                ================================================
                {} = {}
                """
                .format(description, expression, expected_result)
            ))

            try:
                result = parser.parse(expression)
            except FilterParser.Error as e:
                result = str(e)

            if result == expected_result:
                print("OK\n")
            else:
                print(textwrap.dedent(
                    """
                    FAILED

                    Expected result:
                        {}
                    Actual result:
                        {}
                    """
                    .format(expected_result, result)
                ))

                success = False
                break
            #end if
        #end for

        for sym in parser.symbols.keys():
            try:
                parser.parse(sym)
            except FilterParser.Error:
                print("Symbol {} wasn't parsed correctly.".format(sym))
                success = False

        return success
    #end function

#end class


if __name__ == "__main__":
    if FilterParser._test() is True:
        sys.exit(0)
    else:
        sys.exit(1)
