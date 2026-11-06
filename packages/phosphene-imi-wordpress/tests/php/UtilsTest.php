<?php

declare(strict_types=1);

require_once __DIR__ . '/../../src/php/Utils/StringUtils.php';
require_once __DIR__ . '/../../src/php/Utils/HtmlUtils.php';

use Phosphene\ImiWordpress\Utils\HtmlUtils;
use Phosphene\ImiWordpress\Utils\StringUtils;

class UtilsTest {
    public function testStringUtilsSlugify(): void {
        if (StringUtils::slugify('Why Care Work Matters') !== 'why-care-work-matters') {
            throw new Exception("slugify failed for 'Why Care Work Matters'");
        }
        if (StringUtils::slugify('Degrowth in Supply Chains') !== 'degrowth-in-supply-chains') {
            throw new Exception("slugify failed for 'Degrowth in Supply Chains'");
        }
        if (StringUtils::slugify('Land Reform — A New Paradigm! (Vol. 2)') !== 'land-reform-a-new-paradigm-vol-2') {
            throw new Exception("slugify failed for complex punctuation");
        }
        if (StringUtils::slugify('A Very Long Headline', 6) !== 'a-very') {
            throw new Exception("slugify max_length truncation failed");
        }
        if (StringUtils::slugify('') !== '') {
            throw new Exception("slugify empty string failed");
        }
    }

    public function testStringUtilsHumanizeSlug(): void {
        if (StringUtils::humanizeSlug('Cave_Art_in_France') !== 'Cave Art in France') {
            throw new Exception("humanizeSlug with underscores failed");
        }
        if (StringUtils::humanizeSlug('climate-crisis-2026') !== 'climate crisis 2026') {
            throw new Exception("humanizeSlug with hyphens failed");
        }
        if (StringUtils::humanizeSlug('') !== '') {
            throw new Exception("humanizeSlug with empty string failed");
        }
    }

    public function testStringUtilsJoinDelimited(): void {
        if (StringUtils::joinDelimited(['Economics', 'Agriculture']) !== 'Economics, Agriculture') {
            throw new Exception("joinDelimited standard failed");
        }
        if (StringUtils::joinDelimited(['Economics', '', '   ', 'Degrowth']) !== 'Economics, Degrowth') {
            throw new Exception("joinDelimited null omission failed");
        }
        if (StringUtils::joinDelimited([]) !== '') {
            throw new Exception("joinDelimited empty array failed");
        }
        if (StringUtils::joinDelimited(['A', 'B'], "\n") !== "A\nB") {
            throw new Exception("joinDelimited custom delimiter failed");
        }
    }

    public function testHtmlUtilsRenderMetaTag(): void {
        $tag = HtmlUtils::renderMetaTag('citation_title', 'Study & "Research"');
        $expected = '<meta name="citation_title" content="Study &amp; &quot;Research&quot;" />';
        if ($tag !== $expected) {
            throw new Exception("renderMetaTag failed: expected '$expected', got '$tag'");
        }
    }

    public function testHtmlUtilsRenderMetaTags(): void {
        $tags = [
            ['name' => 'citation_title', 'content' => 'Title'],
            ['name' => 'citation_author', 'content' => 'Author'],
        ];
        $expected = "<meta name=\"citation_title\" content=\"Title\" />\n<meta name=\"citation_author\" content=\"Author\" />";
        if (HtmlUtils::renderMetaTags($tags) !== $expected) {
            throw new Exception("renderMetaTags failed");
        }
    }
}
