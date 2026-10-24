"""Block schema registry — the axiomatic layer of the mdrag system.

A BlockSchema is an axiom: it defines what attrs a block type carries,
which are required, and what a valid instance looks like. The
BlockSchemaRegistry is the axiomatic system: additive, never breaking,
queryable by type string or namespace.

The validator derives conformance from the axioms.
The generator proves the axioms are productive by constructing valid instances.

Any sufficiently expressive schema system will encounter block types it
cannot yet express. That is incompleteness — built in deliberately via the
innovation bucket. The registry grows. The incompleteness recedes, never
to zero.
"""

from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, computed_field

from phosphene.mdrag.core import InvariantStatic
from phosphene.mdrag.models import Block

# ---------------------------------------------------------------------------
# AttrSpec
# ---------------------------------------------------------------------------


class AttrSpec(InvariantStatic):
    """Specification for a single block attribute.

    Attributes:
        type_name: The attribute's value type as a string
            (e.g. 'str', 'int', 'bool', 'list[str]').
        required: Whether the attribute must be present in a conforming block.
        description: Human-readable description of this attribute.
        constraints: Optional validation constraints, e.g.
            {'min': 1, 'max': 6} for int ranges,
            {'non_empty': True} for strings.
    """

    type_name: str
    required: bool = True
    description: str = ""
    constraints: dict[str, Any] = {}


# ---------------------------------------------------------------------------
# BlockSchema
# ---------------------------------------------------------------------------


class BlockSchema(InvariantStatic):
    """Schema (axiom) for a single block type.

    Attributes:
        type: Namespaced block type string, e.g. 'core/heading' or
            'sci.bio/thesis'. The namespace is the portion before the
            first '/'.
        attrs: Mapping of attribute name to its AttrSpec.
        description: Human-readable description of this block kind.
        example: A canonical attrs dict for this block type. Used by
            generate_example() to produce a valid Block instance.
        registered_by: Who registered this schema.
        registered_at: ISO date of registration.
    """

    type: str
    posture: Literal["F", "C", "O"] = "F"
    attrs: dict[str, AttrSpec] = {}
    description: str = ""
    example: dict[str, Any] = {}
    registered_by: str = "system"
    registered_at: str = ""

    @computed_field  # type: ignore[misc]
    @property
    def namespace(self) -> str:
        """The namespace portion of the type string (before the first '/')."""
        return self.type.split("/", 1)[0]

    def validate_block(self, block: Block) -> list[str]:
        """Validates a Block's attrs against this schema.

        Checks that all required attrs are present. Does not validate
        attr value types — that is reserved for a future constraint layer.

        Args:
            block: The Block to validate.

        Returns:
            A list of error strings. Empty means the block is valid.
        """
        errors: list[str] = []
        for attr_name, spec in self.attrs.items():
            if spec.required and attr_name not in block.attrs:
                errors.append(
                    f"Block type '{self.type}' missing required attr '{attr_name}'"
                )
        return errors

    def generate_example(self) -> Block:
        """Generates a canonical Block from this schema's example attrs.

        The example is declared in the schema and is guaranteed to be
        valid by construction — it is the schema author's responsibility
        to provide an example that passes validate_block().

        Returns:
            A Block with this schema's type and example attrs.
        """
        return Block(type=self.type, attrs=dict(self.example))


# ---------------------------------------------------------------------------
# BlockSchemaRegistry
# ---------------------------------------------------------------------------

# Bare type strings that resolve to core/ canonical form
_CORE_ALIASES: dict[str, str] = {
    "heading": "core/heading",
    "paragraph": "core/paragraph",
    "list": "core/list",
    "coordinate": "core/coordinate",
}


class BlockSchemaRegistry:
    """The axiomatic system: a global registry of block type schemas.

    Schemas are registered by type string and are retrievable by exact
    type or by namespace. Bare legacy type strings (e.g. 'heading') are
    resolved to their canonical core/ form.

    The registry is additive — schemas are never removed. New schemas
    extend the system without breaking existing ones.
    """

    def __init__(self) -> None:
        """Initialises an empty registry."""
        self._schemas: dict[str, BlockSchema] = {}

    def register(self, schema: BlockSchema) -> None:
        """Registers a BlockSchema under its type string.

        Args:
            schema: The BlockSchema to register.
        """
        self._schemas[schema.type] = schema

    def get(self, type_str: str) -> BlockSchema | None:
        """Returns the BlockSchema for a type string, or None if not registered.

        Bare type strings (e.g. 'heading') are resolved to their
        canonical core/ form before lookup.

        Args:
            type_str: The block type string, namespaced or bare.

        Returns:
            The registered BlockSchema, or None.
        """
        canonical = _CORE_ALIASES.get(type_str, type_str)
        return self._schemas.get(canonical)

    def validate_block(self, block: Block) -> list[str]:
        """Validates a Block against its registered schema.

        Args:
            block: The Block to validate.

        Returns:
            A list of error strings. Empty means the block is valid.
            Returns a 'not registered' error if the type has no schema.
        """
        schema = self.get(block.type)
        if schema is None:
            return [
                f"Block type '{block.type}' is not registered in the schema registry"
            ]
        return schema.validate_block(block)

    def all_types(self) -> list[str]:
        """Returns all registered type strings in registration order.

        Returns:
            List of namespaced type strings.
        """
        return list(self._schemas.keys())

    def types_for_namespace(self, namespace: str) -> list[str]:
        """Returns all registered type strings in a given namespace.

        Args:
            namespace: The namespace prefix, e.g. 'core' or 'sci.bio'.

        Returns:
            List of type strings whose namespace matches exactly.
        """
        return [t for t in self._schemas if self._schemas[t].namespace == namespace]


# ---------------------------------------------------------------------------
# core_registry factory
# ---------------------------------------------------------------------------


# ---------------------------------------------------------------------------
# Keyset extraction
# ---------------------------------------------------------------------------


def keyset_from_blocks(
    blocks: list[Block], registry: BlockSchemaRegistry
) -> frozenset[str]:
    """Extracts the file-level keyset from a list of blocks.

    The keyset contains only the type strings of Formal (F) and Conventional
    (C) blocks. Open (O) blocks are excluded — they are preserved in the file
    but do not contribute to the keyset index.

    Args:
        blocks: The list of Block objects from a parsed document.
        registry: The BlockSchemaRegistry to look up postures against.

    Returns:
        A frozenset of namespaced type strings for all F and C blocks present.
        Open-posture and unregistered block types are excluded.
    """
    keyset: set[str] = set()
    for block in blocks:
        schema = registry.get(block.type)
        if schema is not None and schema.posture in ("F", "C"):
            keyset.add(block.type)
    return frozenset(keyset)


# ---------------------------------------------------------------------------
# Fidelity levels
# ---------------------------------------------------------------------------

#: Ordered fidelity levels from least to most complete.
FIDELITY_LEVELS: tuple[str, ...] = ("parseable", "indexed", "structured", "complete")


# ---------------------------------------------------------------------------
# CompletenessResult
# ---------------------------------------------------------------------------


