"""Parse the catalog's explicit license-policy subset without rewriting source metadata."""

import re
from dataclasses import dataclass
from functools import lru_cache

# Recognition is not proof of compliance. Item.blockers keeps the contextual
# permission, source, review, and official-document restrictions separate.
SUPPORTED_LICENSES = frozenset(
    {
        "CC-BY-4.0",
        "CC-BY-SA-4.0",
        "CC-BY-SA-3.0",
        "CC0-1.0",
        "OFL-1.1",
        "MIT",
        "ISC",
        "Apache-2.0",
        "BSD-2-Clause",
        "BSD-3-Clause",
        "GPL-3.0-only",
        "GPL-3.0-or-later",
        "GPL-2.0-only",
        "GPL-2.0-or-later",
        "OLDAP-2.8",
        "ODbL-1.0",
        "US-PD",
        "Public-domain-US",
        "LicenseRef-FEMA-Ready-Reprint",
        "CC-BY-NC-SA-3.0",
        "Unlicense",
        "Zlib",
        "Unicode-3.0",
        "MPL-2.0",
        "LGPL-3.0-only",
        "LGPL-3.0-or-later",
    }
)
CANONICAL_IDS = {identifier.casefold(): identifier for identifier in SUPPORTED_LICENSES}
SUPPORTED_EXCEPTIONS = frozenset({("Apache-2.0", "Swift-exception")})
CANONICAL_EXCEPTIONS = {exception.casefold(): exception for _, exception in SUPPORTED_EXCEPTIONS}
IDENTIFIER = re.compile(r"[A-Za-z0-9][A-Za-z0-9.-]*\+?")
TOKEN = re.compile(r"\s+|[()/]|[A-Za-z0-9][A-Za-z0-9.-]*\+?")
OPERATORS = {"AND", "OR", "WITH"}


@dataclass(frozen=True)
class LicenseExpression:
    supported: bool
    identifiers: frozenset[str]

    @property
    def requires_source(self) -> bool:
        """Keep source obligations conservative across every mentioned alternative."""
        return any(
            identifier.upper().startswith(("GPL-", "LGPL-", "MPL-"))
            for identifier in self.identifiers
        )


class Parser:
    def __init__(self, value: str):
        self.tokens = []
        position = 0
        for match in TOKEN.finditer(value):
            if match.start() != position:
                raise ValueError("Unsupported license-expression syntax")
            position = match.end()
            token = match.group()
            if not token.isspace():
                self.tokens.append(token)
        if position != len(value) or not self.tokens or len(self.tokens) > 512:
            raise ValueError("Empty, unsupported, or oversized license expression")
        self.position = 0

    def take(self, *values: str) -> bool:
        if self.position < len(self.tokens) and self.tokens[self.position] in values:
            self.position += 1
            return True
        return False

    def identifier(self, *, exception: bool = False) -> str:
        if self.position == len(self.tokens):
            raise ValueError("Missing license-expression operand")
        token = self.tokens[self.position]
        if token in OPERATORS or not IDENTIFIER.fullmatch(token) or (exception and "+" in token):
            raise ValueError("Expected a license or exception identifier")
        self.position += 1
        identifiers = CANONICAL_EXCEPTIONS if exception else CANONICAL_IDS
        return identifiers.get(token.casefold(), token)

    def primary(self, depth: int) -> LicenseExpression:
        if depth > 64:
            raise ValueError("License-expression nesting is too deep")
        if self.take("("):
            value = self.disjunction(depth + 1)
            if not self.take(")"):
                raise ValueError("Unmatched license-expression parentheses")
            return value
        identifier = self.identifier()
        supported = identifier in SUPPORTED_LICENSES
        if self.take("WITH"):
            exception = self.identifier(exception=True)
            # Recognition applies to the exact license/exception pair only;
            # contextual notice, source, and human-review gates remain separate.
            supported = supported and (identifier, exception) in SUPPORTED_EXCEPTIONS
        return LicenseExpression(supported, frozenset({identifier}))

    def conjunction(self, depth: int) -> LicenseExpression:
        value = self.primary(depth)
        while self.take("AND"):
            other = self.primary(depth)
            value = LicenseExpression(
                value.supported and other.supported, value.identifiers | other.identifiers
            )
        return value

    def disjunction(self, depth: int = 0) -> LicenseExpression:
        value = self.conjunction(depth)
        # Cargo's deprecated slash syntax is parsed as OR, never written back.
        while self.take("OR", "/"):
            other = self.conjunction(depth)
            value = LicenseExpression(
                value.supported or other.supported, value.identifiers | other.identifiers
            )
        return value


@lru_cache(maxsize=512)
def parse_license_expression(value: str) -> LicenseExpression:
    """Require complete syntax, evaluate known alternatives, and retain all license IDs."""
    if len(value) > 4096:
        raise ValueError("License expression is too long")
    parser = Parser(value)
    result = parser.disjunction()
    if parser.position != len(parser.tokens):
        raise ValueError("Unexpected license-expression token")
    return result
