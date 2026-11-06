<?php

declare(strict_types=1);

/**
 * Lightweight pure PHP test runner for local unit execution without composer.
 */

require_once __DIR__ . '/PreprintDomainTest.php';
require_once __DIR__ . '/ScholarlyAdaptersTest.php';
require_once __DIR__ . '/RegistryCPTConfigTest.php';
require_once __DIR__ . '/UtilsTest.php';
require_once __DIR__ . '/DoiPatternTest.php';
require_once __DIR__ . '/OrcidPatternTest.php';
require_once __DIR__ . '/DelimitedListUtilTest.php';
require_once __DIR__ . '/SerializationUnitsTest.php';

$testClasses = [
    PreprintDomainTest::class,
    ScholarlyAdaptersTest::class,
    RegistryCPTConfigTest::class,
    UtilsTest::class,
    DoiPatternTest::class,
    OrcidPatternTest::class,
    DelimitedListUtilTest::class,
    SerializationUnitsTest::class,
];

$passed = 0;
$failed = 0;

echo "=== Running Pure PHP Unit Tests ===\n";

foreach ($testClasses as $className) {
    echo "Running $className...\n";
    $instance = new $className();
    $methods = get_class_methods($instance);

    foreach ($methods as $method) {
        if (str_starts_with($method, 'test')) {
            try {
                $instance->$method();
                echo "  ✓ $method\n";
                $passed++;
            } catch (Throwable $e) {
                echo "  ✗ $method: " . $e->getMessage() . "\n";
                echo "    " . $e->getFile() . ':' . $e->getLine() . "\n";
                $failed++;
            }
        }
    }
}

echo "\nSummary: $passed passed, $failed failed.\n";

if ($failed > 0) {
    exit(1);
}
