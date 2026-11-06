<?php

declare(strict_types=1);

require_once __DIR__ . '/../../src/php/Domain/Author.php';
require_once __DIR__ . '/../../src/php/Domain/ContributorSequence.php';
require_once __DIR__ . '/../../src/php/Domain/DOI.php';
require_once __DIR__ . '/../../src/php/Domain/DOIRecord.php';
require_once __DIR__ . '/../../src/php/Domain/DOIStatus.php';
require_once __DIR__ . '/../../src/php/Domain/EditorialState.php';
require_once __DIR__ . '/../../src/php/Domain/License.php';
require_once __DIR__ . '/../../src/php/Domain/VersionInfo.php';

require_once __DIR__ . '/../../src/php/Serialization/AuthorMetaUnit.php';
require_once __DIR__ . '/../../src/php/Serialization/DoiMetaUnit.php';
require_once __DIR__ . '/../../src/php/Serialization/VersionMetaUnit.php';
require_once __DIR__ . '/../../src/php/Serialization/EditorialStateUnit.php';
require_once __DIR__ . '/../../src/php/Serialization/LicenseUnit.php';
require_once __DIR__ . '/../../src/php/Serialization/KeywordsUnit.php';

use Phosphene\ImiWordpress\Domain\Author;
use Phosphene\ImiWordpress\Domain\ContributorSequence;
use Phosphene\ImiWordpress\Domain\DOI;
use Phosphene\ImiWordpress\Domain\DOIRecord;
use Phosphene\ImiWordpress\Domain\DOIStatus;
use Phosphene\ImiWordpress\Domain\EditorialState;
use Phosphene\ImiWordpress\Domain\License;
use Phosphene\ImiWordpress\Domain\VersionInfo;
use Phosphene\ImiWordpress\Serialization\AuthorMetaUnit;
use Phosphene\ImiWordpress\Serialization\DoiMetaUnit;
use Phosphene\ImiWordpress\Serialization\EditorialStateUnit;
use Phosphene\ImiWordpress\Serialization\KeywordsUnit;
use Phosphene\ImiWordpress\Serialization\LicenseUnit;
use Phosphene\ImiWordpress\Serialization\VersionMetaUnit;

class SerializationUnitsTest
{
    public function testAuthorMetaUnit(): void
    {
        $primary = new Author(
            name: 'Dr. Jane Smith',
            orcid: '0000-0002-1825-0097',
            affiliation: 'MIT',
            country: 'US',
            sequence: ContributorSequence::FIRST
        );
        $coauthors = [
            new Author(name: 'Alice Coauthor', sequence: ContributorSequence::ADDITIONAL),
            new Author(name: 'Bob Coauthor', sequence: ContributorSequence::ADDITIONAL),
        ];

        $serialized = AuthorMetaUnit::serialize($primary, $coauthors);
        assertSame('Dr. Jane Smith', $serialized['reg_author_name'], 'primary name');
        assertSame('0000-0002-1825-0097', $serialized['reg_orcid'], 'primary orcid');
        assertSame("Alice Coauthor\nBob Coauthor", $serialized['reg_coauthors'], 'joined coauthors');

        $hydrated = AuthorMetaUnit::hydrate($serialized);
        assertSame($primary->name, $hydrated['primaryAuthor']->name, 'hydrated primary name');
        assertSame($primary->orcid, $hydrated['primaryAuthor']->orcid, 'hydrated primary orcid');
        assertSame(2, count($hydrated['coauthors']), 'hydrated coauthors count');
        assertSame('Alice Coauthor', $hydrated['coauthors'][0]->name, 'first coauthor name');
        assertSame(ContributorSequence::ADDITIONAL, $hydrated['coauthors'][0]->sequence, 'first coauthor sequence');
    }

    public function testDoiMetaUnit(): void
    {
        $doi = new DOI('imi.2026.042');
        $record = new DOIRecord(
            doi: $doi,
            status: DOIStatus::ACTIVE,
            mintedDate: '2026-11-05',
            depositId: 'DEP-888'
        );

        $serialized = DoiMetaUnit::serialize($record);
        assertSame('10.67767/imi.2026.042', $serialized['reg_doi'], 'doi string');
        assertSame('https://doi.org/10.67767/imi.2026.042', $serialized['reg_doi_url'], 'doi url');
        assertSame('active', $serialized['reg_doi_status'], 'doi status');

        $hydrated = DoiMetaUnit::hydrate($serialized);
        assertTrue($hydrated->doi !== null, 'hydrated doi not null');
        assertSame('10.67767/imi.2026.042', $hydrated->doi->value(), 'hydrated doi value');
        assertSame(DOIStatus::ACTIVE, $hydrated->status, 'hydrated status active');
        assertSame('2026-11-05', $hydrated->mintedDate, 'hydrated minted date');
    }

    public function testVersionMetaUnit(): void
    {
        $v = new VersionInfo(
            number: 2,
            versionType: 'minor',
            history: 'revised abstract',
            priorVersions: ['v1']
        );

        $serialized = VersionMetaUnit::serialize($v);
        assertSame(2, $serialized['reg_version'], 'version number');
        assertSame('v1', $serialized['reg_prior_versions'], 'prior versions');

        $hydrated = VersionMetaUnit::hydrate($serialized);
        assertSame(2, $hydrated->number, 'hydrated number');
        assertSame('minor', $hydrated->versionType, 'hydrated type');
        assertSame(['v1'], $hydrated->priorVersions, 'hydrated priors');
    }

    public function testEditorialStateUnit(): void
    {
        $serialized = EditorialStateUnit::serialize(EditorialState::LIVE_PREPRINT);
        assertSame('publish', $serialized['post_status'], 'post_status publish');
        assertSame('preprint', $serialized['pipeline_status'], 'pipeline_status preprint');

        $hydrated = EditorialStateUnit::hydrate(['reg_pipeline_status' => 'preprint']);
        assertSame(EditorialState::LIVE_PREPRINT, $hydrated, 'hydrated live preprint');
    }

    public function testLicenseUnit(): void
    {
        $serialized = LicenseUnit::serialize(License::CC_BY_4_0);
        assertSame('CC BY 4.0', $serialized, 'serialized license');

        $hydrated = LicenseUnit::hydrate(['reg_license' => 'CC BY 4.0']);
        assertSame(License::CC_BY_4_0, $hydrated, 'hydrated license');
    }

    public function testKeywordsUnit(): void
    {
        $keywords = ['astronomy', 'spectroscopy', 'interferometry'];
        $serialized = KeywordsUnit::serialize($keywords);
        assertSame('astronomy, spectroscopy, interferometry', $serialized, 'joined keywords');

        $hydrated = KeywordsUnit::hydrate(['reg_keywords' => $serialized]);
        assertSame($keywords, $hydrated, 'hydrated keywords');
    }
}
