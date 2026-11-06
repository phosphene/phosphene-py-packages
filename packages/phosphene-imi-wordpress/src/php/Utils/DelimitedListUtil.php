<?php

declare(strict_types=1);

namespace Phosphene\ImiWordpress\Utils;

/**
 * Dedicated utility for parsing and assembling newline- and comma-delimited lists.
 *
 * Enforces strict whitespace trimming, carriage-return scrubbing, and null/empty omission.
 */
final class DelimitedListUtil
{
    /**
     * Parse newline-delimited text into a clean list of trimmed, non-empty strings.
     *
     * @param string $raw
     * @return list<string>
     */
    public static function splitLines(string $raw): array
    {
        if (trim($raw) === '') {
            return [];
        }
        $normalized = str_replace("\r", '', $raw);
        $result = [];
        foreach (explode("\n", $normalized) as $line) {
            $trimmed = trim($line);
            if ($trimmed !== '') {
                $result[] = $trimmed;
            }
        }
        return $result;
    }

    /**
     * Join an array of items with newline delimiters, omitting empty elements.
     *
     * @param array<string|Stringable> $items
     * @return string
     */
    public static function joinLines(array $items): string
    {
        $filtered = [];
        foreach ($items as $item) {
            $trimmed = trim((string)$item);
            if ($trimmed !== '') {
                $filtered[] = $trimmed;
            }
        }
        return implode("\n", $filtered);
    }

    /**
     * Parse comma-delimited text into a clean list of trimmed, non-empty strings.
     *
     * @param string $raw
     * @return list<string>
     */
    public static function splitCommas(string $raw): array
    {
        if (trim($raw) === '') {
            return [];
        }
        $result = [];
        foreach (explode(',', $raw) as $item) {
            $trimmed = trim($item);
            if ($trimmed !== '') {
                $result[] = $trimmed;
            }
        }
        return $result;
    }

    /**
     * Join an array of items with comma delimiters, omitting empty elements.
     *
     * @param array<string|Stringable> $items
     * @return string
     */
    public static function joinCommas(array $items): string
    {
        $filtered = [];
        foreach ($items as $item) {
            $trimmed = trim((string)$item);
            if ($trimmed !== '') {
                $filtered[] = $trimmed;
            }
        }
        return implode(', ', $filtered);
    }
}
