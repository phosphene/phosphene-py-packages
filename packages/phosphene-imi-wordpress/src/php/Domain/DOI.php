<?php

declare(strict_types=1);

namespace Phosphene\ImiWordpress\Domain;

require_once __DIR__ . '/../Utils/DoiPattern.php';

use InvalidArgumentException;
use Phosphene\ImiWordpress\Utils\DoiPattern;
use Stringable;

/**
 * Scholarly Digital Object Identifier value object.
 *
 * Constructive, immutable, and strictly validated against ISO 26324 syntax.
 * Defaults to IMI's Crossref prefix (10.67767).
 */
readonly class DOI implements Stringable
{
    public const DEFAULT_PREFIX = '10.67767';

    public function __construct(
        public string $suffix,
        public string $prefix = self::DEFAULT_PREFIX,
    ) {
        $trimmedSuffix = trim($this->suffix);
        $trimmedPrefix = trim($this->prefix);

        if (!DoiPattern::isValid("{$trimmedPrefix}/{$trimmedSuffix}")) {
            throw new InvalidArgumentException("Malformed DOI: {$trimmedPrefix}/{$trimmedSuffix}");
        }
    }

    public function value(): string
    {
        return "{$this->prefix}/{$this->suffix}";
    }

    public function url(): string
    {
        return "https://doi.org/{$this->value()}";
    }

    public function __toString(): string
    {
        return $this->value();
    }

    public function equals(self $other): bool
    {
        return strcasecmp($this->value(), $other->value()) === 0;
    }

    public static function fromString(string $raw): self
    {
        $clean = DoiPattern::stripProtocolPrefix($raw);
        if (str_contains($clean, '/')) {
            [$prefix, $suffix] = explode('/', $clean, 2);
            return new self($suffix, $prefix);
        }
        return new self($clean);
    }
}
