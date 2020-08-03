import pymongo
import argparse
from datetime import datetime
from mongoengine import connect
from wikiloult.models import User, WikiPage, HistoryEntry

DB_ADDRESS = "mongodb://localhost:27017/"

argparser = argparse.ArgumentParser()
argparser.add_argument("--old_db", default="wikiloult_old")
argparser.add_argument("--new_db", default="wikiloult")

if __name__ == '__main__':

    args = argparser.parse_args()
    old_db = pymongo.MongoClient(DB_ADDRESS)[args.old_db]
    connect(args.new_db)

    print("Copying users...")
    new_users = []
    for user in old_db["users"].find():
        new_user = User.create_user(user["_id"])
        new_user.is_allowed = user["is_allowed"]
        new_user.registration_date = user["registration_date"]

    User.objects.insert(new_users)
    print("Done.")

    print("Copying pages...")
    for wiki_page in old_db["pages"].find():
        new_page = WikiPage(name=wiki_page["name"],
                            title=wiki_page["title"],
                            html_content=wiki_page["html_content"],
                            markdown_content=wiki_page["markdown_content"],
                            last_edit=wiki_page["last_edit"],
                            creation_date=wiki_page["creation_date"])
        new_page.save()
        history_entries = []
        for edit in wiki_page["history"]:
            new_entry = HistoryEntry(editor=edit["editor_cookie"],
                                     markdown=edit["markdown"],
                                     edition_time=edit["edition_time"],
                                     title=edit["title"],
                                     page=new_page)
        HistoryEntry.objects.insert(history_entries)
        new_page.history = history_entries
        new_page.save()

    print("Done.")