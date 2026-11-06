<?php

declare(strict_types=1);

use PHPUnit\Framework\TestCase;

require_once __DIR__ . '/../../src/php/CitationMetaTags.php';

/**
 * Pure PHP unit tests for CitationMetaTags — Google Scholar meta tags.
 *
 * TDD: written BEFORE the implementation. All 6 must fail (class not found)
 * on first run, then pass after implementation.
 */
class CitationMetaTagsTest extends TestCase
{
    public function test_renders_citation_title(): void
    {
        $tags = new CitationMetaTags(
            title: 'The Evolution of Cooperation',
            author: 'Robert Axelrod'
        );
        $html = $tags->render();
        $this->assertStringContainsString(
            '<meta name="citation_title" content="The Evolution of Cooperation"',
            $html
        );
    }

    public function test_renders_citation_author(): void
    {
        $tags = new CitationMetaTags(
            title: 'Selfish Gene',
            author: 'Richard Dawkins'
        );
        $html = $tags->render();
        $this->assertStringContainsString(
            '<meta name="citation_author" content="Richard Dawkins"',
            $html
        );
    }

    public function test_renders_citation_publisher(): void
    {
        $tags = new CitationMetaTags(
            title: 'Test Article',
            author: 'Test Author'
        );
        $html = $tags->render();
        $this->assertStringContainsString(
            '<meta name="citation_publisher" content="Independent Media Institute"',
            $html
        );
    }

    public function test_optional_doi_absent_when_not_set(): void
    {
        $tags = new CitationMetaTags(
            title: 'Test Article',
            author: 'Test Author'
        );
        $html = $tags->render();
        $this->assertStringNotContainsString('citation_doi', $html);
    }

    public function test_optional_doi_present_when_set(): void
    {
        $tags = new CitationMetaTags(
            title: 'Test Article',
            author: 'Test Author',
            doi: '10.1234/test.2026'
        );
        $html = $tags->render();
        $this->assertStringContainsString(
            '<meta name="citation_doi" content="10.1234/test.2026"',
            $html
        );
    }

    public function test_html_entities_escaped(): void
    {
        $tags = new CitationMetaTags(
            title: 'Art & Science: A "Bold" <Approach>',
            author: "O'Brien & Partners"
        );
        $html = $tags->render();
        $this->assertStringContainsString('&amp;', $html);
        $this->assertStringContainsString('&lt;', $html);
        $this->assertStringContainsString('&gt;', $html);
    }
}
