"""Named regular expression patterns and validation constants.

All regex patterns are compiled once as top-level constants.
No inline regex strings are permitted inside model definitions or schemas.
"""

from __future__ import annotations

import re

# Namespace, token, and identifier segments: lowercase letters, digits, underscores
IDENTIFIER_PATTERN_STR = r"^[a-z0-9_]+$"
IDENTIFIER_RE = re.compile(IDENTIFIER_PATTERN_STR)

# CTS URN: urn:cts:<namespace>:<work_hierarchy>:<passage_component>
CTS_URN_PATTERN_STR = r"^urn:cts:[a-z0-9_]+:[a-z0-9_.]+(:\S+)?$"
CTS_URN_RE = re.compile(CTS_URN_PATTERN_STR)

# CITE-2 URN: urn:cite2:<namespace>:<collection>.<object>:<subreference>
CITE2_URN_PATTERN_STR = r"^urn:cite2:[a-z0-9_]+:[a-z0-9_.]+(:\S+)?(#\S+)?$"
CITE2_URN_RE = re.compile(CITE2_URN_PATTERN_STR)

# SHA-256 hex digest
SHA256_HEX_STR = r"^[a-f0-9]{64}$"
SHA256_HEX_RE = re.compile(SHA256_HEX_STR)

# DOI prefix: 10.xxxx/...
DOI_PREFIX_RE = re.compile(r"^10\.\d{4,9}/[-._;()/:A-Za-z0-9]+$")

# Wikidata entity: Q followed by digits
WIKIDATA_ID_RE = re.compile(r"^Q\d+$")
