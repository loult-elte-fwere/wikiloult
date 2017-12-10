#!/usr/bin/env mongo
var db = new Mongo().getDB("wikiloult");
db.pages.createIndex({title: "text", html_content : "text"});