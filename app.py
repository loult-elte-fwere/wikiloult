from flask import Flask

from wikiloult.configs import get_config, set_up_db
from wikiloult.views import *

app = Flask(__name__)
config = get_config()
app.config.from_object(config)
set_up_db(config)
login_manager.init_app(app)

@app.errorhandler(404)
def page_not_found(e):
    return render_template('404.html'), 404


@app.errorhandler(429)
def ratelimit_handler(e):
    return render_template('error.html',
                           message="Trop de requêtes : Nombre limite d'inscription atteint"), 429


app.add_url_rule('/', view_func=HomeView.as_view('home'))
app.add_url_rule('/login', view_func=LoginView.as_view('login'))
app.add_url_rule('/logout', view_func=LogoutView.as_view('logout'))
app.add_url_rule('/register', view_func=RegistrationView.as_view('register'))
app.add_url_rule('/user/<user_id>', view_func=UserPageView.as_view('user_page'))
app.add_url_rule('/page/<page_name>', view_func=PageView.as_view('page'))
app.add_url_rule('/page/<page_name>/history', view_func=PageHistoryView.as_view('page_history'))
app.add_url_rule('/page/<page_name>/edit', view_func=PageEditView.as_view('page_edit'))
app.add_url_rule('/page/create', view_func=PageCreateView.as_view('page_create'))
app.add_url_rule('/page/restore', view_func=PageRestoreView.as_view('page_restore'))
app.add_url_rule('/page/search', view_func=SearchPageView.as_view('search_page'))
app.add_url_rule('/random', view_func=RandomPageView.as_view('random_page'))
app.add_url_rule('/last_edits', view_func=LastEditsView.as_view('last_edits'))
app.add_url_rule('/all', view_func=AllPagesView.as_view('all_pages'))
app.add_url_rule('/rules', view_func=RulesView.as_view('rules'))

if __name__ == "__main__":
    app.config['DEBUG'] = True
    app.run()
