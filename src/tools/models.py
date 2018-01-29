import datetime
from html import escape
from collections import OrderedDict
import re
import unicodedata

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
                         "personal_text_markdown": None,
                         "personal_text_html": None}
        self.users.insert_one(new_user_data)

    def add_modification(self, user_cookie : str, page_name : str):
        self.users.update_one({"_id": user_cookie},
                              {"$push": {"modifications": {"page": page_name,
                                                           "date": datetime.datetime.utcnow()}}})

    def get_user_data(self, user_id: str):
        return self.users.find_one({"short_id": user_id})

    def update_user_text(self, user_cookie: str, markdown_content : str):
        markdown_renderer = WikiPageRenderer()
        html_render = markdown_renderer.render(escape(markdown_content))
        self.users.update_one({"_id": user_cookie},
                              {"$set": {"personal_text_html": html_render,
                                        "personal_text_markdown" : markdown_content}})

    def is_allowed(self, user_cookie: str) -> bool:
        """Looks up if a user is allowed to edit/create pages or not"""
        result = self.users.find_one({"_id": user_cookie})
        return False if result is None else result["is_allowed"]


class WikiPagesConnector(BaseConnector):

    def __init__(self):
        super().__init__()
        self.pages = self.db[PAGES_COLLECTION_NAME]

    def create_page(self, page_name : str, markdown_content: str, page_title: str, editor_cookie: str):
        markdown_renderer = WikiPageRenderer()
        page_render = markdown_renderer.render(escape(markdown_content))
        page_data = {"_id": page_name,
                     "title": page_title,
                     "html_content": page_render,
                     "markdown_content": markdown_content,
                     "history": [{"editor_cookie": editor_cookie,
                                  "markdown": markdown_content,
                                  "edition_time": datetime.datetime.utcnow()}],
                     "last_edit": datetime.datetime.utcnow(),
                     "creation_date": datetime.datetime.utcnow()}
        self.pages.insert_one(page_data)

    def edit_page(self, page_name: str, markdown_content: str, page_title: str, editor_cookie: str):
        markdown_renderer = WikiPageRenderer()
        new_render = markdown_renderer.render(escape(markdown_content))
        history_entry = {"editor_cookie": editor_cookie,
                         "markdown": markdown_content,
                         "edition_time": datetime.datetime.utcnow()}
        self.pages.update_one({"_id": page_name},
                              {"$push": {"history": history_entry},
                               "$set": {"html_content": new_render,
                                        "markdown_content" : markdown_content,
                                        "title": page_title,
                                        "last_edit": datetime.datetime.utcnow()}})

    def page_exists(self, page_name: str) -> bool:
        result = self.pages.find_one({"_id": page_name})
        return result is not None

    def search_pages(self, search_query: str):
        return list(self.pages.find({"$text": {"$search": search_query.lower()}}))

    def get_page_data(self, page_name: str):
        page_data = self.pages.find_one({"_id": page_name})
        if page_data is None:
            return None
        condensed_history = []
        prev_editor = None
        for entry in page_data["history"]:
            if prev_editor != entry["editor_cookie"]:
                condensed_history.append({"editor": User(entry["editor_cookie"]),
                                          "edition_time": entry["edition_time"]})
                prev_editor = entry["editor_cookie"]
        page_data["history"] = condensed_history[::-1]
        return page_data

    def get_random_page(self):
        result = self.pages.aggregate([{"$sample": {"size": 1}}])
        return next(result)["_id"]

    def get_last_edited(self, number: int):
        return list(self.pages.aggregate([{"$unwind": "$history"},
                                          {"$sort": {"history.edition_time": -1}},
                                          {"$limit": number}]))

    def get_all_pages_sorted(self):

        def remove_accents(text):
            return ''.join(c for c in unicodedata.normalize('NFD', text)
                    if unicodedata.category(c) != 'Mn')

        def get_first_letter(text: str):
            text = text.lower()
            if text.startswith(("le", "la", "l'", "les")):
                text = re.sub(r"^(le|l'|la|les)\s*", "", text)
            return text[0]

        query = self.pages.find().sort("title", 1)
        per_first_letter = OrderedDict()
        for page_data in query:
            first_letter = get_first_letter(remove_accents(page_data["title"]))
            if first_letter not in per_first_letter:
                per_first_letter[first_letter] = []
            per_first_letter[first_letter].append(page_data)
        return per_first_letter