from flask import Flask, render_template

app = Flask(__name__)


@app.route("/")
def home():
    return render_template("index.html")


@app.route("/login", methods=['GET', 'POST'])
def login():
    """User login page"""
    return render_template("index.html")


@app.route("/page/<page_name>")
def page(page_name):
    """Display a wiki page"""
    return render_template("index.html")


@app.route("/page/<page_name>/edit", methods=['GET', 'POST'])
def page_edit(page_name):
    """Page edition form"""
    return render_template("index.html")


@app.route("/page/create", methods=['GET', 'POST'])
def page_create():
    """Page creation form (almost the same as the page edition form"""
    return render_template("index.html")


@app.route("/user/<cookie>")
def user_page(cookie):
    """User's personal page"""
    return render_template("index.html")


@app.route("/search")
def searc_page():
    """Search for a wiki page"""
    return render_template("index.html")