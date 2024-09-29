#!/usr/bin/env python
#
# Copyright (c) 2022, Alkemy Spa
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#    https://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

import base64
import struct
import zlib
from dataclasses import dataclass
from typing import Dict, List

import sqlparse
from sqlparse.sql import (
    Comment,
    Comparison,
    Function,
    Identifier,
    IdentifierList,
    Operation,
    Parenthesis,
    Statement,
    Where,
)
from sqlparse.tokens import Token

from dbt.adapters.sas.constants import DUMMY_FROM

__all__ = ["prepare_query", "Query"]

# Remove FINAL from the keyword list
try:
    del sqlparse.keywords.KEYWORDS['FINAL']
except:
    pass


@dataclass
class Query:
    pre: str
    post: str
    query: str
    ctes: Dict[str, str]  # CTEs  identifier => view name


def get_identifier(token: Token) -> str:
    if isinstance(token, Function):
        token = token[0]
    return str(token)


def is_whitespace(token: Token) -> bool:
    "Check if token is a whitespace"
    return token.ttype in [Token.Text.Whitespace, Token.Text.Whitespace.Newline]


def get_token_skip_whitespace(tokens: List["Token"]) -> Token:
    "Get the next whitespace token from tokens"
    return pop_token_skip_whitespace(list(tokens))


def pop_token_skip_whitespace(tokens: List["Token"]) -> Token:
    "Pop the next whitespace token from tokens (remote the element from tokens)"
    while tokens:
        token = tokens.pop(0)
        if not is_whitespace(token):
            return token
    return None


def process_cte_definition(token: Identifier, pre: List[str], post: List[str], ctes: Dict[str, str], cte_schema: str) -> None:
    # print('>>>', token, type(token), token.ttype)
    tokens = list(token.tokens)
    # Get identifier
    token = pop_token_skip_whitespace(tokens)
    identifier = get_identifier(token)
    # Check 'AS' keyword
    token = pop_token_skip_whitespace(tokens)
    if token.ttype != Token.Keyword or token.value.upper() != "AS":
        raise Exception(f"Unexpected token {token} (`AS` expected)")
    # Get definition
    token = pop_token_skip_whitespace(tokens)
    if not isinstance(token, Parenthesis):
        raise Exception(f"Unexpected token {token} (parenthesis expected)")
    cte_query = []
    process_parenthesis(token, pre, post, cte_query, ctes, insert_schema=False, cte_schema=cte_schema)
    query = "".join(cte_query)

    crc = zlib.crc32(query.encode('utf-8'))
    encoded_crc = base64.b32encode(struct.pack('I', crc)).decode('ascii').strip('=')[:7]
    view_identifier = f"{cte_schema}.{identifier}_{encoded_crc}"
    ctes[identifier.lower()] = view_identifier

    pre.append(f"create view {view_identifier} as {query};")
    post.append(f"drop view {view_identifier};")


def process_cte(statement: Statement, pre: List[str], post: List[str], ctes: Dict[str, str], cte_schema: str) -> None:
    token = pop_token_skip_whitespace(statement)
    if isinstance(token, IdentifierList):  # Multiple CTE
        with_tokens = list(token.tokens)
        while with_tokens:
            with_token = pop_token_skip_whitespace(with_tokens)
            if with_token.ttype != Token.Punctuation:
                process_cte_definition(with_token, pre, post, ctes, cte_schema)
    elif isinstance(token, Identifier):  # Single CTE
        process_cte_definition(token, pre, post, ctes, cte_schema)
    else:
        raise Exception(f"Unexpected token {token}")


def process_parenthesis(
    parenthesis: Parenthesis,
    pre: List[str],
    post: List[str],
    query: List[str],
    ctes: Dict[str, str],
    insert_schema: bool,
    cte_schema: str,
) -> None:
    p_tokens = parenthesis.tokens
    assert p_tokens[0].value == "("
    assert p_tokens[-1].value == ")"
    query.append("(")
    process_tokens(p_tokens[1:-1], pre, post, query, ctes, insert_schema=insert_schema, cte_schema=cte_schema)
    query.append(")")


