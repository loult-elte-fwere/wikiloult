import re
from mistune import Renderer, InlineLexer, Markdown
import voxpopuli

class WikiLinkRenderer(Renderer):
    def wiki_link(self, alt, link):
        return '<a href="page/%s">%s</a>' % (link, alt)


class WikiLinkInlineLexer(InlineLexer):
    def enable_wiki_link(self):
        # add wiki_link rules
        self.rules.wiki_link = re.compile(
            r'\[\['                   # [[
            r'([\s\S]+?\|[a-zA-Z0-9_]+?)'   # Page du wiki|page_name
            r'\]\](?!\])'             # ]]
        )

        # Add wiki_link parser to default rules
        # you can insert it some place you like
        # but place matters, maybe 3 is not good
        self.default_rules.insert(3, 'wiki_link')

    def output_wiki_link(self, m):
        text = m.group(1)
        alt, link = text.split('|')
        # you can create an custom render
        # you can also return the html if you like
        return self.renderer.wiki_link(alt, link)


class WikiPageRenderer:

    def __init__(self):
        wiki_link_renderer = WikiLinkRenderer()
        link_lexer = WikiLinkInlineLexer(wiki_link_renderer)
        link_lexer.enable_wiki_link()
        self.renderer = Markdown(wiki_link_renderer, inline=link_lexer)

    def render(self, page_string : str):
        return self.renderer(page_string)


def audio_render(text, render_path):
    voice = voxpopuli.Voice(lang="fr", voice_id=1, pitch=60, speed=110)
    voice.to_audio(text, filename=render_path)