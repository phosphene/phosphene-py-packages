<?php

declare(strict_types=1);

namespace Phosphene\ImiWordpress\Serialization;

require_once __DIR__ . '/../Domain/License.php';

use Phosphene\ImiWordpress\Domain\License;

/**
 * Discrete serialization unit for License in WordPress postmeta.
 */
final class LicenseUnit
{
    public static function serialize(License $license): string
    {
        return $license->value;
    }

    /**
     * @param array<string, mixed> $meta
     */
    public static function hydrate(array $meta): License
    {
        $raw = (string)($meta['reg_license'] ?? '');
        return License::tryFrom($raw) ?? License::CC_BY_NC_SA_4_0;
    }
}