class CompletenessResult(BaseModel):
    """Result of a structural completeness check against a RuleEnvironment.

    Attributes:
        fidelity: The highest fidelity level the document achieves.
            One of: 'parseable', 'indexed', 'structured', 'complete'.
        rejected: Always False — documents are never rejected, only assessed.
        missing: The set of required block types that are absent.
        feedback: Human-readable message summarising the gaps, if any.
    """

    model_config = ConfigDict(frozen=True)

    fidelity: str
    rejected: bool = False
    missing: frozenset[str] = frozenset()
    feedback: str = ""


# ---------------------------------------------------------------------------
# RuleEnvironment
# ---------------------------------------------------------------------------


class RuleEnvironment(BaseModel):
    """Namespace-scoped structural completeness rules.

    A RuleEnvironment defines which block types are required for a document
    in a given namespace to be considered structurally complete. It never
    rejects documents — it assesses their fidelity level and provides
    actionable feedback.

    Attributes:
        namespace: The namespace this environment governs (e.g. 'paleo').
        required: Block types that must appear at least once for the document
            to reach 'complete' fidelity.
    """

    model_config = ConfigDict(frozen=True)

    namespace: str
    required: frozenset[str] = frozenset()

    def check_completeness(self, blocks: list[Block]) -> CompletenessResult:
        """Checks a document's blocks against the required set.

        A document with all required blocks is 'complete'. A document with
        some domain blocks but missing required ones is 'structured'. All
        documents are preserved — rejected is always False.

        Args:
            blocks: The list of Block objects from the document.

        Returns:
            A CompletenessResult with fidelity level, missing types,
            and human-readable feedback.
        """
        present_types = {b.type for b in blocks}
        missing = self.required - present_types

        if not missing:
            fidelity = "complete"
            feedback = ""
        else:
            # Document has some blocks but is missing required ones — structured
            fidelity = "structured"
            missing_list = ", ".join(sorted(missing))
            feedback = f"missing required block: {missing_list}"

        return CompletenessResult(
            fidelity=fidelity,
            rejected=False,
            missing=frozenset(missing),
            feedback=feedback,
        )


def build_registry_from_markdown(registries_dir: Path) -> BlockSchemaRegistry:  # type: ignore[name-defined]
    """Builds a BlockSchemaRegistry by reading markdown registry files.

    Reads ``index.md`` for namespace routing via phosphene.frontmatters,
    then reads each namespace file's frontmatter keyset and table body
    to construct BlockSchema objects.

    Starts from core_registry() and registers all namespaced formal schemas.

    Args:
        registries_dir: Path to the meta/registries/ directory.

    Returns:
        A fully populated BlockSchemaRegistry derived from the markdown source.
    """
    # Defer imports to avoid circular dependency at module load time
    from pathlib import Path as _Path

    from phosphene.frontmatters.frontmatter import read as _fm_read

    registries_dir = _Path(registries_dir)
    index_path = registries_dir / "index.md"
    index_result = _fm_read(index_path)
    namespaces: list[dict] = index_result.fields.get("namespaces", [])

    registry = core_registry()

    for ns_entry in namespaces:
        rel_path = ns_entry.get("path", "")
        file_path = registries_dir / rel_path
        if not file_path.exists():
            continue

        result = _fm_read(file_path)
        keys_list: list[str] = result.fields.get("keys", [])
        if not keys_list:
            continue

        rows = _parse_registry_table(result.body or "")
        rows_by_key = {r["key"]: r for r in rows}

        for key in keys_list:
            row = rows_by_key.get(key)
            if not row:
                continue
            import re

            attrs: dict[str, AttrSpec] = {}
            all_attrs = [(a, True) for a in row["required"]] + [
                (a, False) for a in row["optional"]
            ]

            for attr_name, is_req in all_attrs:
                escaped_key = re.escape(key)
                escaped_attr = re.escape(attr_name)
                enum_pattern = re.compile(
                    rf"`?{escaped_key}\.{escaped_attr}`?\s*[—\-]\s*one\s*of:\s*(.+)",
                    re.IGNORECASE,
                )
                list_pattern = re.compile(
                    rf"`?{escaped_key}\.{escaped_attr}`?\s*[—\-]\s*list\s*of\s*string",
                    re.IGNORECASE,
                )

                type_name = "str"
                constraints = {}

                for line in (result.body or "").splitlines():
                    enum_match = enum_pattern.search(line)
                    if enum_match:
                        values = [
                            v.strip().rstrip(".").strip("`").strip()
                            for v in enum_match.group(1).split(",")
                        ]
                        constraints["enum"] = values
                    if list_pattern.search(line):
                        type_name = "list[str]"

                attrs[attr_name] = AttrSpec(
                    type_name=type_name, required=is_req, constraints=constraints
                )

            example = {a: "example" for a in row["required"]}
            registry.register(
                BlockSchema(
                    type=key,
                    posture=row["posture"],
                    attrs=attrs,
                    example=example,
                    registered_at="2026-04-12",
                )
            )

    return registry


def _parse_registry_table(body: str) -> list[dict[str, Any]]:
    """Parses the formal block schema table from a registry file body.

    Extracts rows from the markdown table with columns:
    Key | P | Required | Optional.

    Args:
        body: The markdown body string from a registry namespace file.

    Returns:
        List of dicts with keys: key, posture, required (list), optional (list).
    """

    rows: list[dict[str, Any]] = []
    in_table = False
    header_found = False

    for line in body.splitlines():
        stripped = line.strip()

        if "| Key |" in stripped and "| P |" in stripped:
            header_found = True
            in_table = True
            continue

        if (
            in_table
            and set(stripped.replace("|", "").replace("-", "").replace(" ", ""))
            == set()
        ):
            continue

        if in_table and stripped.startswith("|") and header_found:
            if "| Key |" in stripped:
                break
            parts = [p.strip().strip("`") for p in stripped.split("|") if p.strip()]
            if len(parts) >= 3:
                key = parts[0]
                posture = parts[1]
                if posture not in ("F", "C"):
                    continue
                required_raw = parts[2] if len(parts) > 2 else ""
                optional_raw = parts[3] if len(parts) > 3 else ""
                rows.append(
                    {
                        "key": key,
                        "posture": posture,
                        "required": _parse_attr_cell(required_raw),
                        "optional": _parse_attr_cell(optional_raw),
                    }
                )
            else:
                in_table = False

    return rows


def _parse_attr_cell(raw: str) -> list[str]:
    """Parses a comma-separated attr name cell from a registry table row.

    Args:
        raw: The raw cell content, e.g. 'content, domain' or '—'.

    Returns:
        List of attr name strings. Empty list for '—' or empty input.
    """
    import re as _re

    raw = raw.strip().strip("`")
    if not raw or raw in ("—", "-", "–"):
        return []
    return [a.strip().strip("`") for a in _re.split(r",\s*", raw) if a.strip()]


