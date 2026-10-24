"""
Regex patterns for parsing mdrag document components.
Includes URI, coordinate, and header-based identity patterns.
"""

import re

# URI Pattern: domain.sub/resource-v1
URI_PATTERN = re.compile(r"^[a-z0-9.]+\/[a-z0-9-]+$")

# Header e.g. "uri: sci.bio/levin-v1" at the top of the file
# Removed strict $ anchor to allow following content
URI_HEADER_PATTERN = re.compile(r"^uri:\s+([a-z0-9][a-z0-9.]*/[a-z0-9][a-z0-9-]*)\s*")

# Coordinate e.g. "{:sci.bio/levin-v1.section.1}"
COORDINATE_PATTERN = re.compile(r"\{:([a-z0-9][a-z0-9./-]*)\}")

# Metadata Header Patterns
URI_HEADER_PATTERN = re.compile(r"^uri:\s*([^\n]+)\n+")
