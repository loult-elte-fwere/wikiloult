from html import escape
from pathlib import Path
import re

from flask import render_template, make_response, request, redirect, url_for, current_app, abort, jsonify
from flask.views import MethodView
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address
from flask_login import LoginManager, logout_user, current_user, login_user, login_required
from mongoengine import DoesNotExist

from .models import User, WikiPage, HistoryEntry
from .rendering import WikiPageRenderer, audio_render

current_user: User

# flask-login
login_manager = LoginManager()
login_manager.login_view = "login"
login_manager.login_message = "Vous devez être connectés pour créer ou éditer des pages"


@login_manager.user_loader
def load_user(user_cookie):
    try:
        return User.objects.get(cookie=user_cookie)
    except DoesNotExist:
        return None


# limiter to temper with registration abuse
registration_limiter = Limiter(
    current_app,
    key_func=get_remote_address)


class BaseMethodView(MethodView):

    def dispatch_request(self, *args, **kwargs):
        cookie = request.cookies.get("id", None)
        if cookie is not None:
            try:
                user: User = User.objects.get(cookie=cookie)
            except DoesNotExist:
                pass
            else:
                login_user(user)
        # try:
        return super().dispatch_request(*args, **kwargs)
        # except DoesNotExist:
        #     abort(404)


class SplashHomeView(BaseMethodView):

    def get(self):
        return render_template("homepage.html")


class HomeView(BaseMethodView):

    def get(self):
        return render_template("homepage.html")


class LoginView(BaseMethodView):

    def get(self):
        return render_template("login.html")

    def post(self):
        user_cookie = request.form["user"]
        try:
            user = User.objects.get(cookie=user_cookie)
        except DoesNotExist:
            return redirect(url_for('register'))
        else:
            message = "Connectèw."

        login_user(user)
        return render_template("login.html", message=message)


class LogoutView(BaseMethodView):
    """Logout of the website : destroy session and delete the cookie"""

    def get(self):
        logout_user()
        resp = make_response(render_template("homepage.html"))
        resp.set_cookie('id', '', expires=0)  # destroy the cookie by making it expire immediately
        return resp


class RegistrationView(BaseMethodView):
    decorators = [registration_limiter.limit("1/day",
                                             error_message="Une inscription par jour.")]

    def post(self):
        if current_user.is_authenticated:
            message = "Vous êtes déjà connecté"
        else:
            user_cookie = request.form["user"]
            try:
                user = User.objects.get(cookie=user_cookie)
            except DoesNotExist:
                new_user = User.create_user(user_cookie)
                new_user.save()
                message = """Votre compte utilisateur a été créé.
                Un administrateur doit le valider pour que vous puissiez aussi éditer des pages."""
            else:
                message = "Utilisateur déjà existant."
                login_user(User(user_cookie))

        return render_template("login.html", message=message, base_template='base.html')


class UserPageView(BaseMethodView):
    """Display a user's page"""

    def get(self, user_id: str):
        user: User = User.objects.get(shot_id=user_id)
        return render_template("user_page.html", user=user)


class PageView(BaseMethodView):
    """Display a wiki page"""

    def get(self, page_name: str):
        try:
            page: WikiPage = WikiPage.objects.get(name=page_name)
        except DoesNotExist:
            page = None
        return render_template("wiki_page.html", page=page)


class PageHistoryView(BaseMethodView):
    """Display a page's edit history"""

    def get(self, page_name: str):
        page: WikiPage = WikiPage.objects.get(name=page_name)
        return render_template("page_history.html",
                               page_history=reversed(page.history),
                               page_name=page_name)


class PageEditView(BaseMethodView):
    """Page edition form"""
    decorators = [login_required]

    def get(self, page_name: str):
        page: WikiPage = WikiPage.objects.get(name=page_name)
        return render_template("page_edit.html", page=page)

    def post(self, page_name: str):
        title = request.form["title"]
        markdown_content = request.form["content"]

        # if the user asked only for a preview, don't save and just render the page
        if request.form.get("preview", None) is not None:
            markdown_renderer = WikiPageRenderer()
            html_render = markdown_renderer.render(escape(markdown_content))
            return render_template("page_edit.html",
                                   page_name=page_name,
                                   page_content=markdown_content,
                                   page_title=title,
                                   preview=html_render)

        # same if there's something missing
        if not title.strip() or not markdown_content.strip():
            return render_template("page_edit.html",
                                   page_name=page_name,
                                   page_content=markdown_content,
                                   page_title=title,
                                   message="Le titre ni le contenu ne doivent être vides.")

        # else, we just save
        page: WikiPage = WikiPage.objects.get(name=page_name)
        edit = page.edit(markdown_content, title, current_user)
        audio_render(title, Path(current_app.config["AUDIO_RENDER_FOLDER"]) / Path(page_name + ".wav"))
        current_user.edits.append(edit)
        current_user.save()
        return redirect(url_for("page", page_name=page_name))


