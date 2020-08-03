import re
import unicodedata
from collections import OrderedDict
from datetime import datetime
from html import escape
from typing import List

from cookie_factory import PokeParameters, PokeProfile, hash_cookie
from flask import current_app
from flask_login import UserMixin
from mongoengine import Document, StringField, BooleanField, ReferenceField, DateTimeField, ListField
from pymongo import MongoClient

from config import DB_ADDRESS, USERS_COLLECTION_NAME, PAGES_COLLECTION_NAME
from .rendering import WikiPageRenderer


class User(Document, UserMixin):
    cookie = StringField(primary_key=True)
    is_allowed = BooleanField(default=False)
    short_id = StringField(required=True)
    poke_page = ReferenceField('WikiPage')
    edits = ListField(ReferenceField("HistoryEntry"))
    registration_date = DateTimeField(default=datetime.now)

    @classmethod
    def create_user(cls, user_cookie: str):
        new_user = cls(cookie=user_cookie)
        new_user.short_id = new_user.cookie_hash.hex()[-16:]
        return new_user

    def get_id(self):
        return self.cookie

    @property
    def is_admin(self):
        return self.cookie in current_app.config["ADMIN_COOKIES"]

    @property
    def cookie_hash(self):
        return hash_cookie(self.cookie, current_app.config['SALT'])

    @property
    def poke_params(self) -> PokeParameters:
        return PokeParameters.from_cookie_hash(self.cookie_hash)

    @property
    def poke_profile(self) -> PokeProfile:
        return PokeProfile.from_cookie_hash(self.cookie_hash)


class HistoryEntry(Document):
    editor = ReferenceField(User)
    page = ReferenceField('WikiPage')
    title = StringField(required=True)
    markdown = StringField(required=True)
    edition_time = DateTimeField(default=datetime.now)

    @property
    def render(self):
        return WikiPageRenderer().render(escape(self.markdown))

    @classmethod
    def get_last_edited_pages(cls):
        last_edited_pages = []
        last_editor, last_page = None, None
        for history_entry in cls.objects().order_by("-edition_time")[:30]:
            if history_entry.editor != last_editor or history_entry.page != last_page:
                last_edited_pages.append({
                    "raw_text": re.sub('<[^<]+?>', '', history_entry.page.html_content),
                    "last_editor": history_entry.editor
                })
                last_editor = history_entry.editor
                last_page = history_entry.page
        return last_edited_pages

class WikiPage(Document):
    name = StringField(primary_key=True)
    title = StringField(required=True)
    html_content = StringField(required=True)
    markdown_content = StringField(required=True)
    history: List[HistoryEntry] = ListField(ReferenceField(HistoryEntry))
    last_edit: datetime = DateTimeField(default=datetime.now)
    creation_time: datetime = DateTimeField(default=datetime.now)

    meta = {'indexes': [
        {'fields': ['$title', "$markdown_content", "$name"],
         'default_language': 'french',
         'weights': {'title': 10, 'content': 5, 'name': 7}
        }
    ]}

    @classmethod
    def create_page(cls, name: str, title: str, markdown_content: str, editor: User):
        markdown_renderer = WikiPageRenderer()
        page_render = markdown_renderer.render(escape(markdown_content))
        new_page = cls(name=name,
                       title=title,
                       html_content=page_render,
                       markdown_content=markdown_content)
        new_page.save()
        first_edit = HistoryEntry(editor=editor,
                                  page=new_page,
                                  title=title,
                                  markdown=page_render)
        first_edit.save()
        new_page.history.append(first_edit)
        new_page.save()
        return new_page

    @property
    def audio_filename(self):
        return self.name + ".wav"

    def edit(self, markdown_content: str, page_title: str, editor: User):
        markdown_renderer = WikiPageRenderer()
        new_render = markdown_renderer.render(escape(markdown_content))
        history_entry = HistoryEntry(editor=editor,
                                     page=self,
                                     markdown=markdown_content,
                                     title=page_title)
        history_entry.save()
        self.title = page_title
        self.markdown_content = markdown_content
        self.html_content = new_render
        self.last_edit = datetime.now()
        self.history.append(history_entry)
        self.save()
        return history_entry

    @classmethod
    def get_all_pages_sorted(cls):
        def remove_accents(text):
            return ''.join(c for c in unicodedata.normalize('NFD', text)
                           if unicodedata.category(c) != 'Mn')

        def get_first_letter(text: str):
            text = text.lower()
            if text.startswith(("le", "la", "l'", "les")):
                text = re.sub(r"^(le|l'|la|les)\s+", "", text)
            return text[0]

        per_first_letter = OrderedDict()
        for page in cls.objects().order_by("title"):
            page: WikiPage
            first_letter = get_first_letter(remove_accents(page.title))
            if first_letter not in per_first_letter:
                per_first_letter[first_letter] = []
            per_first_letter[first_letter].append(page)
        return per_first_letter

    @classmethod
    def get_random_page(cls):
        result = cls.objects().aggregate([{"$sample": {"size": 1}}])
        return next(result)


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

    def user_exists(self, user_cookie: str) -> bool:
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

    def add_modification(self, user_cookie: str, page_name: str):
        self.users.update_one({"_id": user_cookie},
                              {"$push": {"modifications": {"page": page_name,
                                                           "date": datetime.datetime.utcnow()}}})

    def get_user_data(self, user_id: str):
        return self.users.find_one({"short_id": user_id})

    def update_user_text(self, user_cookie: str, markdown_content: str):
        markdown_renderer = WikiPageRenderer()
        html_render = markdown_renderer.render(escape(markdown_content))
        self.users.update_one({"_id": user_cookie},
                              {"$set": {"personal_text_html": html_render,
                                        "personal_text_markdown": markdown_content}})

    def is_allowed(self, user_cookie: str) -> bool:
        """Looks up if a user is allowed to edit/create pages or not"""
        result = self.users.find_one({"_id": user_cookie})
        return False if result is None else result["is_allowed"]


class WikiPagesConnector(BaseConnector):

    def __init__(self):
        super().__init__()
        self.pages = self.db[PAGES_COLLECTION_NAME]

    def create_page(self, page_name: str, markdown_content: str, page_title: str, editor_cookie: str):
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
                         "edition_time": datetime.datetime.utcnow(),
                         "title": page_title}
        self.pages.update_one({"_id": page_name},
                              {"$push": {"history": history_entry},
                               "$set": {"html_content": new_render,
                                        "markdown_content": markdown_content,
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

    def get_page_history(self, page_name: str):
        page_data = self.pages.find_one({"_id": page_name})
        if page_data is None:
            return None

        markdown_renderer = WikiPageRenderer()
        edit_title = page_data["title"]
        for i, entry in enumerate(page_data["history"]):
            if "title" in entry:
                edit_title = entry["title"]
            entry["title"] = edit_title
            entry["render"] = markdown_renderer.render(escape(entry["markdown"]))
            entry["edit_id"] = i
            entry["editor"] = User(entry["editor_cookie"])
        return page_data["history"]

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
                text = re.sub(r"^(le|l'|la|les)\s+", "", text)
            return text[0]

        query = self.pages.find().sort("title", 1)
        per_first_letter = OrderedDict()
        for page_data in query:
            first_letter = get_first_letter(remove_accents(page_data["title"]))
            if first_letter not in per_first_letter:
                per_first_letter[first_letter] = []
            per_first_letter[first_letter].append(page_data)
        return per_first_letter
