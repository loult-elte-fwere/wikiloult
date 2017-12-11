
from flask_admin.contrib.pymongo import ModelView
from flask_admin import expose, AdminIndexView
from wtforms import form, fields

from config import ADMIN_COOKIES
from .users import User
import flask_login as login
from flask import redirect, url_for, abort

class UserForm(form.Form):
    is_allowed = fields.BooleanField('Is Allowed')
    _id = fields.StringField("User cookie")


class UserView(ModelView):
    column_list = ('poke_name', 'is_allowed', 'registration_date')
    column_sortable_list = ('is_allowed', 'registration_date')

    form = UserForm

    def get_list(self, *args, **kwargs):
        """Using the user's cookie to compute the actual pokemon name"""
        count, data = super().get_list(*args, **kwargs)
        for item in data:
            user_obj = User(item["_id"])
            item["poke_name"] = user_obj.poke_params.pokename + " " + user_obj.poke_params.poke_adj
        return count, data


class CheckCookieAdminView(AdminIndexView):

    @expose('/')
    def index(self):
        if not login.current_user.is_authenticated:
            return redirect(url_for('login'))

        if login.current_user.cookie not in ADMIN_COOKIES:
            abort(503)

        return super().index()