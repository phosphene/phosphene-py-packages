<?php

declare(strict_types=1);

namespace Phosphene\ImiWordpress\Domain;

require_once __DIR__ . '/DOI.php';
require_once __DIR__ . '/DOIStatus.php';

use LogicException;

/**
 * Scholarly DOI registration and state record. Pure data.
 */
readonly class DOIRecord
{
    public function __construct(
        public ?DOI $doi = null,
        public DOIStatus $status = DOIStatus::UNASSIGNED,
        public string $mintedDate = '',
        public string $depositId = '',
    ) {
        if ($this->status === DOIStatus::ACTIVE && $this->doi === null) {
            throw new LogicException('An ACTIVE DOIRecord must have a non-null DOI instance.');
        }
    }

    public function isMinted(): bool
    {
        return $this->status->isMinted();
    }

    public function isResolvable(): bool
    {
        return $this->status->isResolvable();
    }

    public function withPending(string $depositId): self
    {
        if (!$this->status->canTransitionTo(DOIStatus::PENDING)) {
            throw new LogicException("Cannot transition DOIRecord from {$this->status->value} to pending.");
        }
        return new self(
            doi: $this->doi,
            status: DOIStatus::PENDING,
            mintedDate: $this->mintedDate,
            depositId: $depositId,
        );
    }

    public function withActive(string $mintedDate): self
    {
        if (!$this->status->canTransitionTo(DOIStatus::ACTIVE)) {
            throw new LogicException("Cannot transition DOIRecord from {$this->status->value} to active.");
        }
        if ($this->doi === null) {
            throw new LogicException('Cannot activate DOIRecord without a assigned DOI.');
        }
        return new self(
            doi: $this->doi,
            status: DOIStatus::ACTIVE,
            mintedDate: $mintedDate,
            depositId: $this->depositId,
        );
    }

    public function withWithdrawn(): self
    {
        if (!$this->status->canTransitionTo(DOIStatus::WITHDRAWN)) {
            throw new LogicException("Cannot transition DOIRecord from {$this->status->value} to withdrawn.");
        }
        return new self(
            doi: $this->doi,
            status: DOIStatus::WITHDRAWN,
            mintedDate: $this->mintedDate,
            depositId: $this->depositId,
        );
    }
}
