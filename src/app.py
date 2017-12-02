from flask import Flask, render_template, session, redirect, url_for, request, make_response
import re

from tools.models import UsersConnector, WikiPagesConnector
from tools.users import User

from config import SECRET_KEY

app = Flask(__name__)

app.config['SECRET_KEY'] = SECRET_KEY

app.config.from_envvar('DEV_SETTINGS', silent=True)

def autologin(function):
    """Decorator that tries to log in automatically is the cookie is already set
    by a past login"""
    pass


@app.route("/")
def home():
    return render_template("index.html")


@app.route("/login", methods=['GET', 'POST'])
def login():
    """User login page"""
    if "user" in session:
        redirect(url_for("user_page", user_id=session["user"]['user_id']))

    if request.method == "GET":
        return render_template("login.html")

    elif request.method == "POST":
        user_cookie = request.form["user"]
        user_cnctr = UsersConnector()

        if not user_cnctr.user_exists(user_cookie):
            user_cnctr.register_user(user_cookie)
            message = """"Votre compte utilisateur a été créé. 
            Un administrateur doit le valider pour que vous puissiez aussi éditer des pages"""
        else:
            message = "Connectèw."

        # TypeError: <tools.users.User object at ... > is not JSON serializable
        session["user"] = User(user_cookie).serialize()
        resp = make_response(render_template("login.html", message=message))
        resp.set_cookie("id", user_cookie)
        return resp

@app.route("/logout")
def logout():
    """Logout of the website : destroy session and delete the cookie"""
    session.pop("user", None)
    resp = make_response(render_template("index.html"))
    resp.set_cookie('id', '', expires=0) # destroy the cookie by making it expire immediately
    return resp


@app.route("/page/<page_name>")
def page(page_name):
    """Display a wiki page"""
    page_cnctr = WikiPagesConnector()
    return render_template("wiki_page.html",
                           page_data=page_cnctr.get_page_data(page_name),
                           page_name=page_name)


@app.route("/page/<page_name>/edit", methods=['GET', 'POST'])
def page_edit(page_name):
    """Page edition form"""
    # TODO : faire une fonction preview aussi
    if "user" not in session:
        return render_template("error.html", message="Vous devez être connectés pour éditer la page")

    user_cnctr = UsersConnector()
    if not user_cnctr.is_allowed(session["user"]['cookie']):
        return render_template("error.html", message="Vous n'êtes pas encore autorisés à éditer des pages")

    page_cnctr = WikiPagesConnector()
    if request.method == "GET":
        page_data = page_cnctr.get_page_data(page_name)
        return render_template("page_edit.html",
                               page_content=page_data["markdown_content"],
                               page_title=page_data["title"])

    elif request.method == "POST":
        title = request.form["title"]
        markdown_content = request.form["content"]
        if not title.strip() or not markdown_content.strip():
            return render_template("page_edit.html",
                                   page_content=markdown_content,
                                   page_title=title,
                                   message="Le titre ni le contenu ne doivent être vides.")

        page_cnctr.edit_page(page_name, markdown_content, title, session["user"]['cookie'])
        redirect(url_for("page", page_name=page_name))


@app.route("/page/create", methods=['GET', 'POST'])
def page_create():
    """Page creation form (almost the same as the page edition form"""

    if "user" not in session:
        return render_template("error.html", message="Vous devez être connectés pour éditer la page")

    user_cnctr = UsersConnector()
    if not user_cnctr.is_allowed(session["user"]['cookie']):
        return render_template("error.html", message="Vous n'êtes pas encore autorisés à éditer des pages")

    page_cnctr = WikiPagesConnector()
    if request.method == "GET":
        return render_template("page_create.html")

    elif request.method == "POST":
        page_name = request.form["name"]
        title = request.form["title"]
        markdown_content = request.form["content"]

        error_message = None
        if not title.strip() or not markdown_content.strip() or not page_name.strip():
            error_message = "Le nom de page, titre ou le contenu ne doivent être vides."
        elif not re.match("^[a-zA-Z_]*$", page_name):
            error_message = "Le nom de la page ne doit contenir que des lettres et des tirets du bas"

        if error_message is not None:
            return render_template("page_create.html",
                                   page_content=markdown_content,
                                   page_title=title,
                                   page_name=page_name,
                                   message=error_message)

        page_cnctr.create_page(page_name.lower(), markdown_content, title, session["user"]['cookie'])
        redirect(url_for("page", page_name=page_name))
    return render_template("index.html")


@app.route("/user/<user_id>")
def user_page(user_id):
    """User's personal page"""
    return render_template("index.html")


@app.route("/search")
def search_page():
    """Search for a wiki page"""
    return render_template("index.html")


def main():
    app.run()

if(__name__ == "__main__"):
    main()
