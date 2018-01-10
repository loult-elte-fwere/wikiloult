import re
from mistune import Renderer, InlineLexer, Markdown
import voxpopuli


class WikiloultRenderer(Renderer):

    def wiki_link(self, alt, link):
        return '<a href="/page/%s">%s</a>' % (link, alt)

    def vocaroo_link(self, vocaroo_id):
        return '''
            <div class="vocaroo-player">
                <audio controls="">
                    <source src="http://vocaroo.com/media_command.php?media=%s&amp;command=download_mp3" type="audio/mpeg">
                    <source src="http://vocaroo.com/media_command.php?media=%s&amp;command=download_webm" type="audio/webm">
                </audio>
                <a class="my-auto" href="https://vocaroo.com/i/%s">[🔗]</a>
            </div>''' % (vocaroo_id, vocaroo_id, vocaroo_id)


class WikiloultLexer(InlineLexer):

    def enable_wiki_link(self):
        # add wiki_link rules
        self.rules.wiki_link = re.compile(
            r'\[\['                   # [[
            r'([\s\S]+?\|[a-zA-Z0-9_]+?)'   # Page du wiki|page_name
            r'\]\](?!\])'             # ]]
        )

        self.default_rules.insert(3, 'wiki_link')

    def output_wiki_link(self, m):
        text = m.group(1)
        alt, link = text.split('|')
        return self.renderer.wiki_link(alt, link)

    def enable_vocaroo_link(self):
        # add wiki_link rules
        self.rules.vocaroo = re.compile(
            r'\[\['                   # [[
            r'https?://vocaroo\.com/i/([0-9A-Za-z]+)'   # https://vocaroo\.com/i/(vocaroo_id)
            r'\]\](?!\])'             # ]]
        )

        self.default_rules.insert(3, 'vocaroo')

    def output_vocaroo(self, m):
        vocaroo_id = m.group(1)
        return self.renderer.vocaroo_link(vocaroo_id)


class WikiPageRenderer:

    def __init__(self):
        wiki_link_renderer = WikiloultRenderer()
        link_lexer = WikiloultLexer(wiki_link_renderer)
        link_lexer.enable_wiki_link()
        link_lexer.enable_vocaroo_link()
        self.renderer = Markdown(wiki_link_renderer, inline=link_lexer)

    def render(self, page_string : str):
        return self.renderer(page_string)


def audio_render(text, render_path):
    voice = voxpopuli.Voice(lang="fr", voice_id=1, pitch=60, speed=110)
    voice.to_audio(text, filename=render_path)