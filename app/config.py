from os.path import join, dirname, realpath

# Addresse de la base de données.

DB_ADDRESS = "mongodb://localhost:27017/"
PAGES_COLLECTION_NAME = "pages"
USERS_COLLECTION_NAME = "users"
SECRET_KEY = "this is a big secret key ok"

# Here set the cookies of the admins, in their raw form
ADMIN_COOKIES = ["wiki"]

AUDIO_RENDER_FOLDER = join(dirname(realpath(__file__)), "static/sound/")
