from googlesearch import search
from bs4 import BeautifulSoup
from urllib.parse import urlparse
import pytube
from lyricsgenius import Genius
import config
import discord


token = config.GENIUS_TOKEN

def get_lyrics(url):
	if not url:
		return

	yt = pytube.YouTube(url)

	query = f'{yt.title} Genius Lyrics'

	found_url = ''

	for result in search(query, tld="co.in", num=1, stop=1):
		found_url = result

	domain = urlparse(found_url).netloc
	if domain != 'genius.com':
		return
	try:
		genius = Genius(token, retries=3)
		lyric = genius.lyrics(song_url=found_url)
		return lyric
	except:
		return None

def generate_lyrics_ebmeded(lyrics, thumbnail, author, lyrics_url):
	
	lyrics_title, lyrics = lyrics.split('Lyrics', 1)
	lyric_list = lyrics.split('\n')
	lyric_list[-1] = ''.join([i for i in lyric_list[-1].split('Embed')[0] if not i.isdigit()])

	fmt_lyrics = '\n'.join(f'**   {line}   **' for line in lyric_list)

	lyrics_embed = discord.Embed(title=lyrics_title,url=lyrics_url ,color=0xCC0000, description=fmt_lyrics)
	lyrics_embed.set_thumbnail(url=thumbnail['url'])
	lyrics_embed.set_author(name=author['name'], url=author['channel_url'], icon_url=author['icon_url'])

	return lyrics_embed

