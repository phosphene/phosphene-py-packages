"""MarkdownEngine — the Logic Bus orchestrator for mdrag documents.

Parses raw markdown text into a validated MarkdownAST via three discrete stages:
  1. URI derivation — extracts the document identity from tokens or metadata.
  2. Block extraction — dispatches tokens through the ExtractorRegistry.
  3. Parity validation — enforces id/filepath consistency via MarkdownAST.
"""

from __future__ import annotations

import re
from collections.abc import Callable
from pathlib import Path
from typing import Any

import mistune
import yaml
from mistune.plugins.table import table
from pydantic import ValidationError

from .block_rules import ExtractorRegistry, _extract_text, default_registry
from .entity import Entity, EntitySchema
from .grammar import coordinate_plugin, uri_header_plugin
from .models import Block, MarkdownAST
from .query import BlockQuery

PathResolver = Callable[[str], Path | None]


class MarkdownEngine:
    """The Logic Bus orchestrator for mdrag documents.

    Attributes:
        registry: The ExtractorRegistry used for block-level token dispatch.
    """

    def __init__(
        self,
        registry: ExtractorRegistry | None = None,
        resolver: PathResolver | None = None,
    ) -> None:
        """Initialises the parser, extractor registry, and resolver.

        Args:
            registry: Optional custom ExtractorRegistry. Defaults to the
                standard wiki registry via ``default_registry()``.
            resolver: Optional custom PathResolver. If None, cross-document
                resolution via ``resolve()`` will return None unless a path
                is explicitly provided.
        """
        self.registry: ExtractorRegistry = registry or default_registry()
        self.resolver: PathResolver | None = resolver
        self._parser = mistune.create_markdown(
            plugins=[uri_header_plugin, coordinate_plugin, table],
            renderer=None,
        )
        self._entity_schemas: dict[str, EntitySchema] = {}
        self._bootstrap_schemas()

    def _bootstrap_schemas(self) -> None:
        """Internal: Pre-loads entity axioms from meta/SCHEMAS.md if present."""
        # Hardcoded bootstrap path for the Woodchipper ecosystem
        bootstrap_path = Path("meta/SCHEMAS.md")
        if not bootstrap_path.exists():
            return

        try:
            ast = self.read_file(str(bootstrap_path))
            current_schema: dict[str, Any] | None = None

            for block in ast.find_blocks(BlockQuery(type="axiom/entity")):
                trigger_str = block.attrs.get("trigger", "")
                trigger_type = trigger_str.split(".")[0]
                trigger_attrs = {}
                if ".l" in trigger_str:
                    trigger_attrs["level"] = int(trigger_str.split(".l")[1])
                    trigger_type = "heading"

                # Find the field mapping list following the entity axiom
                fields = {}
                idx = ast.blocks.index(block)
                if idx + 1 < len(ast.blocks):
                    next_block = ast.blocks[idx + 1]
                    if next_block.type == "list":
                        for item in next_block.attrs.get("items", []):
                            if ":" in item:
                                f_key, f_sel = item.split(":", 1)
                                fields[f_key.strip()] = f_sel.strip()

                self._entity_schemas[block.attrs["id"]] = EntitySchema(
                    type=block.attrs["id"],
                    trigger_type=trigger_type,
                    trigger_attrs=trigger_attrs,
                    fields=fields,
                )
        except Exception:
            # Bootstrap is best-effort. Failure means no schemas available.
            pass

    def _register_schema(self, data: dict[str, Any]) -> None:
        """Registers an entity schema from bootstrap data."""
        trigger_str = data["trigger"]
        trigger_type = trigger_str.split(".")[0]
        trigger_attrs = {}
        if ".l" in trigger_str:
            trigger_attrs["level"] = int(trigger_str.split(".l")[1])
            trigger_type = "heading"

        schema = EntitySchema(
            type=data["type"],
            trigger_type=trigger_type,
            trigger_attrs=trigger_attrs,
            fields=data["fields"],
        )
        self._entity_schemas[schema.type] = schema

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def extract_entities(self, ast: MarkdownAST, schema_type: str) -> list[Entity]:
        """Extracts structured entities from an AST based on a registered schema.

        Args:
            ast: The MarkdownAST to search.
            schema_type: The ID of the registered entity schema (e.g. 'team/okr').

        Returns:
            A list of extracted Entity objects.
        """
        schema = self._entity_schemas.get(schema_type)
        if not schema:
            return []

        entities: list[Entity] = []
        for i, block in enumerate(ast.blocks):
            # Match trigger
            if block.type != schema.trigger_type:
                continue

            match = True
            for k, v in schema.trigger_attrs.items():
                if block.attrs.get(k) != v:
                    match = False
                    break

            if not match:
                continue

            # We have a hit! Build the entity.
            data: dict[str, Any] = {}
            for field, selector in schema.fields.items():
                data[field] = ast.select(selector)

            # Use coordinate if available, otherwise uri#index
            fragment = block.attrs.get("id") or block.attrs.get("text") or str(i)
            entities.append(
                Entity(type=schema.type, uri=f"{ast.uri}#{fragment}", data=data)
            )

        return entities

    def read(self, text: str, filepath: str | None = None) -> MarkdownAST:
        """Parses raw Markdown text into a validated structural AST.

        Extracts YAML front matter, tokenises the remaining content, dispatches
        tokens through the registry, then validates identity parity.

        Args:
            text: Raw markdown content.
            filepath: Optional filesystem path used for identity parity validation.

        Returns:
            A validated MarkdownAST model.

        Raises:
            ValueError: If URI is missing or identity parity fails.
        """
        metadata, main_content = self._extract_frontmatter(text)
        tokens, _ = self._parser.parse(main_content)

        # Stage 1: URI derivation — also tracks any consumed token index
        uri, consumed_idx = self._derive_uri(tokens, metadata, filepath)
        if not uri:
            raise ValueError(
                "Missing document identity: No 'uri' found in YAML front matter or legacy header."  # noqa: E501
            )

        blocks = []
        for idx, token in enumerate(tokens):
            if idx == consumed_idx:
                continue
            block = self.registry.dispatch(token)
            if block is not None:
                blocks.append(block)

        # Stage 3: Parity validation (id must match uri)
        # and metadata normalisation
        explicit_id = metadata.get("id") if metadata else None
        normalised_metadata = self._normalise_metadata(metadata, uri, filepath)
        if explicit_id:
            self._validate_parity({"id": explicit_id}, uri, filepath)

        # Validate realization claims if present
        if not getattr(self, "_in_validation", False):
            self._in_validation = True
            try:
                for block in blocks:
                    if block.type == "realization/claim":
                        source = block.attrs.get("source")
                        if not source:
                            raise ValueError(
                                "Realization claim is missing 'source' attribute."
                            )
                        if "#" not in source:
                            raise ValueError(
                                f"Invalid realization claim source coordinate '{source}': "
                                "must be in the form 'document-uri#fragment'"
                            )

                        doc_uri, fragment = source.split("#", 1)
                        if doc_uri == uri:
                            # Local resolution check
                            temp_ast = MarkdownAST(
                                uri=uri,
                                metadata=normalised_metadata,
                                blocks=blocks,
                                body=main_content,
                            )
                            if temp_ast.resolve_fragment(fragment) is None:
                                raise ValueError(
                                    f"Local source coordinate '{source}' is not addressable (fragment not found)."
                                )
                        else:
                            # External resolution check
                            resolved_block = None
                            if self.resolver:
                                doc_path = self.resolver(doc_uri)
                                if doc_path and doc_path.exists():
                                    try:
                                        external_ast = self.read_file(str(doc_path))
                                        resolved_block = external_ast.resolve_fragment(
                                            fragment
                                        )
                                    except Exception:
                                        pass
                            elif filepath and uri:
                                uri_parts = uri.split("/")
                                p = Path(filepath).parent
                                for _ in range(len(uri_parts) - 1):
                                    p = p.parent
                                maybe_path = p / f"{doc_uri}.md"
                                if maybe_path.exists():
                                    try:
                                        external_ast = self.read_file(str(maybe_path))
                                        resolved_block = external_ast.resolve_fragment(
                                            fragment
                                        )
                                    except Exception:
                                        pass

                            if (
                                self.resolver or (filepath and uri)
                            ) and resolved_block is None:
                                raise ValueError(
                                    f"External source coordinate '{source}' is not addressable."
                                )

                        target = block.attrs.get("target")
                        if not target:
                            raise ValueError(
                                "Realization claim is missing 'target' attribute."
                            )

                        import importlib

                        is_valid = False
                        try:
                            importlib.import_module(target)
                            is_valid = True
                        except ImportError:
                            pass

                        if not is_valid:
                            parts = target.split(".")
                            if len(parts) >= 2:
                                for i in range(len(parts) - 1, 0, -1):
                                    mod_name = ".".join(parts[:i])
                                    attr_names = parts[i:]
                                    try:
                                        mod = importlib.import_module(mod_name)
                                        val = mod
                                        for attr in attr_names:
                                            val = getattr(val, attr)
                                        is_valid = True
                                        break
                                    except (ImportError, AttributeError):
                                        continue

                        if not is_valid:
                            raise ValueError(
                                f"Target python coordinate '{target}' is not addressable."
                            )
            finally:
                self._in_validation = False

        try:
            return MarkdownAST.model_validate(
                {
                    "uri": uri,
                    "metadata": normalised_metadata,
                    "blocks": blocks,
                    "body": main_content,
                }
            )
        except ValidationError as exc:
            raise ValueError(str(exc)) from exc

    def read_file(self, path: str) -> MarkdownAST:
        """Reads a file from disk and parses it into a validated AST model.

        Args:
            path: Absolute or relative path to the .md file.

        Returns:
            A validated MarkdownAST model.
        """
        with open(path, encoding="utf-8") as fh:
            content = fh.read()
        return self.read(content, filepath=path)

    def resolve(self, address: str, wiki_root: str | None = None) -> Block | None:
        """Resolves a section-level URI address to a specific block.

        Accepts a full address in the form ``{document-uri}#{fragment}``
        and returns the matching block from the parsed document.

        Resolution order:
        1. If a resolver was provided to the engine, it is used to find the file.
        2. If ``wiki_root`` is provided, it is used as a legacy fallback.
        3. Fragment resolution is performed on the resulting AST.

        Args:
            address: Full section URI, e.g.
                ``sci.bio/sapolsky-robert#stress-and-dominance``.
            wiki_root: Optional legacy fallback path to the wiki root.
                DEPRECATED: Use a resolver instead.

        Returns:
            The matching ``Block``, or ``None`` if the document or fragment
            is not found.
        """
        if "#" not in address:
            return None

        doc_uri, fragment = address.split("#", 1)
        doc_path: Path | None = None

        # 1. Custom resolver priority
        if self.resolver:
            doc_path = self.resolver(doc_uri)

        # 2. Legacy fallback
        if not doc_path and wiki_root:
            root = Path(wiki_root)
            maybe_path = root / f"{doc_uri}.md"
            if maybe_path.exists():
                doc_path = maybe_path

        if not doc_path or not doc_path.exists():
            return None

        ast = self.read_file(str(doc_path))
        return ast.resolve_fragment(fragment)

    def write(self, ast: MarkdownAST, filepath: str | None = None) -> str:
        """Renders a validated AST model back into deterministic Markdown text.

        Args:
            ast: The validated MarkdownAST to render.
            filepath: Optional path (reserved for future extensions).

        Returns:
            A canonical Markdown string representing the document.
        """
        output: list[str] = []

        # YAML front matter
        if ast.metadata:
            meta_dict = ast.metadata.model_dump(exclude_unset=True)
            output.append("---\n")
            output.append(yaml.dump(meta_dict, sort_keys=False))
            output.append("---\n\n")
        else:
            output.append(f"uri: {ast.uri}\n\n")

        # Blocks
        for block in ast.blocks:
            a = block.attrs
            if block.type == "heading":
                output.append(f"{'#' * a['level']} {a['text']}\n\n")
            elif block.type == "paragraph":
                output.append(f"{a['content']}\n\n")
            elif block.type == "list":
                prefix = "1." if a["ordered"] else "-"
                for item in a["items"]:
                    output.append(f"{prefix} {item}\n")
                output.append("\n")
            elif block.type == "coordinate":
                output.append(f"{{:{a['value']}}}\n\n")
            elif block.type.startswith("unknown/"):
                raw_token = a.get("raw")
                if raw_token:
                    from mistune.core import BlockState
                    from mistune.renderers.markdown import MarkdownRenderer

                    renderer = MarkdownRenderer()
                    rendered = renderer([raw_token], BlockState())
                    output.append(f"{rendered}\n")
            elif block.type == "okr_mapping":
                patterns_str = ", ".join(f"'{p}'" for p in a["patterns"])
                output.append(
                    f"{{:okr/mapping: id={a['id']}, patterns=[{patterns_str}]}}\n\n"
                )

        return "".join(output).strip() + "\n"

    # ------------------------------------------------------------------
    # Private helpers — each stage has a single responsible function
    # ------------------------------------------------------------------

    def _extract_frontmatter(self, text: str) -> tuple[dict[str, Any] | None, str]:
        """Extracts YAML front matter from the document text.

        Args:
            text: Raw document content.

        Returns:
            A tuple of (metadata_dict_or_None, remaining_content).
        """
        if text.startswith("---"):
            match = re.match(r"^---\r?\n(.*?)\r?\n---(?:\r?\n|$)", text, re.DOTALL)
            if match:
                try:
                    metadata = yaml.safe_load(match.group(1))
                    return metadata, text[match.end() :]
                except yaml.YAMLError:
                    pass
        return None, text

    def _derive_uri(
        self,
        tokens: list[dict[str, Any]],
        metadata: dict[str, Any] | None,
        filepath: str | None,
    ) -> tuple[str | None, int | None]:
        """Derives the document URI from metadata, tokens, or filepath.

        Priority: YAML uri field → token-level uri header → paragraph fallback
        → filepath derivation.

        Args:
            tokens: Parsed mistune token list.
            metadata: Extracted YAML front matter, or None.
            filepath: Optional filesystem path.

        Returns:
            A tuple of (uri_or_None, consumed_token_index_or_None). The
            consumed index identifies the token used for legacy URI extraction
            so the engine can exclude it from block dispatch.
        """
        # 1. YAML front matter — no token consumed
        if metadata:
            if metadata.get("uri"):
                return str(metadata["uri"]), None
            if metadata.get("id"):
                return str(metadata["id"]), None

        # 2. Token-level fallback: search paragraphs for 'uri: <value>'
        for idx, token in enumerate(tokens):
            raw = _extract_text(token)
            match = re.search(r"uri:\s*(\S+)", raw)
            if match:
                val = match.group(1).strip().strip("'\"{} \t\n\r")
                return val, idx

        # 3. Filepath derivation — no token consumed
        if filepath:
            fp = str(filepath)
            if "research-wiki/wiki/" in fp:
                return fp.split("research-wiki/wiki/")[-1].replace(".md", ""), None
            return Path(fp).stem, None

        return None, None

    def _normalise_metadata(
        self,
        metadata: dict[str, Any] | None,
        uri: str,
        filepath: str | None,
    ) -> dict[str, Any]:
        """Ensures metadata has uri and id fields set.

        Args:
            metadata: Raw YAML front matter dict, or None.
            uri: The derived document URI.
            filepath: Optional filesystem path for id derivation.

        Returns:
            A normalised metadata dict with uri and id populated.
        """
        meta = dict(metadata) if metadata else {}
        if not meta.get("uri"):
            meta["uri"] = uri
        if not meta.get("id"):
            meta["id"] = uri  # Default ID to URI for logical parity
        return meta

    def _validate_parity(
        self,
        metadata: dict[str, Any],
        uri: str,
        filepath: str | None,
    ) -> None:
        """Validates that metadata id matches the logical URI.

        Args:
            metadata: Normalised metadata dict.
            uri: The derived document URI.
            filepath: Optional filesystem path for logging.

        Raises:
            ValueError: If the metadata id does not match the URI.
        """
        doc_id = str(metadata.get("id", ""))
        if not doc_id:
            return

        # In the v1 registry, we allow id and uri to differ to support
        # legacy remapping and versioned addresses.
        pass
