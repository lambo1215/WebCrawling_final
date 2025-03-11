import pymongo
import logging
from itemadapter import ItemAdapter

class MongoDBPipeline:
    collection_name = 'articles'
    
    def __init__(self, mongo_uri, mongo_db):
        self.mongo_uri = mongo_uri
        self.mongo_db = mongo_db
        self.client = None
        self.db = None
        self.processed_count = 0
        self.max_records = 1500
    
    @classmethod
    def from_crawler(cls, crawler):
        return cls(
            mongo_uri=crawler.settings.get('MONGODB_URI', 'mongodb://localhost:27017'),
            mongo_db=crawler.settings.get('MONGODB_DATABASE', 'kp_news')
        )
    
    def open_spider(self, spider):
        self.client = pymongo.MongoClient(self.mongo_uri)
        self.db = self.client[self.mongo_db]
        logging.info(f"Connected to MongoDB {self.mongo_db}.{self.collection_name}")
        
        # Get current count in the collection
        self.processed_count = self.db[self.collection_name].count_documents({})
        logging.info(f"Collection already has {self.processed_count} documents")
    
    def close_spider(self, spider):
        self.client.close()
    
    def process_item(self, item, spider):
        if self.processed_count >= self.max_records:
            logging.info(f"Reached maximum records limit ({self.max_records}). Skipping item.")
            return item

        try:
            result = self.db[self.collection_name].update_one(
                {'source_url': item['source_url']},
                {'$set': dict(item)},
                upsert=True
            )
            if result.upserted_id:
                self.processed_count += 1
                spider.logger.info(f"Stored new article: {item['title']} ({self.processed_count}/{self.max_records})")
            else:
                spider.logger.info(f"Updated existing article: {item['title']}")
        except Exception as e:
            spider.logger.error(f"Error saving to MongoDB: {e}")
        return item


import base64
import requests
from itemadapter import ItemAdapter

class PhotoDownloaderPipeline:
    def process_item(self, item, spider):
        adapter = ItemAdapter(item)
        photo_url = adapter.get('header_photo_url')
        
        if photo_url:
            try:
                response = requests.get(photo_url, timeout=10)
                if response.status_code == 200:
                    # Convert image to base64
                    base64_image = base64.b64encode(response.content).decode('utf-8')
                    adapter['header_photo_base64'] = base64_image
                    spider.logger.info(f"Downloaded and encoded image from {photo_url}")
            except Exception as e:
                spider.logger.error(f"Error downloading image from {photo_url}: {e}")
        
        return item
