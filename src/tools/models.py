from pymongo import MongoClient
from config import DB_ADDRESS, USERS_COLLECTION_NAME, PAGES_COLLECTION_NAME


class BaseConnector:
    """Connects to the DB when instanciated"""

    def __init__(self):
        self.client = MongoClient(DB_ADDRESS)  # connecting to the db
        self.db = self.client["wikiloult"]


class UsersConnector(BaseConnector):
    """Connector dedicated to users"""

    def __init__(self):
        super().__init__()
        self.users = self.db[USERS_COLLECTION_NAME]


class WikiPagesConnector(BaseConnector):

    def __init__(self):
        super().__init__()
        self.pages = self.db[PAGES_COLLECTION_NAME]