class PageRestoreView(BaseMethodView):
    """Restore a page to a previous edit ID"""
    decorators = [login_required]

    def get(self):
        if not current_user.is_admin:
            abort(403)

        edit_id = int(request.args.get('edit_id'))
        history_entry: HistoryEntry = HistoryEntry.objects.get(id=edit_id)
        return render_template("page_edit.html",
                               page_name=history_entry.page.name,
                               page_content=history_entry.markdown,
                               page_title=history_entry.title)


class PageCreateView(BaseMethodView):
    decorators = [login_required]

    def get(self):
        return render_template("page_create.html",
                               page_name=request.args.get("page_name", None))

    def post(self):
        page_name = request.form["name"]
        title = request.form["title"]
        markdown_content = request.form["content"]

        if request.form.get("preview", None) is not None:
            markdown_renderer = WikiPageRenderer()
            html_render = markdown_renderer.render(escape(markdown_content))
            return render_template("page_create.html",
                                   page_content=markdown_content,
                                   page_title=title,
                                   page_name=page_name,
                                   preview=html_render)

        error_message = None
        if not title.strip() or not markdown_content.strip() or not page_name.strip():
            error_message = "Le nom de page, titre ou le contenu ne doivent être vides."
        elif not re.match("^[a-zA-Z_]*$", page_name):
            error_message = "Le nom de la page ne doit contenir que des lettres et des tirets du bas."
        elif WikiPage.objects.get(name=page_name) is not None:
            error_message = "Une page portant ce nom existe déjà, changez le nom svp mr."

        if error_message is not None:
            return render_template("page_create.html",
                                   page_content=markdown_content,
                                   page_title=title,
                                   page_name=page_name,
                                   message=error_message)

        WikiPage.create_page(page_name.lower(), title, markdown_content, current_user)
        current_app.config["AUDIO_RENDER_FOLDER"].mkdir(exist_ok=True, parents=True)
        new_wav_path = current_app.config["AUDIO_RENDER_FOLDER"] / Path(page_name + ".wav")
        audio_render(title, str(new_wav_path))
        return redirect(url_for("page", page_name=page_name))


class SearchPageView(BaseMethodView):
    """Search for a wiki page"""

    def get(self):
        search_query = request.args.get('query', '')
        results = list(WikiPage.objects.search_text(search_query))
        for result in results:
            result.raw_text = re.sub('<[^<]+?>', '', result.html_content)
        return render_template("page_search.html", results_list=results)


class RandomPageView(BaseMethodView):
    """Search for a wiki page"""

    def get(self):
        return redirect(url_for("page", page_name=WikiPage.get_random_page()["_id"]))


class LastEditsView(BaseMethodView):
    """Display pages that where last edited"""

    def get(self):
        last_edited_pages = HistoryEntry.get_last_edited_pages()
        return render_template("last_edited.html", results_list=last_edited_pages)


class LastEditsJSONEndpoint(BaseMethodView):
    """RESTful call to retrieve pages that where last edited"""

    def get(self):
        return jsonify(HistoryEntry.get_last_edited_pages())


class AllPagesView(BaseMethodView):

    def get(self):
        return render_template("all_pages.html", pages_per_first_letter=WikiPage.get_all_pages_sorted())


class RulesView(BaseMethodView):

    def get(self):
        return render_template("rules.html")


class UserListView(BaseMethodView):
    decorators = [login_required]

    def get(self):
        if not current_user.is_admin:
            return abort(403)

        if request.get("action") is not None:
            action = request.get("action")
            short_id = request.get("userid")
            user = User.objects(short_id=short_id)
            if action == "allow":
                user.is_allowed = True
            elif action == "block":
                user.is_allowed = False
            user.save()

        return render_template("users_list.html", users=User.objects)
