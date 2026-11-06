<?php

declare(strict_types=1);

require_once __DIR__ . '/../../src/php/Utils/DoiPattern.php';

use Phosphene\ImiWordpress\Utils\DoiPattern;

class DoiPatternTest
{
    public function testIsValidStandardDois(): void
    {
        assertTrue(DoiPattern::isValid('10.67767/imi.2026.001'), 'IMI standard DOI');
        assertTrue(DoiPattern::isValid('10.1000/182'), 'Handle system DOI');
        assertTrue(DoiPattern::isValid('10.1038/nphys1170'), 'Nature DOI');
        assertTrue(DoiPattern::isValid('10.1002/(SICI)1097-0142(19980101)82:1<4::AID-CNCR1>3.0.CO;2-H'), 'Complex syntax DOI');
    }

    public function testIsValidRejectsMalformed(): void
    {
        assertTrue(!DoiPattern::isValid('not-a-doi'), 'Random string rejected');
        assertTrue(!DoiPattern::isValid('10.123/'), 'Missing suffix rejected');
        assertTrue(!DoiPattern::isValid('/suffix-only'), 'Missing prefix rejected');
        assertTrue(!DoiPattern::isValid('9.67767/invalid'), 'Non-10 prefix rejected');
        assertTrue(!DoiPattern::isValid('10.12/s'), 'Sub-4-digit prefix rejected');
        assertTrue(!DoiPattern::isValid(''), 'Empty string rejected');
    }

    public function testStripProtocolPrefix(): void
    {
        assertSame('10.67767/imi.2026.001', DoiPattern::stripProtocolPrefix('https://doi.org/10.67767/imi.2026.001'), 'https doi.org');
        assertSame('10.67767/imi.2026.001', DoiPattern::stripProtocolPrefix('http://doi.org/10.67767/imi.2026.001'), 'http doi.org');
        assertSame('10.67767/imi.2026.001', DoiPattern::stripProtocolPrefix('https://dx.doi.org/10.67767/imi.2026.001'), 'dx.doi.org');
        assertSame('10.67767/imi.2026.001', DoiPattern::stripProtocolPrefix('doi:10.67767/imi.2026.001'), 'doi: scheme');
        assertSame('10.67767/imi.2026.001', DoiPattern::stripProtocolPrefix('  https://doi.org/10.67767/imi.2026.001  '), 'trimmed whitespace');
    }

    public function testSplit(): void
    {
        $split = DoiPattern::split('https://doi.org/10.67767/imi.2026.042');
        assertTrue($split !== null, 'Valid split returns array');
        assertSame('10.67767', $split['prefix'], 'split prefix');
        assertSame('imi.2026.042', $split['suffix'], 'split suffix');

        $invalidSplit = DoiPattern::split('invalid-doi');
        assertSame(null, $invalidSplit, 'Invalid split returns null');
    }
}
