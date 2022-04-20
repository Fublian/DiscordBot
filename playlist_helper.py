from urllib.parse import urlparse
from urllib.parse import parse_qs
from yt_source import YTSource
import pytube
import discord
import requests
import json
import asyncio
import nest_asyncio
import config

DOMAINS = ['www.youtube.com', 'open.spotify.com']

def evaluate_search(phrase):
	parsed = urlparse(phrase)
	url_obj = {
		'domain': DOMAINS[0],	#Youtube as default
		'url': False,
		'playlist': False,
		'playlist_url': None
	}
	# No valid URL, search default youtube
	if not parsed[1] or parsed[1] not in DOMAINS:
		return url_obj

	# URL is valid and it is part of our DOMAINS
	url_obj['domain'] = parsed[1]
	url_obj['url'] = True

	try:
		if url_obj['domain'] == DOMAINS[0]:
			if parse_qs(parsed.query)['list'][0]:
				url_obj['playlist'] = True
				url_obj['playlist_url'] = parse_qs(parsed.query)['list'][0]
		elif url_obj['domain'] == DOMAINS[1]:
			if parsed[2].startswith('/playlist'):
				url_obj['playlist'] = True
				url_obj['playlist_url'] = phrase
		return url_obj
	except KeyError:
		return url_obj


def get_yt_playlist(playlist_id):
	API_KEY = config.YOUTUBE_API_KEY
	page_token = ""
	URLS = []
	paging = True
	prefix = "https://www.youtube.com/watch?v="

	while paging:
		paging = False
		url = f"https://youtube.googleapis.com/youtube/v3/playlistItems?part=snippet%2C%20status&maxResults=50&{page_token}playlistId={playlist_id}&fields=nextPageToken%2C%20pageInfo%2C%20items%2Fsnippet(resourceId)%2C%20items%2Fstatus&key={API_KEY}"
		response = requests.get(url)

		if (response.status_code != 200):
			print(f'Error getting playlist from the Youtube V3 API')
			return []

		resp = json.loads(response.text)

		
		next_token = resp.get('nextPageToken')
		
		if next_token:
			page_token = f'pageToken={str(next_token)}&'
			paging = True
		for item in resp['items']:
			status = item['status']['privacyStatus']
			if status == 'public':
				URLS.append(f"{prefix}{item['snippet']['resourceId']['videoId']}")
	return URLS

async def create_sources(ctx, player, urls, loop, download):
	sources = []
	for url in urls:
		source = await YTSource.create_source(ctx, url, loop = loop, download=download, quiet = True)
		sources.append(source)
	return sources

def generate_yt_playlist_ebmeded(playlist, length, playlist_url):

	longest = len(max([song['title'] for song in playlist], key=len))

	fmt_queue = '\n'.join(f'**` {i+1}. {song["title"]+(longest-len(song["title"]))*" "}   `**' for i, song in enumerate(playlist))
	if length > 5:
		#fmt_queue += '   \n\u2022 \u2022 \u2022'
		fmt_queue += f'\n**` \u22EE `**\n'

	pl_info = get_playlist_info(playlist_url)
	pl_embed = discord.Embed(title=f"Queuing Playlist - {pl_info['title']}", url=pl_info['playlist_url'],color=0xCC0000, description=fmt_queue)
	pl_embed.set_thumbnail(url=pl_info['thumbnail'])

	pl_embed.set_author(name=pl_info['channel_name'], url=pl_info['channel_url'], icon_url=pl_info['channel_icon_url'])
	pl_embed.set_footer(text=f'{len(playlist)} of {length} in total')
	return pl_embed


def get_playlist_info(playlist_url):
	#try:
	yt = pytube.Playlist(playlist_url)
	pl_info = {}
	pl_info['title'] = yt.title
	pl_info['playlist_url'] = "https://www.youtube.com/playlist?list="+yt.playlist_id
	pl_info['thumbnail'] = yt.initial_data['microformat']['microformatDataRenderer']['thumbnail']['thumbnails'][0]['url']
	pl_info['channel_name'] = yt.owner
	pl_info['channel_url'] = yt.owner_url
	ch = pytube.Channel(yt.owner_url)
	pl_info['channel_icon_url'] = ch.initial_data['header']['c4TabbedHeaderRenderer']['avatar']['thumbnails'][0]['url']
	return pl_info
	#except:
	#	return None
