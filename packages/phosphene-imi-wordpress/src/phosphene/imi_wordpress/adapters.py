"""Wire adapters transforming domain entities into transport payloads.

This module contains pure projections that isolate wire formats, encoding rules,
and third-party schema requirements from the core domain entities.

@dft
- A1 (pure-io-separation): Pure projection logic — zero I/O imports.
- A2 (determinism): Deterministic encoding transformations.
- A3 (manifest-conformance): WordPressMeta strictly models CPT 39-field contract.
- A4 (dft-docs): This docstring section.
- A6 (check-result): Returns typed payload dictionaries (proof of serialization).
"""

from __future__ import annotations

from collections.abc import Mapping
from typing import Any, NotRequired, TypedDict

from phosphene.imi_wordpress.domain import (
    DOIStatus,
    EditorialState,
    PreprintEntry,
)
from phosphene.imi_wordpress.serializers.author_unit import AuthorMetaUnit
from phosphene.imi_wordpress.serializers.doi_unit import DoiMetaUnit
from phosphene.imi_wordpress.serializers.editorial_unit import EditorialStateUnit
from phosphene.imi_wordpress.serializers.keywords_unit import KeywordsUnit
from phosphene.imi_wordpress.serializers.license_unit import LicenseUnit
from phosphene.imi_wordpress.serializers.version_unit import VersionMetaUnit
from phosphene.utils.html import MetaTag, render_meta_tags
from phosphene.utils.text import join_delimited


class WordPressMeta(TypedDict):
    """Canonical TypedDict representing the 39-field IMI Registry schema."""

    reg_author_name: str
    reg_orcid: str
    reg_affiliation: str
    reg_country: str
    reg_abstract: str
    reg_methodology: str
    reg_license: str
    reg_declaration: bool
    reg_keywords: str
    reg_coauthors: str
    reg_destination_url: str
    reg_published_destination: str
    reg_pdf_url: str
    reg_schema_type: str
    reg_registry_id: str
    reg_pipeline_status: str
    reg_version: int
    reg_version_type: str
    reg_version_history: str
    reg_prior_versions: str
    reg_doi: str
    reg_doi_url: str
    reg_doi_status: str
    reg_doi_minted_date: str
    reg_crossref_deposit_id: str
    reg_withdrawal_notice: NotRequired[str]
    reg_title_original: NotRequired[str]
    reg_image_url: NotRequired[str]
    reg_funding: NotRequired[str]
    reg_conflicts: NotRequired[str]
    reg_data_availability: NotRequired[str]
    reg_registered_date: NotRequired[str]


class WordPressPayload(TypedDict):
    """Payload contract for POST/PATCH to /wp-json/wp/v2/imi_registry."""

    title: str
    status: str
    meta: WordPressMeta
    slug: NotRequired[str]


# Schema.org JSON-LD TypedDict with @-prefixed keys
SchemaJsonLd = TypedDict(
    "SchemaJsonLd",
    {
        "@context": str,
        "@type": str,
        "headline": str,
        "description": str,
        "author": list[dict[str, str]],
        "creativeWorkStatus": NotRequired[str],
        "identifier": NotRequired[str],
        "sameAs": NotRequired[str],
    },
)


