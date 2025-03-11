import scrapy
from scrapy_playwright.page import PageMethod
from ..items import NewsArticleItem
from datetime import datetime, timedelta
import logging
import random

class KpNewsSpider(scrapy.Spider):
    name = 'kp_news'
    allowed_domains = ['kp.ru']
    start_urls = ['https://www.kp.ru/online/']
    article_count = 0
    max_articles = 10000
    
    def start_requests(self):
        for url in self.start_urls:
            yield scrapy.Request(
                url,
                meta=dict(
                    playwright=True,
                    playwright_include_page=True,
                    # Use context args for more realistic browser simulation
                    playwright_context_args={
                        "user_agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/121.0.0.0 Safari/537.36",
                        "viewport": {"width": 1280, "height": 720},
                        "ignore_https_errors": True,
                    },
                    # Use a more reliable page method sequence
                    playwright_page_methods=[
                        # Basic load with shorter timeout
                        PageMethod("wait_for_load_state", "domcontentloaded", timeout=30000),
                        # Small delay
                        PageMethod("wait_for_timeout", 2000),
                        # Just wait for body first
                        PageMethod("wait_for_selector", "body", timeout=5000),
                        # Simulate scrolling to trigger lazy-loading
                        PageMethod("evaluate", "() => { window.scrollBy(0, 300); }"),
                        # Another small delay
                        PageMethod("wait_for_timeout", 1000),
                        # Try a very general selector
                        PageMethod("wait_for_selector", ".main, .content, article, a[href*='/online/'], a[href*='/news/']", 
                                  timeout=20000, state="attached")
                    ],
                ),
                callback=self.parse,
                errback=self.errback_handler
            )

    async def parse(self, response):
        page = response.meta["playwright_page"]
        
        try:
            # Take screenshot for debugging
            await page.screenshot(path=f"page_loaded_{datetime.now().strftime('%Y%m%d_%H%M%S')}.png")
            
            # Use scrolling to simulate human behavior and trigger lazy-loading
            await self.simulate_scrolling(page)
            
            # Try multiple selector strategies with increasingly general patterns
            news_items = response.css('article.news-feed__item, div.news-feed__item, .news-list__item, .news-item')
            
            if not news_items or len(news_items) < 3:
                self.logger.warning(f"Found only {len(news_items)} items with primary selectors. Trying secondary selectors.")
                news_items = response.css('article, .news, a[href*="/news/"], a[href*="/online/"], .article-preview')
                
            if not news_items or len(news_items) < 3:
                self.logger.warning("Still not enough items. Trying general link extraction.")
                # Fallback to general links that might be news items based on URL pattern
                all_links = response.css('a[href]')
                news_items = [link for link in all_links if any(x in link.attrib.get('href', '') 
                                                                for x in ['/news/', '/online/', '/daily/', '/incident/'])]
                
            self.logger.info(f"Found {len(news_items)} potential news items using combined strategy")
            
            # Calculate the cutoff time (24 hours ago)
            cutoff_time = datetime.now() - timedelta(days=1)
            
            # Process each news item
            processed_urls = set()  # Track URLs to avoid duplicates
            
            for item in news_items:
                # Break if we've reached the article limit
                if self.article_count >= self.max_articles:
                    self.logger.info(f"Reached article limit of {self.max_articles}")
                    break
                
                # Extract article URL with various fallback methods
                article_url = None
                
                # Try direct href attribute if this is a link
                if 'href' in getattr(item, 'attrib', {}):
                    article_url = item.attrib['href']
                else:
                    # Try CSS selectors for nested links
                    article_url = item.css('a::attr(href), a.news-feed__item-link::attr(href)').get()
                
                if not article_url:
                    continue
                    
                # Complete the URL if it's relative
                if not article_url.startswith('http'):
                    article_url = f"https://www.kp.ru{article_url}"
                
                # Skip if we've already processed this URL
                if article_url in processed_urls:
                    continue
                    
                processed_urls.add(article_url)
                
                # Request the article page with more resilient approach
                yield scrapy.Request(
                    article_url,
                    meta=dict(
                        playwright=True,
                        playwright_include_page=True,
                        playwright_page_methods=[
                            # Basic load
                            PageMethod("wait_for_load_state", "domcontentloaded", timeout=30000),
                            # Small delay
                            PageMethod("wait_for_timeout", 1000),
                            # Just wait for body
                            PageMethod("wait_for_selector", "body", timeout=5000),
                            # Try a general content selector with 'attached' state (more permissive)
                            PageMethod("wait_for_selector", 
                                     "article, .article, .content, .text, h1", 
                                     timeout=20000, state="attached")
                        ],
                    ),
                    callback=self.parse_article,
                    errback=self.errback_handler
                )
            
            # Check for pagination to navigate to the next page
            next_page = response.css('a.pagination__item--next::attr(href), a.next::attr(href), .pagination a::attr(href), a[rel="next"]::attr(href)').get()
            if next_page and self.article_count < self.max_articles:
                if not next_page.startswith('http'):
                    next_page = f"https://www.kp.ru{next_page}"
                    
                # Add randomized delay for pagination    
                await page.wait_for_timeout(random.randint(3000, 5000))
                
                yield scrapy.Request(
                    next_page,
                    meta=dict(
                        playwright=True,
                        playwright_include_page=True,
                        playwright_page_methods=[
                            PageMethod("wait_for_load_state", "domcontentloaded", timeout=30000),
                            PageMethod("wait_for_timeout", 2000),
                            PageMethod("wait_for_selector", "body", timeout=5000),
                            PageMethod("evaluate", "() => { window.scrollBy(0, 300); }"),
                            PageMethod("wait_for_timeout", 1000),
                            PageMethod("wait_for_selector", ".main, .content, article", 
                                      timeout=20000, state="attached")
                        ],
                    ),
                    callback=self.parse,
                    errback=self.errback_handler
                )
                
        except Exception as e:
            self.logger.error(f"Error in parse method: {e}")
            await page.screenshot(path=f"error_{datetime.now().strftime('%Y%m%d_%H%M%S')}.png")
        finally:
            # Close the page when done
            await page.close()
    
    async def parse_article(self, response):
        page = response.meta["playwright_page"]
        
        try:
            # Take screenshot of article page for debugging
            await page.screenshot(path=f"article_{datetime.now().strftime('%Y%m%d_%H%M%S')}.png")
            
            # Wait to ensure content is loaded
            await self.simulate_scrolling(page)
            
            # Extract article data with multiple selector options for each field
            item = NewsArticleItem()
            
            # Title - try multiple strategies
            title = response.css('h1.article-title::text, h1::text, .article__title::text, .title::text').get()
            if not title:
                title = response.css('meta[property="og:title"]::attr(content)').get()
            item['title'] = title
            
            # Description with fallbacks
            description = response.css('div.article-subtext::text, .article__subtitle::text, .lead::text').get()
            if not description:
                description = response.css('meta[name="description"]::attr(content), meta[property="og:description"]::attr(content)').get()
            item['description'] = description
            
            # Article text - try multiple strategies
            article_paragraphs = response.css('div.article-text p::text, .article__text p::text, article p::text, .entry-content p::text, .content p::text').getall()
            if not article_paragraphs or len(''.join(article_paragraphs)) < 100:
                # Fallback to any paragraph tags
                article_paragraphs = response.css('p::text').getall()
            
            # If still no substantial content, try to get any text
            if not article_paragraphs or len(''.join(article_paragraphs)) < 100:
                article_paragraphs = response.css('.content ::text').getall()
                
            item['article_text'] = ' '.join([p.strip() for p in article_paragraphs if p.strip()])
            
            # Publication date with fallbacks
            pub_date = response.css('span.article-date::text, time::text, .time::text, .date::text').get()
            if not pub_date:
                pub_date = response.css('meta[property="article:published_time"]::attr(content)').get()
            item['publication_datetime'] = pub_date
            
            # Photo URL with fallbacks
            photo_url = response.css('div.article-img img::attr(src), .article__main-image img::attr(src), .article__image img::attr(src)').get()
            if not photo_url:
                photo_url = response.css('meta[property="og:image"]::attr(content)').get()
            item['header_photo_url'] = photo_url
            
            # Keywords with fallbacks
            keywords_meta = response.css('meta[name="keywords"]::attr(content)').get()
            if keywords_meta:
                item['keywords'] = [k.strip() for k in keywords_meta.split(',') if k.strip()]
            else:
                # Try extracting tags
                keywords = response.css('.tags a::text, .article-tags a::text').getall()
                item['keywords'] = keywords if keywords else []
            
            # Author with fallbacks
            authors = response.css('span.author::text, .article__author::text, .author-name::text').get()
            if not authors:
                authors = response.css('meta[name="author"]::attr(content)').get()
            item['authors'] = authors
            
            item['source_url'] = response.url
            
            # Only count articles that have meaningful content
            if item['title'] and item['article_text'] and len(item['article_text']) > 100:
                self.article_count += 1
                self.logger.info(f"Extracted article {self.article_count}: {item['title']}")
                yield item
            else:
                self.logger.warning(f"Skipping article with insufficient content: {response.url}")
                
        except Exception as e:
            self.logger.error(f"Error parsing article {response.url}: {e}")
            await page.screenshot(path=f"article_error_{datetime.now().strftime('%Y%m%d_%H%M%S')}.png")
        finally:
            await page.close()
    
    async def simulate_scrolling(self, page):
        """Simulate human-like scrolling behavior"""
        try:
            # Scroll down gradually
            await page.evaluate("""
                () => {
                    const totalHeight = document.body.scrollHeight;
                    const distance = 300;
                    let scrolled = 0;
                    
                    const timer = setInterval(() => {
                        window.scrollBy(0, distance);
                        scrolled += distance;
                        
                        if (scrolled >= totalHeight * 0.6) {
                            clearInterval(timer);
                        }
                    }, 200);
                }
            """)
            
            # Wait for any dynamically loaded content
            await page.wait_for_timeout(random.randint(1000, 2000))
            
        except Exception as e:
            self.logger.error(f"Error during scroll simulation: {e}")
    
    def errback_handler(self, failure):
        """Handle request failures"""
        self.logger.error(f"Request failed: {failure.value}")
        self.logger.error(f"Failed URL: {failure.request.url}")
        
        # Try to extract useful data even from failed requests
        if hasattr(failure, 'value') and hasattr(failure.value, 'response'):
            response = failure.value.response
            if response:
                self.logger.info("Attempting to extract content from failed request")
                
                # Look for links that might be articles
                article_links = response.css('a[href*="/online/"]::attr(href), a[href*="/news/"]::attr(href)').getall()
                if article_links:
                    self.logger.info(f"Found {len(article_links)} potential article links on failed page")





