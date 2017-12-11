import datetime
from html import escape

from pymongo import MongoClient
from config import DB_ADDRESS, USERS_COLLECTION_NAME, PAGES_COLLECTION_NAME

from .users import User
from .rendering import WikiPageRenderer


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
        result = self.users.find_one({"_id": user_cookie})
        return result is not None

    def register_user(self, user_cookie: str):
        """Registers user cookie as a new user. Sets authorization to pending."""
        user_obj = User(user_cookie)
        new_user_data = {"_id": user_cookie,
                         "is_allowed": False,
                         "short_id": user_obj.user_id,
                         "modifications": [],
                         "registration_date": datetime.datetime.utcnow(),
                         "personal_text_raw": None,
                         "personal_text_render": None}
        self.users.insert_one(new_user_data)

    def add_modification(self, user_cookie : str, page_name : str):
        self.users.update_one({"_id": user_cookie},
                              {"$push": {"modifications" : {"page": page_name,
                                                            "date": datetime.datetime.utcnow()}}})

    def get_user_data(self, user_id: str):
        return self.users.find_one({"short_id": user_id})

    def is_allowed(self, user_cookie: str) -> bool:
        """Looks up if a user is allowed to edit/create pages or not"""
        result = self.users.find_one({"_id": user_cookie})
        return False if result is None else result["is_allowed"]


class WikiPagesConnector(BaseConnector):

    def __init__(self):
        super().__init__()
        self.pages = self.db[PAGES_COLLECTION_NAME]

    def create_page(self, page_name : str, markdown_content: str, page_title: str, editor_userid: str):
        markdown_renderer = WikiPageRenderer()
        page_render = markdown_renderer.render(escape(markdown_content))
        page_data = {"_id": page_name,
                     "title": page_title,
                     "html_content": page_render,
                     "history": [{"editor_id": editor_userid,
                                  "markdown": markdown_content,
                                  "edition_time": datetime.datetime.utcnow()}],
                     "last_edit": datetime.datetime.utcnow(),
                     "creation_date": datetime.datetime.utcnow()}
        self.pages.insert_one(page_data)

    def edit_page(self, page_name: str, markdown_content: str, page_title: str, editor_userid : str):
        markdown_renderer = WikiPageRenderer()
        new_render = markdown_renderer.render(escape(markdown_content))
        history_entry = {"editor_id": editor_userid,
                         "markdown": markdown_content,
                         "edition_time": datetime.datetime.utcnow()}
        self.pages.update_one({"_id": page_name},
                              {"$push": {"history": history_entry},
                               "$set": {"html_content": new_render,
                                        "title": page_title,
                                        "last_edit": datetime.datetime.utcnow()}})

    def search_pages(self, search_query: str):
        return self.pages.find({"$text": {"$search": search_query.lower()}})

    def get_page_data(self, page_name : str):
        page_data = self.pages.find_one({"_id" : page_name})
        if page_data is None:
            return None
        page_data["history"] = [{"editor" : User(entry["editor_id"]),
                                 "edition_time": entry["edition_time"]} for entry in page_data["history"]]
        return page_data

    def get_random_page(self):
        result = self.pages.aggregate([{"$sample": {"size": 1}}])
        return next(result)["_id"]

    def get_last_edited(self, number : int):
        return  self.pages.aggregate([{"$unwind": "$history"},
                                      {"$sort": {"history.edition_time": 1}},
                                      {"$limit": number}])