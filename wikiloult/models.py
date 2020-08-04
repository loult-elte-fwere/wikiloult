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
    def get_last_edited_pages(cls, limit=30) -> List['WikiPage']:
        last_edited_pages = []
        last_editor, last_page = None, None
        for history_entry in cls.objects().order_by("-edition_time")[:limit]:
            if history_entry.editor != last_editor or history_entry.page != last_page:
                page = history_entry.page
                page.last_editor = history_entry.editor
                last_edited_pages.append(page)
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

    @property
    def raw_text(self):
        return re.sub('<[^<]+?>', '', self.html_content)

    @property
    def squashed_history(self):
        last_editor = None
        history = []
        for entry in self.history:
            if last_editor != entry.editor:
                history.append(entry)
                last_editor = entry.editor
        return list(reversed(history))

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