def get_arg(parenthesis: Parenthesis, n: int) -> Token:
    "Get the n argument from a parenthesis"
    if not isinstance(parenthesis, Parenthesis):
        raise Exception(f"Unexpected token {parenthesis} (`(` expected)")
    parenthesis_tokens = list(parenthesis.tokens[1:-1])
    token = pop_token_skip_whitespace(parenthesis_tokens)
    if isinstance(token, IdentifierList):
        tokens = list(token.tokens)
        while tokens:
            arg = pop_token_skip_whitespace(tokens)
            if not arg:
                return None
            elif arg.ttype == Token.Punctuation:
                pass
            elif n == 1:
                return arg
            else:
                n = n - 1
        return None
    elif n == 1:
        return token
    else:
        return None


def process_function(
    function: Function,
    pre: List[str],
    post: List[str],
    query: List[str],
    ctes: Dict[str, str],
    insert_schema: bool,
    cte_schema: str,
) -> None:
    function_name = function.tokens[0].value.upper()
    function_tokens = list(function.tokens[1:])
    parenthesis = pop_token_skip_whitespace(function_tokens)
    if function_name == "CAST":
        arg1 = get_arg(parenthesis, 1)
        if arg1 is None:
            raise Exception("CAST argument expected")
        query.append(str(arg1.tokens[0]))
    elif function_name == "NULLIF":
        arg1 = get_arg(parenthesis, 1)
        arg2 = get_arg(parenthesis, 2)
        query.append(f"case when {arg1} = {arg2} then . else {arg1} end")
    else:
        query.append(function_name.lower())
        process_parenthesis(parenthesis, pre, post, query, ctes, insert_schema=insert_schema, cte_schema=cte_schema)


def process_identifier(
    identifier: Identifier,
    pre: List[str],
    post: List[str],
    query: List[str],
    ctes: Dict[str, str],
    insert_schema: bool,
    cte_schema: str,
) -> None:
    i_tokens = identifier.tokens
    has_schema = False
    while i_tokens:
        token = i_tokens.pop(0)
        if isinstance(token, Parenthesis):
            process_parenthesis(token, pre, post, query, ctes, insert_schema=False, cte_schema=cte_schema)
            has_schema = False
        elif isinstance(token, Function):
            process_function(token, pre, post, query, ctes, insert_schema=False, cte_schema=cte_schema)
        elif isinstance(token, Operation):
            process_tokens(list(token.tokens), pre, post, query, ctes, insert_schema=True, cte_schema=cte_schema)
        elif token.ttype == Token.Punctuation and token.value == ",":
            has_schema = False
            query.append(str(token))
        elif token.ttype == Token.Punctuation and token.value == ".":
            has_schema = True
            query.append(str(token))
        elif isinstance(token, Comment):
            pass  # skip comments
        else:
            identifier = str(token)
            # print('>>>', token, type(token), token.ttype)
            if insert_schema and identifier.lower() in ctes and not has_schema:
                next_token = get_token_skip_whitespace(i_tokens)
                if next_token and next_token.value.upper() == "AS":
                    identifier = ctes[identifier.lower()]  # don't add the alias (already present)
                elif next_token and isinstance(next_token, Identifier):
                    identifier = ctes[identifier.lower()]  # don't add the alias (already present)
                else:
                    identifier = ctes[identifier.lower()] + " as " + identifier.lower()
            query.append(identifier)
            has_schema = False