class PreprintPayloadAdapter:
    """Pure projections transforming domain instances into wire payloads."""

    @staticmethod
    def to_wordpress(entry: PreprintEntry) -> WordPressPayload:
        """Project a PreprintEntry entity into a WordPress REST API payload by composing field units."""
        author_meta = AuthorMetaUnit.serialize(entry.primary_author, entry.coauthors)
        doi_meta = DoiMetaUnit.serialize(entry.doi_record)
        version_meta = VersionMetaUnit.serialize(entry.version)
        editorial_meta = EditorialStateUnit.serialize(entry.editorial_state)

        meta: WordPressMeta = {
            "reg_author_name": author_meta["reg_author_name"],
            "reg_orcid": author_meta["reg_orcid"],
            "reg_affiliation": author_meta["reg_affiliation"],
            "reg_country": author_meta["reg_country"],
            "reg_abstract": entry.abstract,
            "reg_methodology": entry.methodology,
            "reg_license": LicenseUnit.serialize(entry.license),
            "reg_declaration": entry.declaration,
            "reg_keywords": KeywordsUnit.serialize(entry.keywords),
            "reg_coauthors": author_meta["reg_coauthors"],
            "reg_destination_url": entry.destination_url,
            "reg_published_destination": entry.published_destination,
            "reg_pdf_url": entry.pdf_url,
            "reg_schema_type": entry.schema_type,
            "reg_registry_id": entry.registry_id,
            "reg_pipeline_status": editorial_meta["pipeline_status"],
            "reg_version": int(version_meta["reg_version"]),
            "reg_version_type": str(version_meta["reg_version_type"]),
            "reg_version_history": str(version_meta["reg_version_history"]),
            "reg_prior_versions": str(version_meta["reg_prior_versions"]),
            "reg_doi": doi_meta["reg_doi"],
            "reg_doi_url": doi_meta["reg_doi_url"],
            "reg_doi_status": doi_meta["reg_doi_status"],
            "reg_doi_minted_date": doi_meta["reg_doi_minted_date"],
            "reg_crossref_deposit_id": doi_meta["reg_crossref_deposit_id"],
        }

        if entry.withdrawal_notice:
            meta["reg_withdrawal_notice"] = entry.withdrawal_notice

        payload: WordPressPayload = {
            "title": entry.title,
            "status": editorial_meta["post_status"],
            "meta": meta,
        }
        if entry.slug:
            payload["slug"] = entry.slug

        return payload

    @staticmethod
    def from_wordpress(
        meta: Mapping[str, Any],
        title: str,
        slug: str = "",
        post_status: str = "",
    ) -> PreprintEntry:
        """Hydrate a PreprintEntry from WordPress postmeta dictionary by composing field units."""
        primary_author, coauthors = AuthorMetaUnit.hydrate(meta)
        doi_record = DoiMetaUnit.hydrate(meta)
        version = VersionMetaUnit.hydrate(meta)
        editorial_state = EditorialStateUnit.hydrate(meta, post_status=post_status)
        license_ = LicenseUnit.hydrate(meta)
        keywords = KeywordsUnit.hydrate(meta)

        return PreprintEntry(
            title=title,
            primary_author=primary_author,
            slug=slug,
            editorial_state=editorial_state,
            abstract=str(meta.get("reg_abstract", "")),
            methodology=str(meta.get("reg_methodology", "")),
            license=license_,
            declaration=bool(meta.get("reg_declaration", True)),
            keywords=keywords,
            coauthors=coauthors,
            destination_url=str(meta.get("reg_destination_url", "")),
            published_destination=str(meta.get("reg_published_destination", "Observatory")),
            pdf_url=str(meta.get("reg_pdf_url", "")),
            schema_type=str(meta.get("reg_schema_type", "ScholarlyArticle")),
            registry_id=str(meta.get("reg_registry_id", "")),
            doi_record=doi_record,
            version=version,
            withdrawal_notice=str(meta.get("reg_withdrawal_notice", "")),
        )

    @staticmethod
    def to_jsonld(entry: PreprintEntry) -> SchemaJsonLd:
        """Project a PreprintEntry entity into a Schema.org JSON-LD dictionary.

        Emits creativeWorkStatus for preprint compliance (Gap B) and maps
        both primary and co-authors to Person objects.
        """
        authors = [
            {"@type": "Person", "name": author.name}
            for author in (entry.primary_author, *entry.coauthors)
        ]

        data: SchemaJsonLd = {
            "@context": "https://schema.org",
            "@type": entry.schema_type,
            "headline": entry.title,
            "description": entry.abstract,
            "author": authors,
        }

        creative_status = {
            EditorialState.LIVE_PREPRINT: "Preprint",
            EditorialState.PUBLISHED: "Published",
            EditorialState.WITHDRAWN: "Retracted",
        }.get(entry.editorial_state)

        if creative_status:
            data["creativeWorkStatus"] = creative_status

        if entry.doi_record.doi:
            data["identifier"] = entry.doi_record.doi.url
            data["sameAs"] = entry.doi_record.doi.url

        return data

    @staticmethod
    def to_citation_tags(
        entry: PreprintEntry,
        publisher: str = "Independent Media Institute",
    ) -> list[MetaTag]:
        """Project a PreprintEntry into structured MetaTag intermediate representations.

        Pure data manipulation without text rendering or HTML string interpolation.
        Emits separate citation_author tags for primary author and each coauthor,
        and emits citation_doi only when the DOI status is ACTIVE.
        """
        primary_name = (
            entry.primaryAuthor.name
            if hasattr(entry, "primaryAuthor")
            else entry.primary_author.name
        )
        tags: list[MetaTag] = [
            MetaTag(name="citation_title", content=entry.title),
            MetaTag(name="citation_author", content=primary_name),
        ]

        for coauthor in entry.coauthors:
            tags.append(MetaTag(name="citation_author", content=coauthor.name))

        tags.append(MetaTag(name="citation_publisher", content=publisher))

        if entry.abstract:
            tags.append(MetaTag(name="citation_abstract", content=entry.abstract))

        if entry.keywords:
            tags.append(
                MetaTag(
                    name="citation_keywords",
                    content=join_delimited(entry.keywords, delimiter=", "),
                )
            )

        if entry.destination_url:
            tags.append(
                MetaTag(
                    name="citation_fulltext_html_url",
                    content=entry.destination_url,
                )
            )

        if entry.pdf_url:
            tags.append(MetaTag(name="citation_pdf_url", content=entry.pdf_url))

        if entry.doi_record.status == DOIStatus.ACTIVE and entry.doi_record.doi:
            tags.append(MetaTag(name="citation_doi", content=entry.doi_record.doi.value))

        return tags

    @classmethod
    def to_citation_meta(
        cls,
        entry: PreprintEntry,
        publisher: str = "Independent Media Institute",
    ) -> str:
        """Render Google Scholar citation meta tags from a PreprintEntry.

        Delegates to the domain-agnostic render_meta_tags presentation utility.
        """
        return render_meta_tags(cls.to_citation_tags(entry, publisher))
