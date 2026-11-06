<?php

declare(strict_types=1);

namespace Phosphene\ImiWordpress\Serialization;

require_once __DIR__ . '/../Domain/VersionInfo.php';
require_once __DIR__ . '/../Utils/DelimitedListUtil.php';

use Phosphene\ImiWordpress\Domain\VersionInfo;
use Phosphene\ImiWordpress\Utils\DelimitedListUtil;

/**
 * Discrete serialization unit for VersionInfo in WordPress postmeta.
 */
final class VersionMetaUnit
{
    /**
     * @return array<string, mixed>
     */
    public static function serialize(VersionInfo $version): array
    {
        return [
            'reg_version' => $version->number,
            'reg_version_type' => $version->versionType,
            'reg_version_history' => $version->history,
            'reg_prior_versions' => DelimitedListUtil::joinLines($version->priorVersions),
        ];
    }

    /**
     * @param array<string, mixed> $meta
     */
    public static function hydrate(array $meta): VersionInfo
    {
        $rawNum = (int)($meta['reg_version'] ?? 1);
        $number = max(1, $rawNum);

        $versionType = (string)($meta['reg_version_type'] ?? 'major');
        $history = (string)($meta['reg_version_history'] ?? '');
        $rawPriors = (string)($meta['reg_prior_versions'] ?? '');
        $priorVersions = DelimitedListUtil::splitLines($rawPriors);

        return new VersionInfo(
            number: $number,
            versionType: $versionType !== '' ? $versionType : 'major',
            history: $history,
            priorVersions: $priorVersions,
        );
    }
}
