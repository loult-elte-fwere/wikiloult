import pymongo
import argparse
from datetime import datetime
from flask import Flask
from mongoengine import connect
from wikiloult.models import User, WikiPage, HistoryEntry

DB_ADDRESS = "mongodb://localhost:27017/"

argparser = argparse.ArgumentParser()
argparser.add_argument("--old_db", default="wikiloult_old")
argparser.add_argument("--new_db", default="wikiloult")
argparser.add_argument("--salt")

if __name__ == '__main__':

    args = argparser.parse_args()
    app = Flask(__name__)
    app.config["SALT"] = args.salt
    old_db = pymongo.MongoClient(DB_ADDRESS)[args.old_db]
    new_db = connect(args.new_db)
    new_db.drop_database(args.new_db)

    with app.app_context():
        print("Copying users...")
        new_users = {}
        for user in old_db["users"].find():
            new_user = User.create_user(user["_id"])
            new_user.is_allowed = user["is_allowed"]
            new_user.registration_date = user["registration_date"]
            new_users[user["_id"]] = new_user

        User.objects.insert(list(new_users.values()))
        print("Done.")

        print("Copying pages...")
        for wiki_page in old_db["pages"].find():
            new_page = WikiPage(name=wiki_page["_id"],
                                title=wiki_page["title"],
                                html_content=wiki_page["html_content"],
                                markdown_content=wiki_page["markdown_content"],
                                last_edit=wiki_page["last_edit"],
                                creation_time=wiki_page["creation_date"])
            new_page.save()
            history_entries = []
            for edit in wiki_page["history"]:
                if edit["editor_cookie"] not in new_users:
                    user = User.create_user(edit["editor_cookie"])
                    user.save()
                    new_users[user.cookie] = user
                new_entry = HistoryEntry(editor=new_users[edit["editor_cookie"]],
                                         markdown=edit["markdown"],
                                         edition_time=edit["edition_time"],
                                         title=edit.get("title", new_page.title),
                                         page=new_page)
                history_entries.append(new_entry)
            HistoryEntry.objects.insert(history_entries)
            new_page.history = history_entries
            new_page.save()
        print("Done.")

        print("Registering user edits")
        for user in new_users.values():
            user.edits = list(HistoryEntry.objects(editor=user).order_by('+edition_time'))
            user.save()
        print("Done.")