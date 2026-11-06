<?php

declare(strict_types=1);

namespace Phosphene\ImiWordpress\Domain;

use InvalidArgumentException;

/**
 * Preprint version lineage value object.
 */
readonly class VersionInfo
{
    /**
     * @param string[] $priorVersions
     */
    public function __construct(
        public int $number = 1,
        public string $versionType = 'major',
        public string $history = '',
        public array $priorVersions = [],
    ) {
        if ($this->number < 1) {
            throw new InvalidArgumentException("Version number must be positive: {$this->number}");
        }
    }

    public function formatted(): string
    {
        return "v{$this->number}";
    }

    public function increment(string $type = 'major', string $notes = ''): self
    {
        $newPrior = array_values(array_unique([...$this->priorVersions, $this->formatted()]));
        return new self(
            number: $this->number + 1,
            versionType: $type,
            history: $notes,
            priorVersions: $newPrior,
        );
    }
}
