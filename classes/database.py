# database.py
from tinydb import TinyDB, Query
from tinydb.storages import JSONStorage
from tinydb.middlewares import CachingMiddleware

class Database:
    def __init__(self, db_path='./podcasts.db'):
        """
        Initialize the TinyDB database.
        
        :param db_path: Path to the JSON file where the database will be stored.
        """
        self.db = TinyDB(db_path, storage=CachingMiddleware(JSONStorage))
        self.table = self.db.table('podcasts')
        self.Podcast = Query()
    
    def insert_podcast(self, hash, metadata, external_data):
        """
        Insert a new podcast entry into the database.
        
        :param hash: Hash used as a unique identifier.
        :param metadata: Metadata dictionary retrieved from a JSON file.
        :param external_data: Dictionary with external service data.
        """
        podcast_data = {
            'hash': hash,
            'metadata': metadata,
            'external_data': external_data
        }
        self.table.upsert(podcast_data, self.Podcast.hash == hash)
    
    def get_podcast(self, hash):
        """
        Retrieve a podcast entry by its hash.
        
        :param hash: Hash to get.
        :return: Dictionary containing the podcast data, or None if not found.
        """
        result = self.table.search(self.Podcast.hash == hash)
        return result[0] if result else None
    
    def update_podcast(self, hash, **kwargs):
        """
        Update fields of an existing podcast entry.
        
        :param hash: Hash to get.
        :param kwargs: Fields to update with their new values.
        """
        self.table.update(kwargs, self.Podcast.hash == hash)
    
    def delete_podcast(self, hash):
        """
        Delete a podcast entry from the database.
        
        :param hash: Hash to delete.
        """
        self.table.remove(self.Podcast.hash == hash)
    
    def get_all_podcasts(self):
        """
        Retrieve all podcast entries from the database.
        
        :return: List of dictionaries containing podcast data.
        """
        return self.table.all()
    
    def close(self):
        """
        Close the database connection.
        """
        self.db.close()
