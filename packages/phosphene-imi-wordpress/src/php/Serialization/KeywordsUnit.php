<?php

declare(strict_types=1);

namespace Phosphene\ImiWordpress\Serialization;

require_once __DIR__ . '/../Utils/DelimitedListUtil.php';

use Phosphene\ImiWordpress\Utils\DelimitedListUtil;

/**
 * Discrete serialization unit for Keywords in WordPress postmeta.
 */
final class KeywordsUnit
{
    /**
     * @param list<string> $keywords
     */
    public static function serialize(array $keywords): string
    {
        return DelimitedListUtil::joinCommas($keywords);
    }

    /**
     * @param array<string, mixed> $meta
     * @return list<string>
     */
    public static function hydrate(array $meta): array
    {
        $raw = (string)($meta['reg_keywords'] ?? '');
        return DelimitedListUtil::splitCommas($raw);
    }
}
