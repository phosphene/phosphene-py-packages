<?php

declare(strict_types=1);

require_once __DIR__ . '/../../src/php/Domain/License.php';
require_once __DIR__ . '/../../src/php/Domain/DOIStatus.php';
require_once __DIR__ . '/../../src/php/Domain/EditorialState.php';
require_once __DIR__ . '/../../src/php/Domain/Author.php';
require_once __DIR__ . '/../../src/php/Domain/DOI.php';
require_once __DIR__ . '/../../src/php/Domain/DOIRecord.php';
require_once __DIR__ . '/../../src/php/Domain/VersionInfo.php';
require_once __DIR__ . '/../../src/php/Domain/PreprintEntry.php';
require_once __DIR__ . '/../../src/php/Adapters/WordPress/PostMetaHydrator.php';
require_once __DIR__ . '/../../src/php/Adapters/Scholarly/GoogleScholarAdapter.php';
require_once __DIR__ . '/../../src/php/Adapters/Scholarly/SchemaJsonLdAdapter.php';

use Phosphene\ImiWordpress\Adapters\Scholarly\GoogleScholarAdapter;
use Phosphene\ImiWordpress\Adapters\Scholarly\SchemaJsonLdAdapter;
use Phosphene\ImiWordpress\Adapters\WordPress\PostMetaHydrator;
use Phosphene\ImiWordpress\Domain\Author;
use Phosphene\ImiWordpress\Domain\DOI;
use Phosphene\ImiWordpress\Domain\DOIRecord;
use Phosphene\ImiWordpress\Domain\DOIStatus;
use Phosphene\ImiWordpress\Domain\EditorialState;
use Phosphene\ImiWordpress\Domain\PreprintEntry;

class ScholarlyAdaptersTest {
    public function testPostMetaHydratorFromGoldenMeta(): void {
        $meta = [
            'reg_author_name' => 'Barsky, Deborah',
            'reg_orcid' => '0000-0002-1234-5678',
            'reg_affiliation' => 'Institut Catala',
            'reg_country' => 'Spain',
            'reg_abstract' => 'This study examines early tool manufacture.',
            'reg_methodology' => 'empirical',
            'reg_license' => 'CC BY-NC-SA 4.0',
            'reg_declaration' => true,
            'reg_keywords' => 'paleoanthropology, tool use, Oldowan',
            'reg_coauthors' => "Lumley, Henry de\nCeliberti, Vincenzo",
            'reg_destination_url' => 'https://observatory.wiki/Tool_Use',
            'reg_published_destination' => 'Observatory',
            'reg_pdf_url' => 'https://ind.media/pdf/tool-use-v1.pdf',
            'reg_schema_type' => 'ScholarlyArticle',
            'reg_registry_id' => 'IMI-2026-001',
            'reg_pipeline_status' => 'preprint',
            'reg_version' => 1,
            'reg_version_type' => 'major',
            'reg_version_history' => 'Initial preprint release',
            'reg_prior_versions' => '',
            'reg_doi' => '10.67767/imi.2026.001',
            'reg_doi_url' => 'https://doi.org/10.67767/imi.2026.001',
            'reg_doi_status' => 'active',
            'reg_doi_minted_date' => '2026-07-15',
            'reg_crossref_deposit_id' => 'cr-dep-100',
        ];

        $entry = PostMetaHydrator::fromMeta('On the Origins of Tool Use', $meta, 'origins-of-tool-use');

        assertSame('On the Origins of Tool Use', $entry->title, 'title matches');
        assertSame('origins-of-tool-use', $entry->slug, 'slug matches');
        assertSame('Barsky, Deborah', $entry->primaryAuthor->name, 'primary author name');
        assertSame('0000-0002-1234-5678', $entry->primaryAuthor->orcid, 'primary author orcid');
        assertSame(EditorialState::LIVE_PREPRINT, $entry->editorialState, 'state mapped to LIVE_PREPRINT');

        // Keywords
        assertSame(['paleoanthropology', 'tool use', 'Oldowan'], $entry->keywords, 'keywords parsed');

        // Coauthors
        assertSame(2, count($entry->coauthors), '2 coauthors parsed');
        assertSame('Lumley, Henry de', $entry->coauthors[0]->name, 'coauthor 1');
        assertSame('Celiberti, Vincenzo', $entry->coauthors[1]->name, 'coauthor 2');

        // DOI Record
        assertSame('10.67767/imi.2026.001', $entry->doiRecord->doi?->value(), 'doi value');
        assertSame(DOIStatus::ACTIVE, $entry->doiRecord->status, 'doi active');
        assertSame('cr-dep-100', $entry->doiRecord->depositId, 'deposit id');
    }

