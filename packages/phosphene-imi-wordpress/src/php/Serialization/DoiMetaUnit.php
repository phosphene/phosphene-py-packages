<?php

declare(strict_types=1);

namespace Phosphene\ImiWordpress\Serialization;

require_once __DIR__ . '/../Domain/DOI.php';
require_once __DIR__ . '/../Domain/DOIRecord.php';
require_once __DIR__ . '/../Domain/DOIStatus.php';

use Phosphene\ImiWordpress\Domain\DOI;
use Phosphene\ImiWordpress\Domain\DOIRecord;
use Phosphene\ImiWordpress\Domain\DOIStatus;

/**
 * Discrete serialization unit for DOIRecord and lifecycle status in WordPress postmeta.
 */
final class DoiMetaUnit
{
    /**
     * @return array<string, string>
     */
    public static function serialize(DOIRecord $record): array
    {
        return [
            'reg_doi' => $record->doi !== null ? $record->doi->value() : '',
            'reg_doi_url' => $record->doi !== null ? $record->doi->url() : '',
            'reg_doi_status' => $record->status->value,
            'reg_doi_minted_date' => $record->mintedDate,
            'reg_crossref_deposit_id' => $record->depositId,
        ];
    }

    /**
     * @param array<string, mixed> $meta
     */
    public static function hydrate(array $meta): DOIRecord
    {
        $rawDoi = trim((string)($meta['reg_doi'] ?? ''));
        $doi = $rawDoi !== '' ? DOI::fromString($rawDoi) : null;

        $rawStatus = (string)($meta['reg_doi_status'] ?? '');
        $status = DOIStatus::tryFrom($rawStatus) ?? DOIStatus::UNASSIGNED;

        // Invariant guard: if ACTIVE but no DOI, status reverts to UNASSIGNED to prevent invalid state
        if ($status === DOIStatus::ACTIVE && $doi === null) {
            $status = DOIStatus::UNASSIGNED;
        }

        return new DOIRecord(
            doi: $doi,
            status: $status,
            mintedDate: (string)($meta['reg_doi_minted_date'] ?? ''),
            depositId: (string)($meta['reg_crossref_deposit_id'] ?? ''),
        );
    }
}
