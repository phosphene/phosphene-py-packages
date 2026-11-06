<?php

declare(strict_types=1);

require_once __DIR__ . '/../../src/php/Domain/ContributorSequence.php';
require_once __DIR__ . '/../../src/php/Domain/License.php';
require_once __DIR__ . '/../../src/php/Domain/DOIStatus.php';
require_once __DIR__ . '/../../src/php/Domain/EditorialState.php';
require_once __DIR__ . '/../../src/php/Domain/Author.php';
require_once __DIR__ . '/../../src/php/Domain/DOI.php';
require_once __DIR__ . '/../../src/php/Domain/DOIRecord.php';
require_once __DIR__ . '/../../src/php/Domain/VersionInfo.php';
require_once __DIR__ . '/../../src/php/Domain/PreprintEntry.php';

use Phosphene\ImiWordpress\Domain\Author;
use Phosphene\ImiWordpress\Domain\ContributorSequence;
use Phosphene\ImiWordpress\Domain\DOI;
use Phosphene\ImiWordpress\Domain\DOIRecord;
use Phosphene\ImiWordpress\Domain\DOIStatus;
use Phosphene\ImiWordpress\Domain\EditorialState;
use Phosphene\ImiWordpress\Domain\License;
use Phosphene\ImiWordpress\Domain\PreprintEntry;
use Phosphene\ImiWordpress\Domain\VersionInfo;

if (!function_exists('assertTrue')) {
    function assertTrue(bool $condition, string $message): void {
        if (!$condition) {
            throw new RuntimeException("Assertion failed: $message");
        }
    }
}

if (!function_exists('assertSame')) {
    function assertSame(mixed $expected, mixed $actual, string $message): void {
        if ($expected !== $actual) {
            $expStr = var_export($expected, true);
            $actStr = var_export($actual, true);
            throw new RuntimeException("Assertion failed: $message (Expected: $expStr, got: $actStr)");
        }
    }
}

class PreprintDomainTest {
    public function testAuthorValueObject(): void {
        $author = new Author(
            name: 'Deborah Barsky',
            orcid: 'https://orcid.org/0000-0002-1234-5678',
            affiliation: 'Institut Catala',
            country: 'Spain',
            sequence: ContributorSequence::FIRST
        );

        assertSame('Deborah Barsky', $author->name, 'author name');
        assertSame('0000-0002-1234-5678', $author->orcid, 'canonicalized orcid');
        assertSame('https://orcid.org/0000-0002-1234-5678', $author->orcidUrl(), 'orcid url');
        assertTrue($author->isPrimary(), 'isPrimary true for first sequence');

        $coauthor = new Author(
            name: 'Co Author',
            sequence: ContributorSequence::ADDITIONAL
        );
        assertTrue(!$coauthor->isPrimary(), 'isPrimary false for additional sequence');

        // Test malformed ORCID throws InvalidArgumentException
        try {
            new Author(name: 'Bad', orcid: 'not-an-orcid');
            assertTrue(false, 'Expected InvalidArgumentException on malformed ORCID');
        } catch (InvalidArgumentException $e) {
            assertTrue(true, 'Malformed ORCID rejected');
        }

        // Test immutability
        try {
            /** @phpstan-ignore-next-line */
            $author->name = 'Mutated';
            assertTrue(false, 'Expected readonly modification error');
        } catch (Error $e) {
            assertTrue(true, 'Readonly class protected');
        }
    }

    public function testDOIValueObject(): void {
        $doi = new DOI(suffix: 'imi.2026.001');
        assertSame('10.67767', $doi->prefix, 'default prefix');
        assertSame('imi.2026.001', $doi->suffix, 'suffix');
        assertSame('10.67767/imi.2026.001', $doi->value(), 'doi value');
        assertSame('https://doi.org/10.67767/imi.2026.001', $doi->url(), 'doi url');
        assertSame('10.67767/imi.2026.001', (string)$doi, 'Stringable implementation');

        // Parsing with protocol stripping
        $parsed = DOI::fromString('https://doi.org/10.67767/imi.2026.042');
        assertSame('10.67767', $parsed->prefix, 'parsed prefix');
        assertSame('imi.2026.042', $parsed->suffix, 'parsed suffix');

        $suffixOnly = DOI::fromString('  imi.2026.099  ');
        assertSame('10.67767', $suffixOnly->prefix, 'parsed suffix prefix');
        assertSame('imi.2026.099', $suffixOnly->suffix, 'parsed suffix trimmed');

        // Equals
        $doi1 = new DOI('imi.2026.001');
        $doi2 = DOI::fromString('https://doi.org/10.67767/imi.2026.001');
        assertTrue($doi1->equals($doi2), 'equals matches canonical values');

        // Invalid syntax throws
        try {
            new DOI('has spaces and ? bad chars');
            assertTrue(false, 'Expected InvalidArgumentException on invalid syntax');
        } catch (InvalidArgumentException $e) {
            assertTrue(true, 'Invalid DOI syntax rejected');
        }
    }

