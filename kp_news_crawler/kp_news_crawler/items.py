import scrapy

class NewsArticleItem(scrapy.Item):
    title = scrapy.Field()  # Required
    description = scrapy.Field()  # Required
    article_text = scrapy.Field()  # Required
    publication_datetime = scrapy.Field()  # Required
    header_photo_url = scrapy.Field()  # Optional
    #header_photo_base64 = scrapy.Field()  # Optional
    keywords = scrapy.Field()  # Required
    authors = scrapy.Field()  # Required
    source_url = scrapy.Field()  # Required
