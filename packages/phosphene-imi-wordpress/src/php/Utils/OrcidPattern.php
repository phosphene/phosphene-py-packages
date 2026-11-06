<?php

declare(strict_types=1);

namespace Phosphene\ImiWordpress\Utils;

/**
 * Dedicated utility for ISO 27729 (ISNI) ORCID identifier syntax and URI resolution.
 *
 * Provides discrete operations for syntax validation, URI prefix stripping,
 * and canonical URI generation.
 */
final class OrcidPattern
{
    /**
     * Standard 16-character hyphenated ORCID syntax with check digit (0-9 or X).
     */
    public const ORCID_SYNTAX = '#^\d{4}-\d{4}-\d{4}-\d{3}[\dX]$#';

    /**
     * Resolving URI prefixes (case-insensitive).
     */
    public const URI_PREFIX = '#^https?://orcid\.org/#i';

    /**
     * Determine if a string matches canonical ORCID syntax.
     */
    public static function isValid(string $candidate): bool
    {
        return preg_match(self::ORCID_SYNTAX, trim($candidate)) === 1;
    }

    /**
     * Strip leading URI prefix (e.g. 'https://orcid.org/') and return canonical digits.
     */
    public static function canonicalize(string $raw): string
    {
        $trimmed = trim($raw);
        $stripped = preg_replace(self::URI_PREFIX, '', $trimmed);
        return trim((string)$stripped);
    }

    /**
     * Format a canonical ORCID into its full permanent URI.
     */
    public static function toUri(string $orcid): string
    {
        $clean = self::canonicalize($orcid);
        if ($clean === '') {
            return '';
        }
        return "https://orcid.org/{$clean}";
    }
}
