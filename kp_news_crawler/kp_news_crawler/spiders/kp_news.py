import scrapy
from scrapy_playwright.page import PageMethod
from ..items import NewsArticleItem
from datetime import datetime, timedelta
import logging
from urllib.parse import urlparse
from playwright.async_api import TimeoutError as PlaywrightTimeoutError

class KpNewsSpider(scrapy.Spider):
    name = 'kp_news'
    allowed_domains = ['kp.ru']
    start_urls = ['https://www.kp.ru/online/']
    article_count = 0
    max_articles = 1500
    processed_urls = set()

    custom_settings = {
        'DOWNLOAD_DELAY': 2,
        'CONCURRENT_REQUESTS': 4,
        'PLAYWRIGHT_DEFAULT_NAVIGATION_TIMEOUT': 60000,
    }
    
    def start_requests(self):
        for url in self.start_urls:
            yield scrapy.Request(
                url,
                meta=dict(
                    playwright=True,
                    playwright_include_page=True,
                    playwright_page_methods=[
                        PageMethod("wait_for_load_state", "domcontentloaded", timeout=60000),
                        PageMethod("wait_for_selector", "body", timeout=10000),
                        PageMethod("evaluate", "() => { window.scrollBy(0, 300); }"),
                        PageMethod("wait_for_selector", ".main, .content, article, a[href*='/online/'], a[href*='/news/']", 
                                  timeout=60000, state="attached")
                    ],
                ),
                callback=self.parse,
                errback=self.errback_handler
            )

    async def parse(self, response):
        page = response.meta["playwright_page"]
        
        try:
            await page.evaluate("() => { window.scrollBy(0, 600); }")
            
            news_items = response.css('article, .news-item, a[href*="/news/"], a[href*="/online/"], .article-preview')
            
            self.logger.info(f"Found {len(news_items)} potential news items")
            
            for item in news_items:
                if self.article_count >= self.max_articles:
                    self.logger.info(f"Reached article limit of {self.max_articles}")
                    return
                
                article_url = item.css('::attr(href)').get()
                
                if not article_url:
                    continue
                    
                if not article_url.startswith('http'):
                    article_url = f"https://www.kp.ru{article_url}"
                
                if article_url in self.processed_urls:
                    continue
                    
                self.processed_urls.add(article_url)
                
                yield scrapy.Request(
                    article_url,
                    meta=dict(
                        playwright=True,
                        playwright_include_page=True,
                        playwright_page_methods=[
                            PageMethod("wait_for_load_state", "domcontentloaded", timeout=60000),
                            PageMethod("wait_for_selector", "body", timeout=10000),
                            PageMethod("wait_for_selector", 
                                     "article, .article, .content, .text, h1, div[class*='article'], .news-item, main", 
                                     timeout=60000, state="attached")
                        ],
                    ),
                    callback=self.parse_article,
                    errback=self.errback_handler
                )
            
            next_page = response.css('a.pagination__item--next::attr(href), a.next::attr(href), .pagination a::attr(href), a[rel="next"]::attr(href)').get()
            if next_page and self.article_count < self.max_articles:
                if not next_page.startswith('http'):
                    next_page = f"https://www.kp.ru{next_page}"
                
                yield scrapy.Request(
                    next_page,
                    meta=dict(
                        playwright=True,
                        playwright_include_page=True,
                        playwright_page_methods=[
                            PageMethod("wait_for_load_state", "domcontentloaded", timeout=60000),
                            PageMethod("wait_for_selector", "body", timeout=10000),
                            PageMethod("wait_for_selector", ".main, .content, article", 
                                      timeout=60000, state="attached")
                        ],
                    ),
                    callback=self.parse,
                    errback=self.errback_handler
                )
                
        except Exception as e:
            self.logger.error(f"Error in parse method: {e}")
        finally:
            await page.close()
    
    async def parse_article(self, response):
        page = response.meta["playwright_page"]
        
        try:
            await page.evaluate("() => { window.scrollBy(0, 600); }")
            
            item = NewsArticleItem()
            
            item['title'] = response.css('h1::text, meta[property="og:title"]::attr(content)').get()
            item['description'] = response.css('.lead::text, meta[name="description"]::attr(content)').get()
            
            article_paragraphs = response.css('.article__text p::text, article p::text, .content p::text').getall()
            if not article_paragraphs:
                article_paragraphs = response.css('p::text').getall()
            
            item['article_text'] = ' '.join([p.strip() for p in article_paragraphs if p.strip()])
            
            item['publication_datetime'] = response.css('time::text, meta[property="article:published_time"]::attr(content)').get()
            item['header_photo_url'] = response.css('.article__image img::attr(src), meta[property="og:image"]::attr(content)').get()
            
            keywords_meta = response.css('meta[name="keywords"]::attr(content)').get()
            item['keywords'] = [k.strip() for k in keywords_meta.split(',')] if keywords_meta else []
            
            item['authors'] = response.css('.author::text, meta[name="author"]::attr(content)').get()
            item['source_url'] = response.url
            
            if item['title'] and item['article_text'] and len(item['article_text']) > 100:
                self.article_count += 1
                self.logger.info(f"Extracted article {self.article_count}: {item['title']}")
                yield item
            else:
                self.logger.warning(f"Skipping article with insufficient content: {response.url}")
                
        except Exception as e:
            self.logger.error(f"Error parsing article {response.url}: {e}")
        finally:
            await page.close()
    
    def errback_handler(self, failure):
        if failure.check(PlaywrightTimeoutError):
            self.logger.warning(f"PlaywrightTimeoutError on {failure.request.url}")
        else:
            self.logger.error(f"Request failed: {failure.value}")
        
        parsed_url = urlparse(failure.request.url)
        base_url = f"{parsed_url.scheme}://{parsed_url.netloc}{parsed_url.path}"
        self.processed_urls.discard(base_url)

