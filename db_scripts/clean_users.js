#!/usr/bin/env mongo
var db = new Mongo().getDB("wikiloult");
db.users.deleteMany({ "is_allowed" : false});