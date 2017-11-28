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

    def user_exists(self, user_cookie : str) -> bool:
        pass

    def register_user(self, user_cookie: str):
        """Registers user cookie as a new user. Sets authorization to pending."""
        pass

    def authorize_user(self, user_cookie: str):
        """Authorize user to create/edit pages"""
        pass

    def get_user_data(self, user_cookie: str):
        pass

    def is_allowed(self, user_cookie: str) -> bool:
        """Looks up if a user is allowed to edit/create pages or not"""
        pass


class WikiPagesConnector(BaseConnector):

    def __init__(self):
        super().__init__()
        self.pages = self.db[PAGES_COLLECTION_NAME]

    def create_page(self, page_name : str, markdown_content: str, page_title: str, editor_cookie: str):
        pass

    def edit_page(self, page_name: str, markdown_content: str, page_title: str, editor_cookie : str):
        pass

    def search_page(self, search_query: str):
        pass

    def get_page_data(self, page_name : str):
        pass