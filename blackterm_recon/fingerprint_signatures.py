from __future__ import annotations

# Passive signatures used by the technology fingerprinting engine. Patterns are
# intentionally conservative: a single weak body token should not be treated as
# definitive without corroborating evidence.

HEADER_SIGNATURES = {
    "server": {
        "nginx": ("Nginx", "web_server", 92),
        "apache": ("Apache HTTP Server", "web_server", 92),
        "microsoft-iis": ("Microsoft IIS", "web_server", 96),
        "caddy": ("Caddy", "web_server", 94),
        "cloudflare": ("Cloudflare", "cdn", 94),
        "gunicorn": ("Gunicorn", "application_server", 92),
        "uvicorn": ("Uvicorn", "application_server", 92),
        "openresty": ("OpenResty", "web_server", 94),
    },
    "x-powered-by": {
        "express": ("Express", "framework", 96),
        "php": ("PHP", "runtime", 92),
        "asp.net": ("ASP.NET", "framework", 94),
        "next.js": ("Next.js", "framework", 96),
    },
    "x-generator": {
        "wordpress": ("WordPress", "cms", 98),
        "drupal": ("Drupal", "cms", 98),
        "joomla": ("Joomla", "cms", 98),
    },
    "via": {
        "varnish": ("Varnish", "cache", 90),
        "cloudfront": ("Amazon CloudFront", "cdn", 92),
    },
}

COOKIE_SIGNATURES = {
    "phpsessid": ("PHP", "runtime", 82),
    "asp.net_sessionid": ("ASP.NET", "framework", 90),
    "jsessionid": ("Java", "runtime", 82),
    "laravel_session": ("Laravel", "framework", 95),
    "django": ("Django", "framework", 78),
    "csrftoken": ("Django", "framework", 72),
    "connect.sid": ("Express", "framework", 84),
    "wordpress_": ("WordPress", "cms", 94),
    "wp-settings": ("WordPress", "cms", 96),
}

BODY_SIGNATURES = {
    "wp-content/": ("WordPress", "cms", 92),
    "wp-includes/": ("WordPress", "cms", 92),
    'content="wordpress': ("WordPress", "cms", 96),
    "drupal-settings-json": ("Drupal", "cms", 94),
    "/sites/default/files/": ("Drupal", "cms", 88),
    'content="joomla': ("Joomla", "cms", 96),
    "/media/system/js/": ("Joomla", "cms", 82),
    "__next_data__": ("Next.js", "framework", 98),
    "/_next/static/": ("Next.js", "framework", 96),
    "data-reactroot": ("React", "frontend", 90),
    "react-dom": ("React", "frontend", 76),
    "ng-version=": ("Angular", "frontend", 98),
    "_ngcontent-": ("Angular", "frontend", 88),
    "data-v-": ("Vue.js", "frontend", 72),
    "__vue__": ("Vue.js", "frontend", 90),
    "nuxt": ("Nuxt", "framework", 72),
    "__nuxt__": ("Nuxt", "framework", 96),
    "shopify.theme": ("Shopify", "ecommerce", 96),
    "cdn.shopify.com": ("Shopify", "ecommerce", 90),
    "wixstatic.com": ("Wix", "site_builder", 92),
    "squarespace.com": ("Squarespace", "site_builder", 90),
}

BANNER_SIGNATURES = {
    "openssh": ("OpenSSH", "remote_access", 96),
    "dropbear": ("Dropbear SSH", "remote_access", 96),
    "nginx": ("Nginx", "web_server", 88),
    "apache": ("Apache HTTP Server", "web_server", 88),
    "microsoft-iis": ("Microsoft IIS", "web_server", 94),
    "redis": ("Redis", "database", 90),
    "mysql": ("MySQL", "database", 88),
    "postgresql": ("PostgreSQL", "database", 88),
    "mongodb": ("MongoDB", "database", 88),
}

SERVICE_SIGNATURES = {
    "ssh": ("SSH", "protocol", 70),
    "https": ("TLS/HTTPS", "protocol", 72),
    "http": ("HTTP", "protocol", 68),
    "microsoft-ds": ("SMB", "protocol", 78),
    "netbios-ssn": ("NetBIOS", "protocol", 76),
    "mysql": ("MySQL", "database", 78),
    "postgresql": ("PostgreSQL", "database", 78),
    "redis": ("Redis", "database", 78),
    "mongodb": ("MongoDB", "database", 78),
}
