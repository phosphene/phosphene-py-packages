<?php

declare(strict_types=1);

namespace Phosphene\ImiWordpress\Domain;

/**
 * Jan's 5-state preprint editorial lifecycle plus withdrawal.
 */
enum EditorialState: string
{
    case DRAFT = 'draft';
    case PENDING_REVIEW = 'pending_review';
    case UNDER_REVIEW = 'under_review';
    case LIVE_PREPRINT = 'live_preprint';
    case PUBLISHED = 'published';
    case WITHDRAWN = 'withdrawn';

    /**
     * True if the state requires a publicly indexable landing page.
     */
    public function isPublished(): bool
    {
        return match ($this) {
            self::LIVE_PREPRINT, self::PUBLISHED, self::WITHDRAWN => true,
            default => false,
        };
    }

    /**
     * True if the article is actively in peer or editorial review.
     */
    public function isReviewing(): bool
    {
        return $this === self::PENDING_REVIEW || $this === self::UNDER_REVIEW;
    }

    /**
     * Determine if a transition to the target state is permitted.
     */
    public function canTransitionTo(self $target): bool
    {
        return match ($this) {
            self::DRAFT => $target === self::PENDING_REVIEW || $target === self::LIVE_PREPRINT,
            self::PENDING_REVIEW => $target === self::UNDER_REVIEW || $target === self::DRAFT,
            self::UNDER_REVIEW => $target === self::LIVE_PREPRINT || $target === self::DRAFT,
            self::LIVE_PREPRINT => $target === self::PUBLISHED || $target === self::WITHDRAWN,
            self::PUBLISHED => $target === self::WITHDRAWN,
            self::WITHDRAWN => false,
        };
    }

    /**
     * Visual advisory token corresponding to this editorial state.
     */
    public function badgeMode(): string
    {
        return match ($this) {
            self::DRAFT => 'draft',
            self::PENDING_REVIEW => 'pending',
            self::UNDER_REVIEW => 'under_review',
            self::LIVE_PREPRINT => 'preprint',
            self::PUBLISHED => 'published',
            self::WITHDRAWN => 'withdrawn',
        };
    }
}
