<?php
/**
 * Bootstrap for pure PHP unit tests — stubs WP functions not available outside WordPress.
 * Loads only the source files under test.
 */
if (!function_exists('esc_attr')) {
    function esc_attr($str) { return htmlspecialchars($str, ENT_QUOTES, 'UTF-8'); }
}
require_once __DIR__ . '/../../src/php/RegistryCPTConfig.php';
