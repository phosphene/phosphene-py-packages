<?php

declare(strict_types=1);

namespace Phosphene\ImiWordpress\Domain;

use InvalidArgumentException;

/**
 * Scholarly publication licenses.
 */
enum License: string
{
    case CC_BY_NC_SA_4_0 = 'CC BY-NC-SA 4.0';
    case CC_BY_4_0 = 'CC BY 4.0';
    case CC0_1_0 = 'CC0 1.0';

    /**
     * Canonical Creative Commons URI.
     */
    public function url(): string
    {
        return match ($this) {
            self::CC_BY_NC_SA_4_0 => 'https://creativecommons.org/licenses/by-nc-sa/4.0/',
            self::CC_BY_4_0 => 'https://creativecommons.org/licenses/by/4.0/',
            self::CC0_1_0 => 'https://creativecommons.org/publicdomain/zero/1.0/',
        };
    }

    /**
     * Standard SPDX identifier.
     */
    public function spdx(): string
    {
        return match ($this) {
            self::CC_BY_NC_SA_4_0 => 'CC-BY-NC-SA-4.0',
            self::CC_BY_4_0 => 'CC-BY-4.0',
            self::CC0_1_0 => 'CC0-1.0',
        };
    }

    public static function fromSpdx(string $spdx): self
    {
        $normalized = strtoupper(trim($spdx));
        return match ($normalized) {
            'CC-BY-NC-SA-4.0' => self::CC_BY_NC_SA_4_0,
            'CC-BY-4.0' => self::CC_BY_4_0,
            'CC0-1.0' => self::CC0_1_0,
            default => throw new InvalidArgumentException("Unknown SPDX license identifier: {$spdx}"),
        };
    }
}
