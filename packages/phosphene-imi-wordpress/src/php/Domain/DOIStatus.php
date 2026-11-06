<?php

declare(strict_types=1);

namespace Phosphene\ImiWordpress\Domain;

/**
 * Lifecycle status of a Digital Object Identifier.
 */
enum DOIStatus: string
{
    case UNASSIGNED = 'unassigned';
    case PENDING = 'pending';
    case ACTIVE = 'active';
    case WITHDRAWN = 'withdrawn';

    /**
     * Determine if a transition to the target status is permitted by the lifecycle state machine.
     */
    public function canTransitionTo(self $target): bool
    {
        return match ($this) {
            self::UNASSIGNED => $target === self::PENDING,
            self::PENDING => $target === self::ACTIVE || $target === self::UNASSIGNED,
            self::ACTIVE => $target === self::WITHDRAWN,
            self::WITHDRAWN => false,
        };
    }

    /**
     * True if the DOI has been minted with Crossref.
     */
    public function isMinted(): bool
    {
        return $this === self::ACTIVE || $this === self::WITHDRAWN;
    }

    /**
     * True if the DOI should resolve to a public landing page.
     */
    public function isResolvable(): bool
    {
        return $this === self::ACTIVE;
    }
}
