<?php

declare(strict_types=1);

namespace Phosphene\ImiWordpress\Serialization;

require_once __DIR__ . '/../Domain/Author.php';
require_once __DIR__ . '/../Domain/ContributorSequence.php';
require_once __DIR__ . '/../Utils/DelimitedListUtil.php';

use Phosphene\ImiWordpress\Domain\Author;
use Phosphene\ImiWordpress\Domain\ContributorSequence;
use Phosphene\ImiWordpress\Utils\DelimitedListUtil;

/**
 * Discrete serialization unit for primary author and coauthors in WordPress postmeta.
 */
final class AuthorMetaUnit
{
    /**
     * @param Author $primary
     * @param list<Author> $coauthors
     * @return array<string, string>
     */
    public static function serialize(Author $primary, array $coauthors = []): array
    {
        $coauthorNames = array_map(fn(Author $a) => $a->name, $coauthors);
        return [
            'reg_author_name' => $primary->name,
            'reg_orcid' => $primary->orcid,
            'reg_affiliation' => $primary->affiliation,
            'reg_country' => $primary->country,
            'reg_coauthors' => DelimitedListUtil::joinLines($coauthorNames),
        ];
    }

    /**
     * @param array<string, mixed> $meta
     * @return array{primaryAuthor: Author, coauthors: list<Author>}
     */
    public static function hydrate(array $meta): array
    {
        $primary = new Author(
            name: (string)($meta['reg_author_name'] ?? ''),
            orcid: (string)($meta['reg_orcid'] ?? ''),
            affiliation: (string)($meta['reg_affiliation'] ?? ''),
            country: (string)($meta['reg_country'] ?? ''),
            sequence: ContributorSequence::FIRST,
        );

        $rawCoauthors = (string)($meta['reg_coauthors'] ?? '');
        $lines = DelimitedListUtil::splitLines($rawCoauthors);
        $coauthors = [];
        foreach ($lines as $line) {
            $coauthors[] = new Author(
                name: $line,
                sequence: ContributorSequence::ADDITIONAL,
            );
        }

        return [
            'primaryAuthor' => $primary,
            'coauthors' => $coauthors,
        ];
    }
}
