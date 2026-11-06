<?php

declare(strict_types=1);

namespace Phosphene\ImiWordpress\Serialization;

require_once __DIR__ . '/../Domain/EditorialState.php';

use Phosphene\ImiWordpress\Domain\EditorialState;

/**
 * Discrete serialization unit for EditorialState to WP post_status and reg_pipeline_status.
 */
final class EditorialStateUnit
{
    /**
     * @return array{post_status: string, pipeline_status: string}
     */
    public static function serialize(EditorialState $state): array
    {
        $postStatus = $state->isPublished() ? 'publish' : 'draft';
        $pipelineStatus = match ($state) {
            EditorialState::LIVE_PREPRINT => 'preprint',
            EditorialState::PUBLISHED => 'published',
            EditorialState::WITHDRAWN => 'withdrawn',
            EditorialState::PENDING_REVIEW => 'pending_review',
            EditorialState::UNDER_REVIEW => 'under_review',
            default => 'draft',
        };

        return [
            'post_status' => $postStatus,
            'pipeline_status' => $pipelineStatus,
        ];
    }

    /**
     * @param array<string, mixed> $meta
     * @param string $postStatus
     */
    public static function hydrate(array $meta, string $postStatus = ''): EditorialState
    {
        $pipeline = (string)($meta['reg_pipeline_status'] ?? '');
        return match ($pipeline) {
            'preprint' => EditorialState::LIVE_PREPRINT,
            'published' => EditorialState::PUBLISHED,
            'withdrawn' => EditorialState::WITHDRAWN,
            'pending_review' => EditorialState::PENDING_REVIEW,
            'under_review' => EditorialState::UNDER_REVIEW,
            default => $postStatus === 'publish' ? EditorialState::PUBLISHED : EditorialState::DRAFT,
        };
    }
}
