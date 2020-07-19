from flask.views import MethodView
from flask import Blueprint, render_template, make_response, request, redirect, url_for
from flask_login import LoginManager, logout_user, current_user, login_user
from .models import User
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address

# flask-login
login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = "login"
login_manager.login_message = "Vous devez être connectés pour créer ou éditer des pages"

@login_manager.user_loader
def load_user(user_cookie):
    return User(user_cookie)

# limiter to temper with registration abuse
registration_limiter = Limiter(
    app,
    key_func=get_remote_address)


class BaseMethodView(MethodView):


    def dispatch_request(self, *args, **kwargs):
        # TODO: take care of autologging here
        pass


class HomeView(BaseMethodView):

    def get(self):
        return render_template("homepage.html")


class LoginView(BaseMethodView):

    def get(self):
        return render_template("login.html")

    def post(self):
        user_cookie = request.form["user"]
        user_cnctr = UsersConnector()

        if not user_cnctr.user_exists(user_cookie):
            return redirect(url_for('register'))
        else:
            message = "Connectèw."

        login_user(User(user_cookie))
        return render_template("login.html", message=message)


class LogoutView(BaseMethodView):
    """Logout of the website : destroy session and delete the cookie"""

    def get(self):
        logout_user()
        resp = make_response(render_template("homepage.html"))
        resp.set_cookie('id', '', expires=0)  # destroy the cookie by making it expire immediately
        return resp


class RegistrationView(BaseMethodView):

    def get(self):
        if user_cnctr.user_exists(request.cookies.get("id", None)):
            message = "Connectèw."
        else:
            message = None
        return render_template("register.html", base_template='base.html', message=message)

    def post(self):
        user_cookie = request.form["user"]
        if not user_cnctr.user_exists(user_cookie):
            user_cnctr.register_user(user_cookie)
            message = """Votre compte utilisateur a été créé.
            Un administrateur doit le valider pour que vous puissiez aussi éditer des pages."""
        else:
            message = "Connectèw."
            login_user(User(user_cookie))
        return render_template("register.html", message=message, base_template='base.html')


class PageView(BaseMethodView):
    """Display a wiki page"""

    def get(self, page_name: str):
        page_cnctr = WikiPagesConnector()
        page_data = page_cnctr.get_page_data(page_name)
        return render_template("wiki_page.html",
                               page_data=page_data,
                               page_name=page_name,
                               audio_filename=page_name + ".wav")


class PageHistoryView(BaseMethodView):
    """Display a page's edit history"""

    def get(self, page_name: str):
        page_cnctr = WikiPagesConnector()
        page_history = page_cnctr.get_page_history(page_name)
        return render_template("page_history.html",
                               page_history=reversed(page_history),
                               page_name=page_name)


class PageEditView(BaseMethodView):
    """Page edition form"""

    def get(self, page_name: str):
        page_data = page_cnctr.get_page_data(page_name)
        return render_template("page_edit.html",
                               page_name=page_name,
                               page_content=page_data["markdown_content"],
                               page_title=page_data["title"])

    def post(self, page_name: str):
        # TODO: check for possible refactoring of this
        title = request.form["title"]
        markdown_content = request.form["content"]

        if request.form.get("preview", None) is not None:
            markdown_renderer = WikiPageRenderer()
            html_render = markdown_renderer.render(escape(markdown_content))
            return render_template("page_edit.html",
                                   page_name=page_name,
                                   page_content=markdown_content,
                                   page_title=title,
                                   preview=html_render)

        if not title.strip() or not markdown_content.strip():
            return render_template("page_edit.html",
                                   page_name=page_name,
                                   page_content=markdown_content,
                                   page_title=title,
                                   message="Le titre ni le contenu ne doivent être vides.")

        page_cnctr.edit_page(page_name, markdown_content, title, current_user.cookie)
        audio_render(title, join(AUDIO_RENDER_FOLDER, page_name + ".wav"))
        user_cnctr.add_modification(current_user.cookie, page_name)
        return redirect(url_for("page", page_name=page_name))


class PageRestoreView(BaseMethodView):
    """Restore a page to a previous edit ID"""

    def get(self):
        if not current_user.is_admin:
            abort(403)
        page_name = request.args.get('page_name')
        edit_id = int(request.args.get('edit_id'))
        page_cnctr = WikiPagesConnector()
        page_data = page_cnctr.get_page_data(page_name)
        if page_data is None:
            abort(500)

        page_history = page_cnctr.get_page_history(page_name)
        try:
            selected_edit = page_history[edit_id]
        except IndexError:
            abort(500)
        else:
            return render_template("page_edit.html",
                                   page_name=page_name,
                                   page_content=selected_edit["markdown"],
                                   page_title=selected_edit["title"])


class PageCreateView(BaseMethodView):

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
        elif page_cnctr.get_page_data(page_name) is not None:
            error_message = "Une page portant ce nom existe déjà, changez le nom svp mr."

        if error_message is not None:
            return render_template("page_create.html",
                                   page_content=markdown_content,
                                   page_title=title,
                                   page_name=page_name,
                                   message=error_message)

        page_cnctr.create_page(page_name.lower(), markdown_content, title, current_user.cookie)
        try:
            makedirs(AUDIO_RENDER_FOLDER)
        except FileExistsError:
            pass
        audio_render(title, join(AUDIO_RENDER_FOLDER, page_name + ".wav"))
        return redirect(url_for("page", page_name=page_name))


class SearchPageView(BaseMethodView):
    """Search for a wiki page"""

    def get(self):
        search_query = request.args.get('query', '')
        page_cnctr = WikiPagesConnector()
        results = page_cnctr.search_pages(search_query)
        for result in results:
            result["raw_text"] = re.sub('<[^<]+?>', '', result["html_content"])
        return render_template("page_search.html", results_list=results)


class RandomPageView(BaseMethodView):
    """Search for a wiki page"""

    def get(self):
        page_cnctr = WikiPagesConnector()
        return redirect(url_for("page", page_name=page_cnctr.get_random_page()))


class LastEditsView(BaseMethodView):
    """Display pages that where last edited"""

    def get(self):
        page_cnctr = WikiPagesConnector()
        last_edited_pages = []
        last_editor, last_page = None, None
        for page in page_cnctr.get_last_edited(30):
            if page["history"]["editor_cookie"] != last_editor or page["_id"] != last_page:
                page["raw_text"] = re.sub('<[^<]+?>', '', page["html_content"])
                page["last_editor"] = User(page["history"]["editor_cookie"])
                last_edited_pages.append(page)
                last_editor = page["history"]["editor_cookie"]
                last_page = page["_id"]

        return render_template("last_edited.html", results_list=last_edited_pages)


class AllPagesView(BaseMethodView):

    def get(self):
        page_cnctr = WikiPagesConnector()
        return render_template("all_pages.html", pages_per_first_letter=page_cnctr.get_all_pages_sorted())


class RulesView(BaseMethodView):

    def get(self):
        return render_template("rules.html")