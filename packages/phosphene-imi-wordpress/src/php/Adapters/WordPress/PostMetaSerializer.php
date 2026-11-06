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
 * Pure orchestrator serializing a domain PreprintEntry instance into WordPress postmeta.
 */
final class PostMetaSerializer
{
    /**
     * @return array<string, mixed>
     */
    public static function toMeta(PreprintEntry $entry): array
    {
        $editorialData = EditorialStateUnit::serialize($entry->editorialState);

        return array_merge(
            AuthorMetaUnit::serialize($entry->primaryAuthor, $entry->coauthors),
            DoiMetaUnit::serialize($entry->doiRecord),
            VersionMetaUnit::serialize($entry->version),
            [
                'reg_pipeline_status' => $editorialData['pipeline_status'],
                'reg_license' => LicenseUnit::serialize($entry->license),
                'reg_keywords' => KeywordsUnit::serialize($entry->keywords),
                'reg_abstract' => $entry->abstract,
                'reg_methodology' => $entry->methodology,
                'reg_declaration' => $entry->declaration,
                'reg_destination_url' => $entry->destinationUrl,
                'reg_published_destination' => $entry->publishedDestination,
                'reg_pdf_url' => $entry->pdfUrl,
                'reg_schema_type' => $entry->schemaType,
                'reg_registry_id' => $entry->registryId,
                'reg_withdrawal_notice' => $entry->withdrawalNotice,
            ]
        );
    }
}
