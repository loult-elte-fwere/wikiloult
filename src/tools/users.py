from os import path

from config import ADMIN_COOKIES
from .data import pokemons
from colorsys import hsv_to_rgb
from hashlib import md5
from salt import SALT
from struct import pack
from flask_login import UserMixin
import json

DATA_FILES_FOLDER = path.join(path.dirname(path.realpath(__file__)), "data/")

with open(path.join(DATA_FILES_FOLDER, "adjectifs.txt")) as adj_file:
    adjectives = adj_file.read().splitlines()

with open(path.join(DATA_FILES_FOLDER, "metiers.txt")) as file:
    jobs = file.read().splitlines()

with open(path.join(DATA_FILES_FOLDER, "villes.json")) as file:
    cities = json.load(file)

with open(path.join(DATA_FILES_FOLDER, "sexualite.txt")) as file:
    sexual_orient = file.read().splitlines()


class VoiceParameters:

    def __init__(self, speed : int, pitch : int, voice_id : int):
        self.speed = speed
        self.pitch = pitch
        self.voice_id = voice_id

    @classmethod
    def from_cookie_hash(cls, cookie_hash):
        return cls((cookie_hash[5] % 80) + 90, # speed
                   cookie_hash[0] % 100, # pitch
                   cookie_hash[1]) # voice_id


class PokeParameters:

    def __init__(self, color, poke_id, adj_id):
        self.color = color
        self.poke_id = poke_id
        self.pokename = pokemons.pokemon[self.poke_id]
        self.poke_adj = adjectives[adj_id % len(adjectives)]
        self.img = str(self.poke_id).zfill(3)

    @classmethod
    def from_cookie_hash(cls, cookie_hash):
        color_rgb = hsv_to_rgb(cookie_hash[4] / 255, 0.8, 0.9)
        return cls('#' + pack('3B', *(int(255 * i) for i in color_rgb)).hex(), # color
                   (cookie_hash[2] | (cookie_hash[3] << 8)) % len(pokemons.pokemon) + 1,
                   (cookie_hash[5] | (cookie_hash[6] << 13)) % len(adjectives) + 1) # poke id


class PokeProfile:

    def __init__(self, job_id, age, city_id, sex_orient_id):
        self.job = jobs[job_id]
        self.age = age
        self.city, self.departement = cities[city_id]
        self.sex_orient = sexual_orient[sex_orient_id]

    @classmethod
    def from_cookie_hash(cls, cookie_hash):
        return cls((cookie_hash[4] | (cookie_hash[2] << 7)) % len(jobs), # job
                   (cookie_hash[3] | (cookie_hash[5] << 6)) % 62 + 18, # age
                   ((cookie_hash[6] * cookie_hash[4] << 17)) % len(cities), # city
                   (cookie_hash[2] | (cookie_hash[3] << 4)) % len(sexual_orient)) # sexual orientation


class User(UserMixin):

    def __init__(self, cookie):
        cookie_hash = md5((cookie + SALT).encode('utf8')).digest()
        self.voice_params = VoiceParameters.from_cookie_hash(cookie_hash)
        self.poke_params = PokeParameters.from_cookie_hash(cookie_hash)
        self.poke_profile = PokeProfile.from_cookie_hash(cookie_hash)
        self.cookie = cookie
        self.user_id = cookie_hash.hex()[-16:]
        self.is_admin = cookie in ADMIN_COOKIES

    def get_id(self):
        return self.cookie
