<?php

declare(strict_types=1);

namespace Phosphene\ImiWordpress\Utils;

/**
 * Dedicated utility for ISO 26324 DOI grammar and protocol prefix handling.
 *
 * Provides discrete operations for syntax validation, protocol stripping,
 * and canonical prefix/suffix decomposition.
 */
final class DoiPattern
{
    /**
     * Standard ISO 26324 syntax regex.
     * Requires prefix starting with '10.' followed by 4 to 9 digits, a slash,
     * and a non-empty suffix of allowable standard characters (including SICI delimiters <>).
     */
    public const DOI_SYNTAX = '#^10\.\d{4,9}/[-._;()/:A-Za-z0-9<>]+$#';

    /**
     * Resolving URL and URI prefixes (case-insensitive).
     */
    public const PROTOCOL_PREFIX = '#^(https?://(dx\.)?doi\.org/|doi:)#i';

    /**
     * Determine if a string matches canonical DOI syntax.
     */
    public static function isValid(string $candidate): bool
    {
        return preg_match(self::DOI_SYNTAX, trim($candidate)) === 1;
    }

    /**
     * Strip leading URL or URI prefixes (e.g. 'https://doi.org/' or 'doi:').
     */
    public static function stripProtocolPrefix(string $raw): string
    {
        $trimmed = trim($raw);
        $stripped = preg_replace(self::PROTOCOL_PREFIX, '', $trimmed);
        return trim((string)$stripped);
    }

    /**
     * Parse and split a DOI into its prefix and suffix parts.
     *
     * @param string $canonicalDoi
     * @return array{prefix: string, suffix: string}|null Null if syntax is invalid
     */
    public static function split(string $canonicalDoi): ?array
    {
        $clean = self::stripProtocolPrefix($canonicalDoi);
        if (!self::isValid($clean)) {
            return null;
        }

        [$prefix, $suffix] = explode('/', $clean, 2);
        return [
            'prefix' => $prefix,
            'suffix' => $suffix,
        ];
    }
}