def core_registry() -> BlockSchemaRegistry:
    """Returns a BlockSchemaRegistry pre-loaded with the four core axioms.

    The core axioms are the canonical schemas for the domain-neutral
    block types: heading, paragraph, list, coordinate.

    Returns:
        A BlockSchemaRegistry with core/heading, core/paragraph,
        core/list, and core/coordinate registered.
    """
    reg = BlockSchemaRegistry()

    reg.register(
        BlockSchema(
            type="core/heading",
            posture="C",
            attrs={
                "level": AttrSpec(
                    type_name="int",
                    description="Heading level, 1 (largest) to 6 (smallest).",
                    constraints={"min": 1, "max": 6},
                ),
                "text": AttrSpec(
                    type_name="str",
                    description="The heading text content.",
                    constraints={"non_empty": True},
                ),
            },
            description="A section heading with level and text.",
            example={"level": 1, "text": "Introduction"},
            registered_at="2026-04-08",
        )
    )

    reg.register(
        BlockSchema(
            type="core/paragraph",
            posture="O",
            attrs={
                "content": AttrSpec(
                    type_name="str",
                    description="The paragraph text content.",
                    constraints={"non_empty": True},
                ),
            },
            description="A prose paragraph block.",
            example={"content": "This is a paragraph."},
            registered_at="2026-04-08",
        )
    )

    reg.register(
        BlockSchema(
            type="core/list",
            posture="C",
            attrs={
                "ordered": AttrSpec(
                    type_name="bool",
                    description="True for ordered (numbered) lists, False for unordered.",
                ),
                "items": AttrSpec(
                    type_name="list[str]",
                    description="The list items as plain strings.",
                ),
            },
            description="A list block, ordered or unordered.",
            example={"ordered": False, "items": ["First item", "Second item"]},
            registered_at="2026-04-08",
        )
    )

    reg.register(
        BlockSchema(
            type="core/coordinate",
            posture="F",
            attrs={
                "value": AttrSpec(
                    type_name="str",
                    description="The coordinate address, e.g. 'sci.bio/levin-v1'.",
                    constraints={"non_empty": True},
                ),
            },
            description="A wiki coordinate reference block.",
            example={"value": "sci.bio/levin-v1"},
            registered_at="2026-04-08",
        )
    )

    # core/code — registered 2026-05-11 per SPEC_LOG [decision] Block Design Axiom.
    # Content in native form (the code itself). Language makes it interpretable.
    # Reasoning fields belong in domain-specific extensions (e.g. sci/model).
    reg.register(
        BlockSchema(
            type="core/code",
            posture="C",
            attrs={
                "content": AttrSpec(
                    type_name="str",
                    required=True,
                    description="The code content, preserved verbatim in its native form.",
                    constraints={"non_empty": True},
                ),
                "language": AttrSpec(
                    type_name="str",
                    required=False,
                    description=(
                        "Execution or interpretation context, e.g. 'python', 'bash', "
                        "'typescript'. Absent means language is unknown or irrelevant."
                    ),
                ),
                "label": AttrSpec(
                    type_name="str",
                    required=False,
                    description="Optional name for Hickey addressing of this block.",
                ),
            },
            description=(
                "A code block. Content is preserved verbatim — this is the native "
                "habitat of code. Language provides the execution context. "
                "Domain-specific reasoning fields (purpose, assumptions, outputs) "
                "belong in namespace-qualified extensions of this type."
            ),
            example={
                "content": "def entropy(p):\n    return -sum(x * log(x) for x in p if x > 0)",
                "language": "python",
                "label": "entropy-definition",
            },
            registered_by="edphos",
            registered_at="2026-05-11",
        )
    )

    # core/table — registered 2026-05-11 per T-039 and SPEC_LOG [decision] Block Design Axiom.
    # Structural block. Headers and rows are the native form. Caption enriches without transforming.
    reg.register(
        BlockSchema(
            type="core/table",
            posture="C",
            attrs={
                "headers": AttrSpec(
                    type_name="list[str]",
                    required=True,
                    description="Column header labels, in order.",
                    constraints={"non_empty": True},
                ),
                "rows": AttrSpec(
                    type_name="list[list[str]]",
                    required=True,
                    description="Table rows. Each row is a list of cell strings, aligned to headers.",
                ),
                "caption": AttrSpec(
                    type_name="str",
                    required=False,
                    description="Optional table caption or description.",
                ),
            },
            description=(
                "A tabular data block. Headers and rows are the native structure. "
                "Rendering is consumer-determined. Caption provides optional context."
            ),
            example={
                "headers": ["Block type", "Posture", "Registered"],
                "rows": [
                    ["core/heading", "C", "2026-04-08"],
                    ["core/code", "C", "2026-05-11"],
                ],
                "caption": "Registered core block types.",
            },
            registered_by="edphos",
            registered_at="2026-05-11",
        )
    )

    # core/narrative — registered 2026-05-11 per T-019 and SPEC_LOG [decision] Block Design Axiom.
    # Intentional prose — distinct from paragraph in that it serves a document function.
    # Role is optional: the distinction from paragraph is structural, not always named.
    reg.register(
        BlockSchema(
            type="core/narrative",
            posture="O",
            attrs={
                "content": AttrSpec(
                    type_name="str",
                    required=True,
                    description="The narrative prose, preserved as written.",
                    constraints={"non_empty": True},
                ),
                "role": AttrSpec(
                    type_name="str",
                    required=False,
                    description=(
                        "The narrative's function within the document. "
                        "E.g. 'introduction', 'transition', 'synthesis', "
                        "'background', 'argument'. Absent when role is implicit."
                    ),
                ),
            },
            description=(
                "Intentional prose with a document function. Distinct from core/paragraph "
                "in that it is purposeful — it advances an argument, frames a section, "
                "or synthesises prior content. Role names the function when it is explicit."
            ),
            example={
                "content": (
                    "The formalism above captures the equilibrium condition, but it "
                    "conceals the path-dependence that makes empirical application non-trivial."
                ),
                "role": "transition",
            },
            registered_by="edphos",
            registered_at="2026-05-11",
        )
    )

    # ── sci/ namespace — scientific reasoning blocks (registered 2026-05-11) ──────
    # Three blocks form the scientific reasoning chain: hypothesis → model → prediction.
    # Each follows the Block Design Axiom: native content + mandatory reasoning fields.

    # sci/hypothesis — a testable claim in its native form.
    # Mandatory reasoning fields: domain + testable_via.
    # You cannot register a hypothesis without declaring how it would be tested.
    reg.register(
        BlockSchema(
            type="sci/hypothesis",
            posture="C",
            attrs={
                "statement": AttrSpec(
                    type_name="str",
                    required=True,
                    description="The hypothesis as stated, in its native form.",
                    constraints={"non_empty": True},
                ),
                "domain": AttrSpec(
                    type_name="str",
                    required=True,
                    description=(
                        "The scientific domain or namespace this hypothesis belongs to, "
                        "e.g. 'sci.bio', 'sci.origins', 'sci.cog'."
                    ),
                    constraints={"non_empty": True},
                ),
                "testable_via": AttrSpec(
                    type_name="str",
                    required=True,
                    description=(
                        "How this hypothesis would be empirically tested. Mandatory — "
                        "mirrors the tension field in wiki/formalism. A hypothesis "
                        "that cannot specify its test condition is not a hypothesis."
                    ),
                    constraints={"non_empty": True},
                ),
                "predicts": AttrSpec(
                    type_name="list[str]",
                    required=False,
                    description="Observable phenomena this hypothesis predicts.",
                ),
                "assumes": AttrSpec(
                    type_name="list[str]",
                    required=False,
                    description="Background conditions the hypothesis presupposes.",
                ),
                "status": AttrSpec(
                    type_name="str",
                    required=False,
                    description=(
                        "Epistemic status: 'seed', 'active', 'supported', "
                        "'refuted', 'suspended'."
                    ),
                ),
            },
            description=(
                "A scientific hypothesis. Statement is the native form. "
                "domain and testable_via are mandatory — the block commits to "
                "what it is about and how it could be falsified. "
                "predicts and assumes extend the reasoning space."
            ),
            example={
                "statement": (
                    "Bioelectric pattern memory in planaria is substrate-independent: "
                    "the pattern persists through complete cellular turnover."
                ),
                "domain": "sci.bio",
                "testable_via": (
                    "Ablate and regenerate planaria under bioelectric pattern suppression; "
                    "measure head morphology and memory retention across full cell-cycle turnover."
                ),
                "predicts": [
                    "Regenerated planaria retain conditioned behaviour despite full cell replacement.",
                    "Bioelectric disruption during regeneration scrambles morphological memory.",
                ],
                "assumes": [
                    "Bioelectric state is separable from genomic identity.",
                    "Conditioning protocol captures stable memory, not transient state.",
                ],
                "status": "active",
            },
            registered_by="edphos",
            registered_at="2026-05-11",
        )
    )

    # sci/model — a scientific model in its native form, possibly expressed as code or formalism.
    # Mandatory reasoning fields: domain + purpose + assumptions.
    # Assumptions are required — you cannot register a model without declaring its limits.
    reg.register(
        BlockSchema(
            type="sci/model",
            posture="C",
            attrs={
                "content": AttrSpec(
                    type_name="str",
                    required=True,
                    description=(
                        "The model specification in native form — code, equations, "
                        "pseudocode, or formal description. Preserved verbatim."
                    ),
                    constraints={"non_empty": True},
                ),
                "language": AttrSpec(
                    type_name="str",
                    required=False,
                    description=(
                        "Execution context if content is code: 'python', 'r', 'julia', etc. "
                        "Absent for non-executable model specifications."
                    ),
                ),
                "domain": AttrSpec(
                    type_name="str",
                    required=True,
                    description="The scientific domain this model applies to.",
                    constraints={"non_empty": True},
                ),
                "purpose": AttrSpec(
                    type_name="str",
                    required=True,
                    description=(
                        "What this model computes or explains. The reasoning-space "
                        "commitment: a consumer can always ask what this model is for."
                    ),
                    constraints={"non_empty": True},
                ),
                "assumptions": AttrSpec(
                    type_name="list[str]",
                    required=True,
                    description=(
                        "What must be true for this model to apply. Mandatory — "
                        "the declared limits of the model. Parallel to tension in "
                        "wiki/formalism: no model registers without its constraints."
                    ),
                ),
                "outputs": AttrSpec(
                    type_name="list[str]",
                    required=False,
                    description="What the model produces — quantities, classifications, predictions.",
                ),
                "validated_against": AttrSpec(
                    type_name="list[str]",
                    required=False,
                    description="Empirical results, datasets, or benchmarks the model has been tested on.",
                ),
            },
            description=(
                "A scientific model. Content is the native form — code or formal specification. "
                "domain, purpose, and assumptions are mandatory. "
                "assumptions declares the model's limits; it cannot be omitted."
            ),
            example={
                "content": (
                    "def free_energy(phi, A, B):\n"
                    '    """Variational free energy under Gaussian assumptions."""\n'
                    "    return 0.5 * (phi - A @ B).T @ (phi - A @ B)"
                ),
                "language": "python",
                "domain": "sci.cog",
                "purpose": (
                    "Approximate Bayesian inference over hidden states via variational "
                    "free energy minimisation."
                ),
                "assumptions": [
                    "Generative model is Gaussian.",
                    "Hidden states are conditionally independent given observations.",
                    "Variational distribution is in the same family as the prior.",
                ],
                "outputs": [
                    "Free energy scalar",
                    "Posterior belief over hidden states",
                ],
                "validated_against": [
                    "Friston 2010 synthetic benchmark",
                    "SPM12 inversion pipeline",
                ],
            },
            registered_by="edphos",
            registered_at="2026-05-11",
        )
    )

    # sci/prediction — a concrete, observable prediction from a model or hypothesis.
    # Mandatory reasoning fields: derives_from + observable_via.
    # A prediction that cannot be observed is not a prediction.
    reg.register(
        BlockSchema(
            type="sci/prediction",
            posture="C",
            attrs={
                "statement": AttrSpec(
                    type_name="str",
                    required=True,
                    description="The prediction as stated, in its native form.",
                    constraints={"non_empty": True},
                ),
                "derives_from": AttrSpec(
                    type_name="str",
                    required=True,
                    description=(
                        "Hickey coordinate of the model or hypothesis that generates "
                        "this prediction, e.g. 'sci.bio/levin-bioelectric-v1'."
                    ),
                    constraints={"non_empty": True},
                ),
                "observable_via": AttrSpec(
                    type_name="str",
                    required=True,
                    description=(
                        "How this prediction would be measured or observed. Mandatory — "
                        "a prediction without an observational route is unfalsifiable."
                    ),
                    constraints={"non_empty": True},
                ),
                "timescale": AttrSpec(
                    type_name="str",
                    required=False,
                    description="When this prediction is testable — near-term, decade, etc.",
                ),
                "status": AttrSpec(
                    type_name="str",
                    required=False,
                    description="'pending', 'confirmed', 'disconfirmed'.",
                ),
            },
            description=(
                "A concrete, observable prediction derived from a sci/model or sci/hypothesis. "
                "statement is the native form. derives_from traces its lineage. "
                "observable_via is mandatory — it is the falsifiability condition."
            ),
            example={
                "statement": (
                    "Disrupting gap junction connectivity in planaria during regeneration "
                    "will produce ectopic eye formation at non-canonical positions."
                ),
                "derives_from": "sci.bio/levin-bioelectric-v1",
                "observable_via": (
                    "Pharmacological gap junction blockade during regeneration; "
                    "histological imaging of regenerated tissue."
                ),
                "timescale": "near-term (existing experimental protocol)",
                "status": "confirmed",
            },
            registered_by="edphos",
            registered_at="2026-05-11",
        )
    )

    # wiki/formalism — first domain block beyond the core four.
    # Registered 2026-04-14 per SPEC_LOG [decision] Formalism block.
    reg.register(
        BlockSchema(
            type="wiki/formalism",
            posture="C",
            attrs={
                "name": AttrSpec(
                    type_name="str",
                    required=True,
                    description="The ### heading name identifying this formalism.",
                    constraints={"non_empty": True},
                ),
                "expression": AttrSpec(
                    type_name="str",
                    required=True,
                    description="The mathematical expression or formula.",
                    constraints={"non_empty": True},
                ),
                "operational_role": AttrSpec(
                    type_name="str",
                    required=True,
                    description="What the formula does in the theory's own terms.",
                    constraints={"non_empty": True},
                ),
                "tension": AttrSpec(
                    type_name="str",
                    required=True,
                    description=(
                        "Where the formalism exposes internal failure or empirical "
                        "mismatch. Required — embeds the Hilbert/Braithwaite testing "
                        "protocol in the document structure."
                    ),
                    constraints={"non_empty": True},
                ),
                "variables": AttrSpec(
                    type_name="list[str]",
                    required=False,
                    description="List of 'symbol: definition' strings.",
                ),
                "source": AttrSpec(
                    type_name="str",
                    required=False,
                    description="Optional attribution (author, year).",
                ),
                "ct_structure": AttrSpec(
                    type_name="str",
                    required=False,
                    description=(
                        "Optional category-theoretic object the formalism maps to "
                        "(e.g. 'Forgetful Functor', 'Temporal Colimit')."
                    ),
                ),
            },
            description=(
                "A named mathematical formalism extracted from a ## The Formalism "
                "or ## Formalisms block. Required fields: name, expression, "
                "operational_role, tension. The tension field is mandatory — it "
                "records where the formalism fails under empirical application."
            ),
            example={
                "name": "H-Theorem",
                "expression": "dH/dt ≤ 0 ⟹ S ↑",
                "variables": ["H: Boltzmann H-function", "t: time"],
                "operational_role": (
                    "The H-function monotonically decreases in a closed system, "
                    "yielding an arrow of time."
                ),
                "tension": (
                    "Cannot be derived from time-symmetric Newtonian axioms without "
                    "the Stosszahlansatz — the arrow of time is a formal artifact."
                ),
                "source": "Boltzmann (1872)",
                "ct_structure": "Forgetful Functor U: C_mech → C_thermo",
            },
            registered_by="edphos",
            registered_at="2026-04-14",
        )
    )

    # ── Five-block wiki format schemas (T-050) ─────────────────────────────
    # These five block types constitute the formal layer of every wiki document.
    # Registered 2026-04-28 per SPEC_LOG T-050.

    reg.register(
        BlockSchema(
            type="wiki/wit-and-wisdom",
            posture="C",
            attrs={
                "items": AttrSpec(
                    type_name="list[str]",
                    required=True,
                    description=(
                        "A non-empty list of characteristic quotes, aphorisms, or "
                        "memorable statements attributed to the subject. Each item "
                        "is a verbatim or lightly edited quotation."
                    ),
                    constraints={"non_empty": True},
                ),
            },
            description=(
                "A ## Wit & Wisdom section containing a curated list of characteristic "
                "quotes and aphorisms from the subject. Conventional posture: expected "
                "in person and thinker documents, not rejected if absent."
            ),
            example={
                "items": [
                    "The dose makes the poison.",
                    "All models are wrong, but some are useful.",
                ],
            },
            registered_by="edphos+flow",
            registered_at="2026-04-28",
        )
    )

    reg.register(
        BlockSchema(
            type="wiki/analogies",
            posture="C",
            attrs={
                "items": AttrSpec(
                    type_name="list[str]",
                    required=True,
                    description=(
                        "A non-empty list of analogy expressions in the form "
                        "'A : B :: C : D [tag]' where tag is one of: "
                        "generative, illustrative, confirmed. "
                        "Each item is the analogy headline; mapping and disanalogy "
                        "are captured in the document body."
                    ),
                    constraints={
                        "non_empty": True,
                        "enum_suffix": ["generative", "illustrative", "confirmed"],
                    },
                ),
            },
            description=(
                "A ## Analogies section containing structured conceptual mappings. "
                "Each analogy follows the pattern 'A : B :: C : D [tag]' and is "
                "accompanied by a mapping description and a disanalogy. "
                "Conventional posture: standard in developed thinker documents."
            ),
            example={
                "items": [
                    "Glucocorticoid chronicity : hippocampus :: compound interest : debt [generative]",
                    "Testosterone : aggression :: amplifier : signal [confirmed]",
                ],
            },
            registered_by="edphos+flow",
            registered_at="2026-04-28",
        )
    )

    reg.register(
        BlockSchema(
            type="wiki/nuance",
            posture="C",
            attrs={
                "tensions": AttrSpec(
                    type_name="list[str]",
                    required=False,
                    description=(
                        "Explicit tensions, contradictions, or unresolved "
                        "boundary conditions within the subject's framework."
                    ),
                ),
                "models": AttrSpec(
                    type_name="list[str]",
                    required=False,
                    description=(
                        "Conceptual models, frameworks, or tools the subject "
                        "deploys, with brief characterisation."
                    ),
                ),
                "open_questions": AttrSpec(
                    type_name="list[str]",
                    required=False,
                    description=(
                        "Open dialectical questions — unresolved problems that "
                        "remain after the framework has been applied."
                    ),
                ),
            },
            description=(
                "A ## Nuance section containing tensions, boundary conditions, "
                "and open questions within the subject's theoretical framework. "
                "All sub-attrs are optional; at least one should be non-empty "
                "for the block to be substantive. Conventional posture."
            ),
            example={
                "tensions": [
                    "Hard determinism vs. the functional language of cultural agency",
                ],
                "models": [
                    "Tinbergen four questions — mechanism / development / function / evolution",
                ],
                "open_questions": [
                    "If culture is a causal force, does this rescue social agency or relocate the determinism?",
                ],
            },
            registered_by="edphos+flow",
            registered_at="2026-04-28",
        )
    )

    reg.register(
        BlockSchema(
            type="wiki/genealogy",
            posture="F",
            attrs={
                "builds_on": AttrSpec(
                    type_name="list[str]",
                    required=False,
                    description=(
                        "Intellectual predecessors: thinkers or works the subject "
                        "directly builds upon. Each entry: 'Name — brief characterisation'."
                    ),
                ),
                "converges_with": AttrSpec(
                    type_name="list[str]",
                    required=False,
                    description=(
                        "Independent parallel developments reaching overlapping "
                        "conclusions. Each entry: 'Name — convergence characterisation'."
                    ),
                ),
                "departs_from": AttrSpec(
                    type_name="list[str]",
                    required=False,
                    description=(
                        "Explicit rejections or departures from prior frameworks. "
                        "Each entry: 'Name — what is rejected and why'."
                    ),
                ),
                "responds_to": AttrSpec(
                    type_name="list[str]",
                    required=False,
                    description=(
                        "Works or positions the subject directly addresses or responds to."
                    ),
                ),
                "downstream": AttrSpec(
                    type_name="list[str]",
                    required=False,
                    description=(
                        "Forward morphisms: downstream work or projects that build "
                        "on or cite this framework. Load-bearing for morphism extraction."
                    ),
                ),
            },
            description=(
                "A ## Genealogy section encoding the morphism graph for this document. "
                "Formal posture: required for complete wiki documents. Drives the "
                "morphism extractor and PageRank centrality computation. At least one "
                "of builds_on, converges_with, departs_from should be non-empty."
            ),
            example={
                "builds_on": [
                    "Hans Selye — general adaptation syndrome; the foundational stress physiology framework",
                ],
                "converges_with": [
                    "Bruce McEwen — allostatic load; independent development of the cumulative-stress-damage framework",
                ],
                "departs_from": [
                    "E.O. Wilson / classic sociobiology — rejects the genetic-determinist reduction of social behavior",
                ],
                "responds_to": [],
                "downstream": [
                    "Observatory.wiki — contributor; behavioral biology lens on human social organization",
                ],
            },
            registered_by="edphos+flow",
            registered_at="2026-04-28",
        )
    )

    reg.register(
        BlockSchema(
            type="wiki/claims",
            posture="C",
            attrs={
                "items": AttrSpec(
                    type_name="list[str]",
                    required=True,
                    description=(
                        "A non-empty list of epistemic claims in the form "
                        "'Claim text. [status]' where status is one of: "
                        "reported, confirmed, inferred, contested. "
                        "Each claim is a complete, falsifiable proposition."
                    ),
                    constraints={
                        "non_empty": True,
                        "enum_suffix": [
                            "reported",
                            "confirmed",
                            "inferred",
                            "contested",
                        ],
                    },
                ),
            },
            description=(
                "A ## Claims section containing a numbered list of explicit epistemic "
                "claims with status tags. Conventional posture: expected in developed "
                "documents, not rejected if absent. Status vocabulary: "
                "confirmed (evidence strong), reported (attributed, unverified), "
                "inferred (derived by platform), contested (active disagreement)."
            ),
            example={
                "items": [
                    "Chronic stress causes measurable hippocampal atrophy. [confirmed]",
                    "Free will does not survive a full accounting of the neuroscience. [reported]",
                    "The rank-health gradient is present across all income levels. [inferred]",
                ],
            },
            registered_by="edphos+flow",
            registered_at="2026-04-28",
        )
    )

    # ── biol/ namespace — behavioral and evolutionary biology (registered 2026-05-13) ──
    # Twelve block types: nine Formal (F) + three Conventional (C).
    # Source of truth: meta/registries/schemas/biol.md
    # The five-block research format (thesis/evidence/gap/implication/genealogy) plus
    # formalism genealogy blocks (morphism, formalism, formalism-lineage, predication).

    reg.register(
        BlockSchema(
            type="biol/thesis",
            posture="F",
            attrs={
                "content": AttrSpec(
                    type_name="str",
                    required=True,
                    description="The central thesis or argument of the document.",
                    constraints={"non_empty": True},
                ),
                "domain": AttrSpec(
                    type_name="str",
                    required=False,
                    description=(
                        "The sub-domain within behavioral/evolutionary biology, "
                        "e.g. 'neuroendocrinology', 'collective computation', 'bioelectricity'."
                    ),
                ),
            },
            description=(
                "The central thesis block for biol namespace documents. "
                "Formal posture: required for structurally complete biol docs."
            ),
            example={
                "content": (
                    "Chronic stress exposure produces measurable hippocampal atrophy "
                    "via glucocorticoid-mediated mechanisms, with downstream effects on "
                    "memory consolidation and stress reactivity."
                ),
                "domain": "neuroendocrinology",
            },
            registered_by="edphos",
            registered_at="2026-05-13",
        )
    )

    reg.register(
        BlockSchema(
            type="biol/evidence",
            posture="F",
            attrs={
                "items": AttrSpec(
                    type_name="list[str]",
                    required=True,
                    description=(
                        "Empirical evidence items supporting the thesis. "
                        "Each item is a concise statement of a finding or result."
                    ),
                    constraints={"non_empty": True},
                ),
                "sources": AttrSpec(
                    type_name="list[str]",
                    required=False,
                    description="Source attributions for evidence items (author, year, or Hickey coordinate).",
                ),
            },
            description=(
                "Empirical evidence supporting the biol thesis. "
                "Formal posture: required for structurally complete biol docs."
            ),
            example={
                "items": [
                    "Chronic restraint stress reduces hippocampal CA3 dendritic branching in rodents.",
                    "Glucocorticoid receptor blockade prevents stress-induced atrophy.",
                ],
                "sources": ["Watanabe et al. 1992", "McEwen 1999"],
            },
            registered_by="edphos",
            registered_at="2026-05-13",
        )
    )

    reg.register(
        BlockSchema(
            type="biol/gap",
            posture="F",
            attrs={
                "content": AttrSpec(
                    type_name="str",
                    required=True,
                    description=(
                        "An open question, unresolved tension, or empirical gap "
                        "within the framework described by this document."
                    ),
                    constraints={"non_empty": True},
                ),
            },
            description=(
                "An open gap or unresolved question in the biol framework. "
                "Formal posture: required for structurally complete biol docs."
            ),
            example={
                "content": (
                    "The dose-response relationship between cortisol exposure duration "
                    "and structural hippocampal change is not yet fully characterised "
                    "across naturalistic (non-experimental) populations."
                ),
            },
            registered_by="edphos",
            registered_at="2026-05-13",
        )
    )

    reg.register(
        BlockSchema(
            type="biol/implication",
            posture="F",
            attrs={
                "content": AttrSpec(
                    type_name="str",
                    required=True,
                    description="The downstream implication or applied consequence of the framework.",
                    constraints={"non_empty": True},
                ),
                "domain": AttrSpec(
                    type_name="str",
                    required=True,
                    description=(
                        "The domain to which this implication applies, "
                        "e.g. 'clinical', 'evolutionary', 'platform'."
                    ),
                    constraints={"non_empty": True},
                ),
            },
            description=(
                "A downstream implication of the biol framework. "
                "Formal posture: required for structurally complete biol docs. "
                "domain is mandatory — implications are always directed."
            ),
            example={
                "content": (
                    "Chronic stress exposure in early development may produce lasting "
                    "alterations in HPA axis reactivity, with implications for psychiatric risk."
                ),
                "domain": "clinical",
            },
            registered_by="edphos",
            registered_at="2026-05-13",
        )
    )

    reg.register(
        BlockSchema(
            type="biol/genealogy",
            posture="F",
            attrs={
                "builds_on": AttrSpec(
                    type_name="list[str]",
                    required=True,
                    description=(
                        "Intellectual predecessors within the biol domain. "
                        "Each entry: 'Name — brief characterisation of the contribution'."
                    ),
                    constraints={"non_empty": True},
                ),
                "departs_from": AttrSpec(
                    type_name="list[str]",
                    required=False,
                    description="Frameworks or positions explicitly rejected. Each entry: 'Name — what is rejected'.",
                ),
                "extends": AttrSpec(
                    type_name="list[str]",
                    required=False,
                    description="Works or frameworks this document extends without departing from.",
                ),
            },
            description=(
                "Genealogy block for biol namespace documents. "
                "Formal posture. builds_on is mandatory. "
                "Distinct from wiki/genealogy — biol/genealogy tracks domain-internal lineage."
            ),
            example={
                "builds_on": [
                    "Hans Selye — general adaptation syndrome; foundational stress physiology",
                    "Bruce McEwen — allostatic load; cumulative-stress-damage framework",
                ],
                "departs_from": [
                    "Simple homeostasis models — stress as deviation from setpoint (too static)",
                ],
                "extends": [
                    "Sapolsky 2004 — Why Zebras Don't Get Ulcers; applied neuroendocrinology",
                ],
            },
            registered_by="edphos",
            registered_at="2026-05-13",
        )
    )

    reg.register(
        BlockSchema(
            type="biol/morphism",
            posture="F",
            attrs={
                "type": AttrSpec(
                    type_name="str",
                    required=True,
                    description=(
                        "The morphism type, e.g. 'forgetful', 'adjunction', "
                        "'natural_transformation', 'colimit', 'functor'."
                    ),
                    constraints={"non_empty": True},
                ),
                "scope": AttrSpec(
                    type_name="str",
                    required=True,
                    description=(
                        "What the morphism maps between — source and target categories "
                        "or levels of analysis."
                    ),
                    constraints={"non_empty": True},
                ),
            },
            description=(
                "A category-theoretic morphism connecting levels of biological organisation. "
                "Formal posture. Used for formalising inter-level relationships "
                "in e.g. Flack/Hoel causal emergence analyses."
            ),
            example={
                "type": "forgetful",
                "scope": "C_micro (neuron firing) → C_macro (population state); discards spike-timing detail",
            },
            registered_by="edphos",
            registered_at="2026-05-13",
        )
    )

    reg.register(
        BlockSchema(
            type="biol/formalism",
            posture="F",
            attrs={
                "name": AttrSpec(
                    type_name="str",
                    required=True,
                    description="The formalism name, matching the ### heading in the document.",
                    constraints={"non_empty": True},
                ),
                "expression": AttrSpec(
                    type_name="str",
                    required=True,
                    description="The mathematical expression or equation.",
                    constraints={"non_empty": True},
                ),
                "notation": AttrSpec(
                    type_name="str",
                    required=False,
                    description="Notation guide for symbols used in the expression.",
                ),
                "domain": AttrSpec(
                    type_name="str",
                    required=False,
                    description="The biological sub-domain this formalism applies to.",
                ),
            },
            description=(
                "A named mathematical formalism in a biol namespace document. "
                "Formal posture. Lighter than wiki/formalism — tension is not required "
                "here (biological formalisms often lack clean failure modes at the formula level); "
                "tension belongs in biol/gap."
            ),
            example={
                "name": "Allostatic Load Index",
                "expression": "AL = Σ(biomarker_i > threshold_i)",
                "notation": "biomarker_i: one of 10 neuroendocrine/metabolic/immune indicators",
                "domain": "neuroendocrinology",
            },
            registered_by="edphos",
            registered_at="2026-05-13",
        )
    )

    reg.register(
        BlockSchema(
            type="biol/formalism-lineage",
            posture="F",
            attrs={
                "origin": AttrSpec(
                    type_name="list[str]",
                    required=True,
                    description=(
                        "The origin(s) of the formalism lineage. Multiple roots are valid, "
                        "e.g. ['Boltzmann (1877)', 'Gibbs (1902)']. "
                        "Each entry: 'Name (year)' or 'Name (year) — brief note'."
                    ),
                    constraints={"non_empty": True},
                ),
                "target": AttrSpec(
                    type_name="str",
                    required=True,
                    description="The current formalism this lineage terminates at (Hickey coordinate or name).",
                    constraints={"non_empty": True},
                ),
                "intermediate": AttrSpec(
                    type_name="list[str]",
                    required=False,
                    description=(
                        "Optional intermediate hops between origin and target, "
                        "e.g. ['Mehta & Schwab (2014)'] in a Kadanoff → Flack chain."
                    ),
                ),
                "formalism_ref": AttrSpec(
                    type_name="str",
                    required=False,
                    description="Hickey coordinate of the biol/formalism block this lineage describes.",
                ),
            },
            description=(
                "Derivation lineage for a mathematical formalism in the biol domain. "
                "Formal posture. Tracks the path from origin(s) to target formalism — "
                "the history-of-analysis layer for formal apparatus."
            ),
            example={
                "origin": [
                    "Boltzmann (1877) — entropy formulation",
                    "Gibbs (1902) — ensemble theory",
                ],
                "target": "biol/levin-bioelectric-v1#free-energy-formulation",
                "intermediate": [
                    "Jaynes (1957) — MaxEnt principle",
                    "Friston (2010) — free energy",
                ],
                "formalism_ref": "biol/levin-bioelectric-v1#allostatic-index",
            },
            registered_by="edphos",
            registered_at="2026-05-13",
        )
    )

    reg.register(
        BlockSchema(
            type="biol/predication",
            posture="F",
            attrs={
                "content": AttrSpec(
                    type_name="str",
                    required=True,
                    description=(
                        "The predication statement — a claim about what a formalism "
                        "does, models, or defines in the biological domain."
                    ),
                    constraints={"non_empty": True},
                ),
                "formalism_ref": AttrSpec(
                    type_name="str",
                    required=False,
                    description="Hickey coordinate of the formalism this predication applies to.",
                ),
                "modality": AttrSpec(
                    type_name="str",
                    required=False,
                    description=(
                        "How the formalism relates to its domain. "
                        "One of: defines, operationalizes, models, semanticizes."
                    ),
                    constraints={
                        "enum": ["defines", "operationalizes", "models", "semanticizes"]
                    },
                ),
            },
            description=(
                "A predication block: a statement about what a formalism does in the biological domain. "
                "Formal posture. modality encodes the relationship type — "
                "defines (constitutive), operationalizes (measurement), models (approximates), "
                "semanticizes (gives meaning to)."
            ),
            example={
                "content": (
                    "The Allostatic Load Index operationalizes cumulative physiological wear "
                    "as a count of biomarkers exceeding clinical thresholds."
                ),
                "formalism_ref": "biol/sapolsky-robert#allostatic-load-index",
                "modality": "operationalizes",
            },
            registered_by="edphos",
            registered_at="2026-05-13",
        )
    )

    # biol/ Conventional blocks (keyset-indexed, no conformance checking)

    reg.register(
        BlockSchema(
            type="biol/prose",
            posture="C",
            attrs={
                "content": AttrSpec(
                    type_name="str",
                    required=True,
                    description="Elaboration on formal findings; contextualising prose.",
                    constraints={"non_empty": True},
                ),
            },
            description="Conventional prose block in a biol document. Elaborates on formal findings.",
            example={
                "content": "The glucocorticoid cascade unfolds over minutes to hours, unlike fast neurotransmission."
            },
            registered_by="edphos",
            registered_at="2026-05-13",
        )
    )

    reg.register(
        BlockSchema(
            type="biol/annotation",
            posture="C",
            attrs={
                "content": AttrSpec(
                    type_name="str",
                    required=True,
                    description="Social, evolutionary, or contextual prose on a formalism.",
                    constraints={"non_empty": True},
                ),
            },
            description="Conventional annotation block in a biol document. Social/biological prose on a formalism.",
            example={
                "content": "Sapolsky's popularisation brought allostatic load into public health discourse."
            },
            registered_by="edphos",
            registered_at="2026-05-13",
        )
    )

    reg.register(
        BlockSchema(
            type="biol/citations",
            posture="C",
            attrs={
                "items": AttrSpec(
                    type_name="list[str]",
                    required=True,
                    description="Source references for the document. Each entry: standard citation format.",
                    constraints={"non_empty": True},
                ),
            },
            description="Conventional citations block in a biol document.",
            example={
                "items": [
                    "Sapolsky, R.M. (2004). Why Zebras Don't Get Ulcers. Holt.",
                    "McEwen, B.S. (1998). NEJM 338(3):171–179.",
                ]
            },
            registered_by="edphos",
            registered_at="2026-05-13",
        )
    )

    # ── paleo/ namespace — paleoanthropology and human origins (registered 2026-05-13) ──
    # Seven block types: four Formal (F) + three Conventional (C).
    # Source of truth: meta/registries/schemas/paleo.md
    # Five-block research format (thesis/evidence/gap/implication) minus genealogy —
    # paleo documents use wiki/genealogy for intellectual lineage.

    reg.register(
        BlockSchema(
            type="paleo/thesis",
            posture="F",
            attrs={
                "content": AttrSpec(
                    type_name="str",
                    required=True,
                    description="The central thesis or interpretive claim of the document.",
                    constraints={"non_empty": True},
                ),
                "domain": AttrSpec(
                    type_name="str",
                    required=False,
                    description=(
                        "The sub-domain within paleoanthropology, "
                        "e.g. 'lithic analysis', 'dispersal modelling', 'cognitive archaeology'."
                    ),
                ),
            },
            description=(
                "The central thesis block for paleo namespace documents. "
                "Formal posture: required for structurally complete paleo docs."
            ),
            example={
                "content": (
                    "The Body-Grammar Substrate Hypothesis proposes that pre-linguistic "
                    "body grammar served as the cognitive substrate from which structured "
                    "language emerged via analogical transfer."
                ),
                "domain": "cognitive archaeology",
            },
            registered_by="edphos",
            registered_at="2026-05-13",
        )
    )

    reg.register(
        BlockSchema(
            type="paleo/evidence",
            posture="F",
            attrs={
                "items": AttrSpec(
                    type_name="list[str]",
                    required=True,
                    description=(
                        "Archaeological, genetic, or comparative evidence items. "
                        "Each item is a concise statement of a finding or datum."
                    ),
                    constraints={"non_empty": True},
                ),
                "sources": AttrSpec(
                    type_name="list[str]",
                    required=False,
                    description="Source attributions (author, year, site, or Hickey coordinate).",
                ),
            },
            description=(
                "Empirical evidence for the paleo thesis. "
                "Formal posture: required for structurally complete paleo docs."
            ),
            example={
                "items": [
                    "Earliest cave art (Blombos ochre engravings, ~75 kya) precedes systematic ochre use.",
                    "Homo sapiens dispersal into Europe correlates with Upper Palaeolithic symbolic explosion.",
                ],
                "sources": ["Henshilwood et al. 2002", "d'Errico 2003"],
            },
            registered_by="edphos",
            registered_at="2026-05-13",
        )
    )

    reg.register(
        BlockSchema(
            type="paleo/gap",
            posture="F",
            attrs={
                "content": AttrSpec(
                    type_name="str",
                    required=True,
                    description=(
                        "An open question, interpretive gap, or unresolved empirical "
                        "problem within the paleo framework described."
                    ),
                    constraints={"non_empty": True},
                ),
            },
            description=(
                "An open gap or unresolved question in the paleo framework. "
                "Formal posture: required for structurally complete paleo docs."
            ),
            example={
                "content": (
                    "The taphonomic record between 300–200 kya is insufficiently dense "
                    "to resolve whether symbolic behaviour was continuous or punctuated "
                    "in its development."
                ),
            },
            registered_by="edphos",
            registered_at="2026-05-13",
        )
    )

    reg.register(
        BlockSchema(
            type="paleo/implication",
            posture="F",
            attrs={
                "content": AttrSpec(
                    type_name="str",
                    required=True,
                    description="The downstream implication of the paleo framework.",
                    constraints={"non_empty": True},
                ),
                "domain": AttrSpec(
                    type_name="str",
                    required=True,
                    description=(
                        "The domain this implication applies to, "
                        "e.g. 'cognitive evolution', 'linguistics', 'platform'."
                    ),
                    constraints={"non_empty": True},
                ),
            },
            description=(
                "A downstream implication of the paleo framework. "
                "Formal posture: required for structurally complete paleo docs. "
                "domain is mandatory — implications are always directed."
            ),
            example={
                "content": (
                    "If body grammar is the cognitive substrate for language, then "
                    "sign languages are not derivative of spoken language but equally "
                    "primary instantiations of the same substrate."
                ),
                "domain": "linguistics",
            },
            registered_by="edphos",
            registered_at="2026-05-13",
        )
    )

    # paleo/ Conventional blocks

    reg.register(
        BlockSchema(
            type="paleo/prose",
            posture="C",
            attrs={
                "content": AttrSpec(
                    type_name="str",
                    required=True,
                    description="Elaboration on paleo findings; contextualising narrative.",
                    constraints={"non_empty": True},
                ),
            },
            description="Conventional prose block in a paleo document.",
            example={
                "content": "The Levantine corridor served as the primary route for early Homo sapiens dispersals into Eurasia."
            },
            registered_by="edphos",
            registered_at="2026-05-13",
        )
    )

    reg.register(
        BlockSchema(
            type="paleo/citations",
            posture="C",
            attrs={
                "items": AttrSpec(
                    type_name="list[str]",
                    required=True,
                    description="Source references for the document.",
                    constraints={"non_empty": True},
                ),
            },
            description="Conventional citations block in a paleo document.",
            example={
                "items": [
                    "Klein, R.G. (2009). The Human Career, 3rd ed. Chicago.",
                    "d'Errico, F. (2003). JHE 44(2):166–195.",
                ]
            },
            registered_by="edphos",
            registered_at="2026-05-13",
        )
    )

    reg.register(
        BlockSchema(
            type="paleo/annotation",
            posture="C",
            attrs={
                "content": AttrSpec(
                    type_name="str",
                    required=True,
                    description="Domain application narrative — contextual annotation for a specific site, find, or argument.",
                    constraints={"non_empty": True},
                ),
            },
            description="Conventional annotation block in a paleo document.",
            example={
                "content": "The Blombos Cave ochre engravings constitute the earliest known abstract symbolic artefacts in the African record."
            },
            registered_by="edphos",
            registered_at="2026-05-13",
        )
    )

    reg.register(
        BlockSchema(
            type="realization/claim",
            posture="F",
            attrs={
                "source": AttrSpec(
                    type_name="str",
                    required=True,
                    description="Wiki coordinate of the abstract system being realized.",
                ),
                "target": AttrSpec(
                    type_name="str",
                    required=True,
                    description="Code coordinate of the concrete domain.",
                ),
                "realization_type": AttrSpec(
                    type_name="str",
                    required=True,
                    description="Whether the satisfaction is analytic or empirical.",
                    constraints={"enum": ["analytic", "empirical"]},
                ),
                "domain": AttrSpec(
                    type_name="str",
                    required=True,
                    description="The empirical substructure in scope for this claim.",
                ),
                "deferred": AttrSpec(
                    type_name="list[str]",
                    required=False,
                    description="Aspects of the specification explicitly not in scope.",
                ),
                "verified_by": AttrSpec(
                    type_name="str",
                    required=False,
                    description="Evidence that the satisfaction relation holds.",
                ),
                "approximation": AttrSpec(
                    type_name="str",
                    required=False,
                    description="The degree to which the abstract structure is found in the concrete domain.",
                ),
                "significance": AttrSpec(
                    type_name="str",
                    required=False,
                    description="What this concrete realization confers on the abstract theory.",
                ),
                "desargues_conditions": AttrSpec(
                    type_name="list[str]",
                    required=False,
                    description="Structural properties of the concrete domain independent of the theoretical axioms.",
                ),
                "aspect": AttrSpec(
                    type_name="str",
                    required=False,
                    description="Human-readable label for the theoretical unit being realized.",
                ),
            },
            description="Formal block schemas for mapping theoretical units to their concrete code realizations.",
            example={
                "source": "math/wald-abraham#decision-function",
                "target": "phosphene.wald.models.DecisionFunction",
                "realization_type": "analytic",
                "domain": "finite terminal decision space",
            },
            registered_by="edphos+flow",
            registered_at="2026-05-26",
        )
    )

    return reg
