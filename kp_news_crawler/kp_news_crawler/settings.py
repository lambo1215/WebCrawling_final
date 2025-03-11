# Scrapy settings for kp_news_crawler project

BOT_NAME = 'kp_news_crawler'

SPIDER_MODULES = ['kp_news_crawler.spiders']
NEWSPIDER_MODULE = 'kp_news_crawler.spiders'

# Crawl responsibly by identifying yourself (and your website) on the user-agent
USER_AGENT = 'KP News Crawler (+your-contact-email@example.com)'

# Obey robots.txt rules
ROBOTSTXT_OBEY = True

# -----------------------------------------------------------------------------
# Playwright Configuration
# -----------------------------------------------------------------------------

# Enable Playwright middleware
DOWNLOAD_HANDLERS = {
    "http": "scrapy_playwright.handler.ScrapyPlaywrightDownloadHandler",
    "https": "scrapy_playwright.handler.ScrapyPlaywrightDownloadHandler",
}

# Configure Playwright browser options
PLAYWRIGHT_LAUNCH_OPTIONS = {
    "headless": True,
    "timeout": 30000,  # Browser launch timeout
}

# Playwright context arguments for realistic browsing
PLAYWRIGHT_CONTEXT_ARGS = {
    "viewport": {"width": 1280, "height": 720},
    "ignore_https_errors": True,
}

# Playwright settings for default timeouts
PLAYWRIGHT_DEFAULT_NAVIGATION_TIMEOUT = 30000  # 30 seconds
PLAYWRIGHT_DEFAULT_WAIT_TIMEOUT = 10000         # 10 seconds

# -----------------------------------------------------------------------------
# MongoDB Configuration
# -----------------------------------------------------------------------------

# MongoDB connection settings
MONGODB_URI = 'mongodb://localhost:27017'
MONGODB_DATABASE = 'kp_news'
MONGODB_COLLECTION = 'articles'

# -----------------------------------------------------------------------------
# Pipeline Configuration
# -----------------------------------------------------------------------------

# Configure item pipelines
ITEM_PIPELINES = {
    'kp_news_crawler.pipelines.MongoDBPipeline': 300,
}

# -----------------------------------------------------------------------------
# Rate Limiting and Crawl Behavior
# -----------------------------------------------------------------------------

# Respectful crawl settings
DOWNLOAD_DELAY = 1           # Reduced to 1 second
RANDOMIZE_DOWNLOAD_DELAY = True
CONCURRENT_REQUESTS = 8      # Lowered to 8
CONCURRENT_REQUESTS_PER_DOMAIN = 8
AUTOTHROTTLE_ENABLED = True   # Enabled AutoThrottle
AUTOTHROTTLE_START_DELAY = 5
AUTOTHROTTLE_MAX_DELAY = 60
AUTOTHROTTLE_TARGET_CONCURRENCY = 1.0
AUTOTHROTTLE_DEBUG = False

# -----------------------------------------------------------------------------
# Retry Middleware Settings
# -----------------------------------------------------------------------------

# Retry middleware settings
RETRY_ENABLED = True
RETRY_TIMES = 3
RETRY_HTTP_CODES = [500, 502, 503, 504, 400, 408, 410, 429] # Added 400 and 410
DOWNLOAD_TIMEOUT = 60  # Reduced to 60 seconds

# -----------------------------------------------------------------------------
# Core Settings
# -----------------------------------------------------------------------------

# Obey robots.txt rules
ROBOTSTXT_OBEY = True

# Disable cookies to reduce memory usage
COOKIES_ENABLED = False

# Set the Twisted reactor
TWISTED_REACTOR = 'twisted.internet.asyncioreactor.AsyncioSelectorReactor'

# Set settings whose default value is deprecated to a future-proof value
REQUEST_FINGERPRINTER_IMPLEMENTATION = '2.7'
FEED_EXPORT_ENCODING = 'utf-8'

# Enable memory usage extension
MEMUSAGE_ENABLED = True
MEMUSAGE_LIMIT_MB = 2048    # Adjust as needed
MEMUSAGE_WARNING_MB = 1024

# Logging settings
LOG_LEVEL = 'INFO'
LOG_FILE = 'kp_news_crawler.log'

# Project-specific settings
ARTICLE_LIMIT = 1500  # Enforce article limit