    public function testDOIRecord(): void {
        $record = new DOIRecord();
        assertSame(null, $record->doi, 'default doi is null');
        assertSame(DOIStatus::UNASSIGNED, $record->status, 'default status is unassigned');
        assertTrue(!$record->isMinted(), 'unassigned is not minted');
        assertTrue(!$record->isResolvable(), 'unassigned is not resolvable');

        // State progression
        $doi = new DOI('imi.2026.001');
        $recordWithDoi = new DOIRecord(doi: $doi);
        $pending = $recordWithDoi->withPending('DEP-12345');
        assertSame(DOIStatus::PENDING, $pending->status, 'transitioned to pending');
        assertSame('DEP-12345', $pending->depositId, 'depositId recorded');

        $active = $pending->withActive('2026-11-05');
        assertSame(DOIStatus::ACTIVE, $active->status, 'transitioned to active');
        assertSame('2026-11-05', $active->mintedDate, 'mintedDate recorded');
        assertTrue($active->isMinted(), 'active is minted');
        assertTrue($active->isResolvable(), 'active is resolvable');

        $withdrawn = $active->withWithdrawn();
        assertSame(DOIStatus::WITHDRAWN, $withdrawn->status, 'transitioned to withdrawn');
        assertTrue($withdrawn->isMinted(), 'withdrawn is still minted (tombstone)');
        assertTrue(!$withdrawn->isResolvable(), 'withdrawn is not resolvable');

        // Invariant: ACTIVE requires DOI
        try {
            new DOIRecord(doi: null, status: DOIStatus::ACTIVE);
            assertTrue(false, 'Expected LogicException for ACTIVE DOIRecord without DOI');
        } catch (LogicException $e) {
            assertTrue(true, 'Active without DOI rejected');
        }
    }

    public function testEditorialState(): void {
        $draft = EditorialState::DRAFT;
        assertTrue(!$draft->isPublished(), 'draft is not published');
        assertTrue(!$draft->isReviewing(), 'draft is not reviewing');
        assertTrue($draft->canTransitionTo(EditorialState::PENDING_REVIEW), 'draft -> pending_review');

        $pending = EditorialState::PENDING_REVIEW;
        assertTrue($pending->isReviewing(), 'pending_review is reviewing');
        assertSame('pending', $pending->badgeMode(), 'pending badge mode');

        $underReview = EditorialState::UNDER_REVIEW;
        assertTrue($underReview->isReviewing(), 'under_review is reviewing');
        assertSame('under_review', $underReview->badgeMode(), 'under_review badge mode');

        $live = EditorialState::LIVE_PREPRINT;
        assertTrue($live->isPublished(), 'live_preprint is published');
        assertTrue(!$live->isReviewing(), 'live_preprint is not reviewing');
        assertSame('preprint', $live->badgeMode(), 'preprint badge mode');
    }

    public function testLicense(): void {
        $lic = License::CC_BY_4_0;
        assertSame('https://creativecommons.org/licenses/by/4.0/', $lic->url(), 'CC BY 4.0 URL');
        assertSame('CC-BY-4.0', $lic->spdx(), 'CC BY 4.0 SPDX');
        assertSame(License::CC_BY_NC_SA_4_0, License::fromSpdx('CC-BY-NC-SA-4.0'), 'fromSpdx matches');
    }

    public function testVersionInfo(): void {
        $v1 = new VersionInfo(number: 1);
        assertSame('v1', $v1->formatted(), 'v1 formatted');

        $v2 = $v1->increment('minor', 'fixed typos');
        assertSame(2, $v2->number, 'incremented number');
        assertSame('v2', $v2->formatted(), 'v2 formatted');
        assertSame('fixed typos', $v2->history, 'version history');
        assertSame(['v1'], $v2->priorVersions, 'prior versions tracked');
    }

    public function testPreprintEntry(): void {
        $author = new Author(name: 'Primary Author');
        $coauthor = new Author(name: 'Co Author', sequence: ContributorSequence::ADDITIONAL);

        $entry = new PreprintEntry(
            title: 'Test Preprint Title',
            primaryAuthor: $author,
            coauthors: [$coauthor]
        );

        assertSame(['Primary Author', 'Co Author'], array_map(fn($a) => $a->name, $entry->allAuthors()), 'allAuthors sequence');

        $promoted = $entry->withEditorialState(EditorialState::LIVE_PREPRINT);
        assertSame(EditorialState::LIVE_PREPRINT, $promoted->editorialState, 'wither updated editorial state');
    }
}
