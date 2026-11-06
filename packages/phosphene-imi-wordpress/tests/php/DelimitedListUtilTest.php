<?php

declare(strict_types=1);

require_once __DIR__ . '/../../src/php/Utils/DelimitedListUtil.php';

use Phosphene\ImiWordpress\Utils\DelimitedListUtil;

class DelimitedListUtilTest
{
    public function testSplitLines(): void
    {
        $raw = "  Author One  \r\n\r\n  Author Two \nAuthor Three\n  ";
        $result = DelimitedListUtil::splitLines($raw);
        assertSame(['Author One', 'Author Two', 'Author Three'], $result, 'splitLines scrubs \\r, trims and drops blanks');

        assertSame([], DelimitedListUtil::splitLines(''), 'empty returns empty array');
        assertSame([], DelimitedListUtil::splitLines("  \n  \r\n  "), 'whitespace returns empty array');
    }

    public function testJoinLines(): void
    {
        $items = ['Line 1', '  Line 2  ', '', 'Line 3'];
        $result = DelimitedListUtil::joinLines($items);
        assertSame("Line 1\nLine 2\nLine 3", $result, 'joinLines trims and filters empty');
    }

    public function testSplitCommas(): void
    {
        $raw = '  geology,  climate change , , paleontology ';
        $result = DelimitedListUtil::splitCommas($raw);
        assertSame(['geology', 'climate change', 'paleontology'], $result, 'splitCommas trims and drops empty');

        assertSame([], DelimitedListUtil::splitCommas(''), 'empty returns empty array');
    }

    public function testJoinCommas(): void
    {
        $items = ['term 1', '  term 2 ', '', 'term 3'];
        $result = DelimitedListUtil::joinCommas($items);
        assertSame('term 1, term 2, term 3', $result, 'joinCommas trims and formats cleanly');
    }
}