def process_from(
    statement: Statement, pre: List[str], post: List[str], query: List[str], ctes: Dict[str, str], cte_schema: str
) -> None:
    while statement:
        token = statement.pop(0)
        if isinstance(token, Identifier):
            process_identifier(token, pre, post, query, ctes, insert_schema=True, cte_schema=cte_schema)
        elif isinstance(token, IdentifierList):
            id_tokens = list(token.tokens)
            while id_tokens:
                id_token = id_tokens.pop(0)
                if id_token.ttype == Token.Punctuation:
                    query.append(str(id_token))
                elif isinstance(id_token, Identifier):
                    process_identifier(id_token, pre, post, query, ctes, insert_schema=True, cte_schema=cte_schema)
                elif isinstance(id_token, Function):
                    process_function(id_token, pre, post, query, ctes, insert_schema=False, cte_schema=cte_schema)
                else:
                    query.append(str(id_token))
        elif isinstance(token, Function):
            process_function(token, pre, post, query, ctes, insert_schema=False, cte_schema=cte_schema)
        elif isinstance(token, Parenthesis):
            process_parenthesis(token, pre, post, query, ctes, insert_schema=True, cte_schema=cte_schema)
        elif isinstance(token, Where):
            process_tokens(list(token.tokens), pre, post, query, ctes, insert_schema=False, cte_schema=cte_schema)
        elif isinstance(token, Comment):
            pass  # skip comments
        else:
            query.append(str(token))


def process_tokens(
    tokens: List["Token"],
    pre: List[str],
    post: List[str],
    query: List[str],
    ctes: Dict[str, str],
    insert_schema: bool,
    cte_schema: str,
) -> None:
    is_a_select: bool = False
    has_from: bool = False
    while tokens:
        token = tokens.pop(0)
        # if token.ttype != Token.Text.Whitespace and token.ttype != Token.Text.Whitespace.Newline:
        #     print('>>>', token, type(token), token.ttype)
        if token.ttype == Token.Keyword.DML and str(token).upper() == "SELECT":
            is_a_select = True
            query.append(str(token))
        elif token.ttype == Token.Keyword.CTE:
            process_cte(tokens, pre, post, ctes, cte_schema)
        elif token.ttype == Token.Operator.Comparison and token.value == "!=":
            query.append("<>")
        elif token.ttype == Token.Keyword and token.value.upper() == "TRUE":
            query.append("1")
        elif token.ttype == Token.Keyword and token.value.upper() == "FALSE":
            query.append("0")
        elif token.ttype == Token.Keyword and token.value.upper().split(" ")[0] == "UNION":
            if is_a_select and not has_from:
                query.append(DUMMY_FROM)
                has_from = False
            query.append(str(token))
        elif token.ttype == Token.Keyword and token.value.upper() == "FROM":
            query.append(str(token))
            query.append(" ")
            has_from = True
            process_from(tokens, pre, post, query, ctes, cte_schema)
        elif isinstance(token, Identifier):
            process_identifier(token, pre, post, query, ctes, insert_schema, cte_schema)
        elif isinstance(token, IdentifierList):
            process_tokens(list(token.tokens), pre, post, query, ctes, insert_schema, cte_schema)
        elif isinstance(token, Operation):
            process_tokens(list(token.tokens), pre, post, query, ctes, insert_schema, cte_schema)
        elif isinstance(token, Comparison):
            process_tokens(list(token.tokens), pre, post, query, ctes, insert_schema, cte_schema)
        elif isinstance(token, Parenthesis):
            process_tokens(list(token.tokens), pre, post, query, ctes, insert_schema, cte_schema)
        elif isinstance(token, Function):
            process_function(token, pre, post, query, ctes, insert_schema=False, cte_schema=cte_schema)
        elif isinstance(token, Comment):
            pass  # skip comments
        else:
            query.append(str(token))
    if is_a_select and not has_from:
        query.append(DUMMY_FROM)


def prepare_query(sql: str, cte_schema: str) -> Query:
    pre: List[str] = []
    post: List[str] = []
    query: List[str] = []
    ctes: Dict[str, str] = {}  # identifier => view name
    for statement in sqlparse.parse(sql):
        process_tokens(list(statement.tokens), pre, post, query, ctes, insert_schema=False, cte_schema=cte_schema)
    # If the query is a "CREATE VIEW" using a CTEs, don't delete the CTEs
    keep_ctes = pre and "".join(query).upper().strip().startswith("CREATE VIEW")
    if keep_ctes:
        post = []
    return Query(
        pre="\n".join(pre),
        post="\n".join(post),
        query="".join(query),
        ctes=ctes,
    )
