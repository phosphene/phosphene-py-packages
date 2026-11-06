<?php

declare(strict_types=1);

require_once __DIR__ . '/../../src/php/Utils/OrcidPattern.php';

use Phosphene\ImiWordpress\Utils\OrcidPattern;

class OrcidPatternTest
{
    public function testIsValidStandardOrcids(): void
    {
        assertTrue(OrcidPattern::isValid('0000-0002-1825-0097'), 'Standard ORCID');
        assertTrue(OrcidPattern::isValid('0000-0001-5109-3700'), 'Standard ORCID');
        assertTrue(OrcidPattern::isValid('0000-0002-1694-233X'), 'ORCID with X check digit');
    }

    public function testIsValidRejectsMalformed(): void
    {
        assertTrue(!OrcidPattern::isValid('not-an-orcid'), 'Text rejected');
        assertTrue(!OrcidPattern::isValid('0000-0002-1825-009'), '15 digits rejected');
        assertTrue(!OrcidPattern::isValid('0000000218250097'), 'Un-hyphenated rejected');
        assertTrue(!OrcidPattern::isValid('0000-0002-1825-009Y'), 'Invalid check letter rejected');
        assertTrue(!OrcidPattern::isValid(''), 'Empty rejected');
    }

    public function testCanonicalize(): void
    {
        assertSame('0000-0002-1825-0097', OrcidPattern::canonicalize('https://orcid.org/0000-0002-1825-0097'), 'https prefix stripped');
        assertSame('0000-0002-1825-0097', OrcidPattern::canonicalize('http://orcid.org/0000-0002-1825-0097'), 'http prefix stripped');
        assertSame('0000-0002-1825-0097', OrcidPattern::canonicalize('  0000-0002-1825-0097  '), 'trimmed digits');
    }

    public function testToUri(): void
    {
        assertSame('https://orcid.org/0000-0002-1825-0097', OrcidPattern::toUri('0000-0002-1825-0097'), 'full URI generated');
        assertSame('https://orcid.org/0000-0002-1825-0097', OrcidPattern::toUri('https://orcid.org/0000-0002-1825-0097'), 'idempotent with existing URI');
        assertSame('', OrcidPattern::toUri(''), 'empty returns empty');
    }
}
