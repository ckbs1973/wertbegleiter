<?php
// Copy this file to config.php on the ALL-INKL/KAS webspace.
// Never commit the real config.php with the live token.

return array(
    // Use the same long token as TRADINGVIEW_WEBHOOK_TOKEN in your local .env.
    'token' => 'CHANGE_ME_TO_A_LONG_RANDOM_TOKEN_32_CHARS_MIN',

    // Keep storage below this bridge directory. The included .htaccess blocks
    // direct browser access to storage files when Apache overrides are active.
    'storage_dir' => __DIR__ . '/storage',

    // TradingView alerts should be small JSON objects. This limit protects the
    // endpoint from accidental large uploads.
    'max_body_bytes' => 262144,
);
