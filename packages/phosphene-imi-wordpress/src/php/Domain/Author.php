<?php

declare(strict_types=1);

namespace Phosphene\ImiWordpress\Domain;

require_once __DIR__ . '/ContributorSequence.php';
require_once __DIR__ . '/../Utils/OrcidPattern.php';

use InvalidArgumentException;
use Phosphene\ImiWordpress\Utils\OrcidPattern;

/**
 * Scholarly contributor value object.
 *
 * Immutable personal, institutional, and sequence metadata shared by primary authors and co-authors.
 */
readonly class Author
{
    public string $orcid;

    public function __construct(
        public string $name,
        string $orcid = '',
        public string $affiliation = '',
        public string $country = '',
        public ContributorSequence $sequence = ContributorSequence::FIRST,
        public string $role = 'author',
    ) {
        $cleanOrcid = OrcidPattern::canonicalize($orcid);
        if ($cleanOrcid !== '' && !OrcidPattern::isValid($cleanOrcid)) {
            throw new InvalidArgumentException("Malformed ORCID: {$orcid}");
        }
        $this->orcid = $cleanOrcid;
    }

    public function orcidUrl(): string
    {
        return OrcidPattern::toUri($this->orcid);
    }

    public function isPrimary(): bool
    {
        return $this->sequence === ContributorSequence::FIRST;
    }

    public function equals(self $other): bool
    {
        return $this->name === $other->name && $this->orcid === $other->orcid;
    }
}
