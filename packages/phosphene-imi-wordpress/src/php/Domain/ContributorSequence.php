<?php

declare(strict_types=1);

namespace Phosphene\ImiWordpress\Domain;

/**
 * Contributor ordering sequence for scholarly schemas (e.g. Crossref 5.3.1 contributor sequence).
 */
enum ContributorSequence: string
{
    case FIRST = 'first';
    case ADDITIONAL = 'additional';
}
