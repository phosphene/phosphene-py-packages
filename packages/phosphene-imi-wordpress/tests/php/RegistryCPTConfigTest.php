<?php

declare(strict_types=1);

require_once __DIR__ . '/../../src/php/RegistryCPTConfig.php';

// Polyfill TestCase assertions if PHPUnit isn't loaded
if (!class_exists('PHPUnit\Framework\TestCase')) {
    abstract class BaseTestCase {
        public function assertSame(mixed $expected, mixed $actual, string $message = ''): void {
            if ($expected !== $actual) {
                $e = var_export($expected, true);
                $a = var_export($actual, true);
                throw new RuntimeException("Assertion failed: $message (Expected $e, got $a)");
            }
        }
        public function assertTrue(bool $condition, string $message = ''): void {
            if (!$condition) {
                throw new RuntimeException("Assertion failed: $message");
            }
        }
        public function assertContains(mixed $needle, array $haystack, string $message = ''): void {
            if (!in_array($needle, $haystack, true)) {
                throw new RuntimeException("Assertion failed: $message (Array does not contain needle)");
            }
        }
        public function assertArrayHasKey(string|int $key, array $array, string $message = ''): void {
            if (!array_key_exists($key, $array)) {
                throw new RuntimeException("Assertion failed: $message (Missing key: $key)");
            }
        }
    }
} else {
    abstract class BaseTestCase extends PHPUnit\Framework\TestCase {}
}

class RegistryCPTConfigTest extends BaseTestCase
{
    public function test_version_is_1_0_0(): void
    {
        $this->assertSame('1.0.0', RegistryCPTConfig::VERSION);
    }

    public function test_cpt_slug_is_imi_registry(): void
    {
        $this->assertSame('imi_registry', RegistryCPTConfig::SLUG);
    }

    public function test_cpt_supports_title_and_custom_fields(): void
    {
        $args = RegistryCPTConfig::post_type_args();
        $this->assertContains('title', $args['supports']);
        $this->assertContains('custom-fields', $args['supports']);
    }

    public function test_cpt_show_in_rest_is_true(): void
    {
        $args = RegistryCPTConfig::post_type_args();
        $this->assertTrue($args['show_in_rest']);
    }

    public function test_meta_fields_include_legacy_keys(): void
    {
        $fields = RegistryCPTConfig::meta_fields();
        $this->assertArrayHasKey('author_name', $fields);
        $this->assertArrayHasKey('category', $fields);
        $this->assertArrayHasKey('source_url', $fields);

        foreach (['author_name', 'category', 'source_url'] as $key) {
            $this->assertSame('string', $fields[$key]['type']);
            $this->assertTrue($fields[$key]['show_in_rest']);
            $this->assertTrue($fields[$key]['single']);
        }
    }

    public function test_meta_fields_include_canonical_preprint_fields(): void
    {
        $fields = RegistryCPTConfig::meta_fields();

        $canonicalKeys = [
            'reg_author_name',
            'reg_orcid',
            'reg_affiliation',
            'reg_country',
            'reg_abstract',
            'reg_methodology',
            'reg_license',
            'reg_declaration',
            'reg_keywords',
            'reg_coauthors',
            'reg_destination_url',
            'reg_published_destination',
            'reg_pdf_url',
            'reg_pdf_id',
            'reg_download_count',
            'reg_schema_type',
            'reg_registry_id',
            'reg_pipeline_status',
            'reg_version',
            'reg_version_type',
            'reg_version_history',
            'reg_prior_versions',
            'reg_doi',
            'reg_doi_url',
            'reg_doi_status',
            'reg_doi_minted_date',
            'reg_crossref_deposit_id',
            'reg_withdrawal_notice',
        ];

        foreach ($canonicalKeys as $key) {
            $this->assertArrayHasKey($key, $fields, "Field $key must be declared");
            $this->assertTrue($fields[$key]['show_in_rest'], "Field $key must show in REST");
            $this->assertTrue($fields[$key]['single'], "Field $key must be single");
        }

        // Test specific types
        $this->assertSame('integer', $fields['reg_version']['type']);
        $this->assertSame('boolean', $fields['reg_declaration']['type']);
        $this->assertSame('integer', $fields['reg_download_count']['type']);
        $this->assertSame('string', $fields['reg_doi']['type']);
    }
}