    public function testGoogleScholarAdapterActiveDoi(): void {
        $author = new Author(name: 'Alice Smith');
        $co1 = new Author(name: 'Bob Jones');
        $co2 = new Author(name: 'Carol White');

        $entry = new PreprintEntry(
            title: 'Hydrogen Power in Heavy Industry',
            primaryAuthor: $author,
            abstract: 'An in-depth study of industrial decarbonization.',
            keywords: ['energy', 'hydrogen'],
            coauthors: [$co1, $co2],
            destinationUrl: 'https://observatory.wiki/Heavy_Industry',
            pdfUrl: 'https://ind.media/pdf/industry-v1.pdf',
            doiRecord: new DOIRecord(
                doi: new DOI(suffix: 'imi.2026.042'),
                status: DOIStatus::ACTIVE
            )
        );

        $html = GoogleScholarAdapter::render($entry);

        assertTrue(str_contains($html, '<meta name="citation_title" content="Hydrogen Power in Heavy Industry" />'), 'has citation_title');
        assertTrue(str_contains($html, '<meta name="citation_author" content="Alice Smith" />'), 'has primary author');
        assertTrue(str_contains($html, '<meta name="citation_author" content="Bob Jones" />'), 'has coauthor 1');
        assertTrue(str_contains($html, '<meta name="citation_author" content="Carol White" />'), 'has coauthor 2');
        assertTrue(str_contains($html, '<meta name="citation_publisher" content="Independent Media Institute" />'), 'has publisher');
        assertTrue(str_contains($html, '<meta name="citation_abstract" content="An in-depth study of industrial decarbonization." />'), 'has abstract');
        assertTrue(str_contains($html, '<meta name="citation_keywords" content="energy, hydrogen" />'), 'has keywords');
        assertTrue(str_contains($html, '<meta name="citation_fulltext_html_url" content="https://observatory.wiki/Heavy_Industry" />'), 'has fulltext url');
        assertTrue(str_contains($html, '<meta name="citation_pdf_url" content="https://ind.media/pdf/industry-v1.pdf" />'), 'has pdf url');
        assertTrue(str_contains($html, '<meta name="citation_doi" content="10.67767/imi.2026.042" />'), 'has active doi');
    }

    public function testGoogleScholarAdapterPendingDoiOmitted(): void {
        $entry = new PreprintEntry(
            title: 'Pending Article',
            primaryAuthor: new Author(name: 'Alice Smith'),
            doiRecord: new DOIRecord(
                doi: new DOI(suffix: 'imi.2026.099'),
                status: DOIStatus::PENDING
            )
        );

        $html = GoogleScholarAdapter::render($entry);
        assertTrue(!str_contains($html, 'citation_doi'), 'pending doi is not rendered');
    }

