<?php

declare(strict_types=1);

namespace Phosphene\ImiWordpress\Domain;

require_once __DIR__ . '/Author.php';
require_once __DIR__ . '/ContributorSequence.php';
require_once __DIR__ . '/DOI.php';
require_once __DIR__ . '/DOIRecord.php';
require_once __DIR__ . '/DOIStatus.php';
require_once __DIR__ . '/EditorialState.php';
require_once __DIR__ . '/License.php';
require_once __DIR__ . '/VersionInfo.php';

/**
 * Pure domain entity representing a scholarly preprint registry record.
 *
 * Models business reality with semantic collections and zero transport knowledge.
 */
readonly class PreprintEntry
{
    /**
     * @param string[] $keywords
     * @param Author[] $coauthors
     */
    public function __construct(
        public string $title,
        public Author $primaryAuthor,
        public string $slug = '',
        public EditorialState $editorialState = EditorialState::DRAFT,
        public string $abstract = '',
        public string $methodology = '',
        public License $license = License::CC_BY_NC_SA_4_0,
        public bool $declaration = true,
        public array $keywords = [],
        public array $coauthors = [],
        public string $destinationUrl = '',
        public string $publishedDestination = 'Observatory',
        public string $pdfUrl = '',
        public string $schemaType = 'ScholarlyArticle',
        public string $registryId = '',
        public DOIRecord $doiRecord = new DOIRecord(),
        public VersionInfo $version = new VersionInfo(),
        public string $withdrawalNotice = '',
    ) {}

    /**
     * Return all contributors in publication sequence (primary followed by co-authors).
     *
     * @return list<Author>
     */
    public function allAuthors(): array
    {
        return [$this->primaryAuthor, ...$this->coauthors];
    }

    public function withEditorialState(EditorialState $state): self
    {
        return new self(
            title: $this->title,
            primaryAuthor: $this->primaryAuthor,
            slug: $this->slug,
            editorialState: $state,
            abstract: $this->abstract,
            methodology: $this->methodology,
            license: $this->license,
            declaration: $this->declaration,
            keywords: $this->keywords,
            coauthors: $this->coauthors,
            destinationUrl: $this->destinationUrl,
            publishedDestination: $this->publishedDestination,
            pdfUrl: $this->pdfUrl,
            schemaType: $this->schemaType,
            registryId: $this->registryId,
            doiRecord: $this->doiRecord,
            version: $this->version,
            withdrawalNotice: $this->withdrawalNotice,
        );
    }

    public function withDoiRecord(DOIRecord $doiRecord): self
    {
        return new self(
            title: $this->title,
            primaryAuthor: $this->primaryAuthor,
            slug: $this->slug,
            editorialState: $this->editorialState,
            abstract: $this->abstract,
            methodology: $this->methodology,
            license: $this->license,
            declaration: $this->declaration,
            keywords: $this->keywords,
            coauthors: $this->coauthors,
            destinationUrl: $this->destinationUrl,
            publishedDestination: $this->publishedDestination,
            pdfUrl: $this->pdfUrl,
            schemaType: $this->schemaType,
            registryId: $this->registryId,
            doiRecord: $doiRecord,
            version: $this->version,
            withdrawalNotice: $this->withdrawalNotice,
        );
    }
}
