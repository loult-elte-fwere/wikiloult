from os import path
from .data import pokemons
from colorsys import hsv_to_rgb
from hashlib import md5
from salt import SALT
from struct import pack
from flask_login import UserMixin 


with open(path.join(path.dirname(path.realpath(__file__)), "data/adjectifs.txt")) as adj_file:
    adjectives = adj_file.read().split()


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
        self.poke_adj = adjectives[adj_id]

    @classmethod
    def from_cookie_hash(cls, cookie_hash):
        color_rgb = hsv_to_rgb(cookie_hash[4] / 255, 0.8, 0.9)
        return cls('#' + pack('3B', *(int(255 * i) for i in color_rgb)).hex(), # color
                   (cookie_hash[2] | (cookie_hash[3] << 8)) % len(pokemons.pokemon) + 1,
                   (cookie_hash[5] | (cookie_hash[6] << 13)) % len(adjectives) + 1) # poke id


class User(UserMixin):

    def __init__(self, cookie):
        cookie_hash = md5((cookie + SALT).encode('utf8')).digest()
        self.voice_params = VoiceParameters.from_cookie_hash(cookie_hash)
        self.poke_params = PokeParameters.from_cookie_hash(cookie_hash)
        self.cookie = cookie
        self.user_id = cookie_hash.hex()[-16:]

    def get_id(self):
        return self.cookie