    public function testSchemaJsonLdCreativeWorkStatusPreprint(): void {
        $entry = new PreprintEntry(
            title: 'Preprint Title',
            primaryAuthor: new Author(name: 'Author One'),
            editorialState: EditorialState::LIVE_PREPRINT,
            abstract: 'Sample abstract',
            doiRecord: new DOIRecord(
                doi: new DOI(suffix: 'imi.2026.001'),
                status: DOIStatus::ACTIVE
            )
        );

        $jsonLd = SchemaJsonLdAdapter::build($entry);

        assertSame('https://schema.org', $jsonLd['@context'], 'context matches');
        assertSame('ScholarlyArticle', $jsonLd['@type'], 'type matches');
        assertSame('Preprint Title', $jsonLd['headline'], 'headline matches');
        assertSame('Preprint', $jsonLd['creativeWorkStatus'], 'creativeWorkStatus is Preprint (Gap B fix)');
        assertSame('https://doi.org/10.67767/imi.2026.001', $jsonLd['identifier'], 'identifier is doi url');
        assertSame('https://doi.org/10.67767/imi.2026.001', $jsonLd['sameAs'], 'sameAs is doi url');
    }

    public function testSchemaJsonLdCreativeWorkStatusRetracted(): void {
        $entry = new PreprintEntry(
            title: 'Withdrawn Title',
            primaryAuthor: new Author(name: 'Author One'),
            editorialState: EditorialState::WITHDRAWN
        );

        $jsonLd = SchemaJsonLdAdapter::build($entry);
        assertSame('Retracted', $jsonLd['creativeWorkStatus'], 'creativeWorkStatus is Retracted');
    }

    public function testSchemaJsonLdDraftOmitsCreativeWorkStatus(): void {
        $entry = new PreprintEntry(
            title: 'Draft Title',
            primaryAuthor: new Author(name: 'Author One'),
            editorialState: EditorialState::DRAFT
        );

        $jsonLd = SchemaJsonLdAdapter::build($entry);
        assertTrue(!isset($jsonLd['creativeWorkStatus']), 'draft omits creativeWorkStatus');
    }

    public function testPostMetaSerializerRoundtrip(): void {
        require_once __DIR__ . '/../../src/php/Adapters/WordPress/PostMetaSerializer.php';
        $meta = [
            'reg_author_name' => 'Barsky, Deborah',
            'reg_orcid' => '0000-0002-1234-5678',
            'reg_affiliation' => 'Institut Catala',
            'reg_country' => 'Spain',
            'reg_abstract' => 'This study examines early tool manufacture.',
            'reg_methodology' => 'empirical',
            'reg_license' => 'CC BY-NC-SA 4.0',
            'reg_declaration' => true,
            'reg_keywords' => 'paleoanthropology, tool use, Oldowan',
            'reg_coauthors' => "Lumley, Henry de\nCeliberti, Vincenzo",
            'reg_destination_url' => 'https://observatory.wiki/Tool_Use',
            'reg_published_destination' => 'Observatory',
            'reg_pdf_url' => 'https://ind.media/pdf/tool-use-v1.pdf',
            'reg_schema_type' => 'ScholarlyArticle',
            'reg_registry_id' => 'IMI-2026-001',
            'reg_pipeline_status' => 'preprint',
            'reg_version' => 1,
            'reg_version_type' => 'major',
            'reg_version_history' => 'Initial preprint release',
            'reg_prior_versions' => '',
            'reg_doi' => '10.67767/imi.2026.001',
            'reg_doi_url' => 'https://doi.org/10.67767/imi.2026.001',
            'reg_doi_status' => 'active',
            'reg_doi_minted_date' => '2026-07-15',
            'reg_crossref_deposit_id' => 'cr-dep-100',
            'reg_withdrawal_notice' => '',
        ];

        $entry = PostMetaHydrator::fromMeta('On the Origins of Tool Use', $meta, 'origins-of-tool-use');
        $serialized = \Phosphene\ImiWordpress\Adapters\WordPress\PostMetaSerializer::toMeta($entry);

        assertSame($meta['reg_author_name'], $serialized['reg_author_name'], 'serialized author name');
        assertSame($meta['reg_coauthors'], $serialized['reg_coauthors'], 'serialized coauthors');
        assertSame($meta['reg_doi'], $serialized['reg_doi'], 'serialized doi');
        assertSame($meta['reg_pipeline_status'], $serialized['reg_pipeline_status'], 'serialized pipeline status');
    }
}
