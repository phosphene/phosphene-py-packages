<?php

declare(strict_types=1);

namespace Phosphene\ImiWordpress\Adapters\WordPress;

require_once __DIR__ . '/../../Domain/PreprintEntry.php';
require_once __DIR__ . '/../../Serialization/AuthorMetaUnit.php';
require_once __DIR__ . '/../../Serialization/DoiMetaUnit.php';
require_once __DIR__ . '/../../Serialization/VersionMetaUnit.php';
require_once __DIR__ . '/../../Serialization/EditorialStateUnit.php';
require_once __DIR__ . '/../../Serialization/LicenseUnit.php';
require_once __DIR__ . '/../../Serialization/KeywordsUnit.php';

use Phosphene\ImiWordpress\Domain\PreprintEntry;
use Phosphene\ImiWordpress\Serialization\AuthorMetaUnit;
use Phosphene\ImiWordpress\Serialization\DoiMetaUnit;
use Phosphene\ImiWordpress\Serialization\EditorialStateUnit;
use Phosphene\ImiWordpress\Serialization\KeywordsUnit;
use Phosphene\ImiWordpress\Serialization\LicenseUnit;
use Phosphene\ImiWordpress\Serialization\VersionMetaUnit;

/**
 * Pure orchestrator constructing domain PreprintEntry instances by composing discrete serialization units.
 */
final class PostMetaHydrator
{
    /**
     * Hydrate a PreprintEntry from a post title and meta key-value array.
     *
     * @param string $title
     * @param array<string, mixed> $meta WordPress postmeta dictionary
     * @param string $slug
     * @return PreprintEntry
     */
    public static function fromMeta(string $title, array $meta, string $slug = ''): PreprintEntry
    {
        $authorData = AuthorMetaUnit::hydrate($meta);
        $doiRecord = DoiMetaUnit::hydrate($meta);
        $version = VersionMetaUnit::hydrate($meta);
        $editorialState = EditorialStateUnit::hydrate($meta);
        $license = LicenseUnit::hydrate($meta);
        $keywords = KeywordsUnit::hydrate($meta);

        return new PreprintEntry(
            title: $title,
            primaryAuthor: $authorData['primaryAuthor'],
            slug: $slug,
            editorialState: $editorialState,
            abstract: (string)($meta['reg_abstract'] ?? ''),
            methodology: (string)($meta['reg_methodology'] ?? ''),
            license: $license,
            declaration: (bool)($meta['reg_declaration'] ?? true),
            keywords: $keywords,
            coauthors: $authorData['coauthors'],
            destinationUrl: (string)($meta['reg_destination_url'] ?? ''),
            publishedDestination: (string)($meta['reg_published_destination'] ?? 'Observatory'),
            pdfUrl: (string)($meta['reg_pdf_url'] ?? ''),
            schemaType: (string)($meta['reg_schema_type'] ?? 'ScholarlyArticle'),
            registryId: (string)($meta['reg_registry_id'] ?? ''),
            doiRecord: $doiRecord,
            version: $version,
            withdrawalNotice: (string)($meta['reg_withdrawal_notice'] ?? ''),
        );
    }
}
