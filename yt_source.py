import discord
import asyncio
from functools import partial
from youtube_dl import YoutubeDL
#from yt_dlp import YoutubeDL
import pytube
import requests
import json

import config


ytdlopts = {
	'format': 'bestaudio/best',
	'outtmpl': 'downloads/%(extractor)s-%(id)s-%(title)s.%(ext)s',
	'restrictfilenames': True,
	'noplaylist': True,
	'nocheckcertificate': True,
	'ignoreerrors': False,
	'logtostderr': False,
	'quiet': True,
	'no_warnings': True,
	'default_search': 'auto',
	'source_address': '0.0.0.0'
}

ffmpegopts = {
    'before_options': '-nostdin',
    'options': '-vn'
}

ytdl = YoutubeDL(ytdlopts)


class YTSource(discord.PCMVolumeTransformer):

	def __init__(self, source, *, data, requester):
		super().__init__(source)
		self.requester = requester
		
		self.title = data.get('title')
		self.web_url = data.get('webpage_url')
		self.views = data.get('view_count')
		self.thumbnail = data.get('thumbnails')[0]
		self.author = get_author_(self.web_url)
		self.type = 'youtube'


	def __getitem__(self, item: str):
		return self.__getattribute__(item)

	def __setitem__(self, item: str):
		return self.__getattribute__(item)

	def get_thumbnail(self):
		return self.thumbnail

	def get_author(self):
		return self.author


	@classmethod
	async def create_source(cls, ctx, search: str, * , loop, download=False, quiet = False):
		loop = loop or asyncio.get_event_loop()

		to_run = partial(ytdl.extract_info, url=search, download=download)

		data = await loop.run_in_executor(None, to_run)

		if 'entries' in data:
			data = data['entries'][0]

		if not quiet:
			await ctx.send(f'```ini\n[Added {data["title"]} to the Queue]\n```', delete_after=15)

		if download:
			source = ytdl.prepare_filename(data)
		else:
			return {'webpage_url': data['webpage_url'], 'requester': ctx.author, 'title': data['title']}

		return cls(discord.FFmpegPCMAudio(source), data=data, requester=ctx.author)

	@classmethod
	async def regather_stream(cls, data, *, loop):
		loop = loop or asyncio.get_event_loop()
		requester = data['requester']

		to_run = partial(ytdl.extract_info, url=data['webpage_url'], download=False)
		data = await loop.run_in_executor(None, to_run)

		return cls(discord.FFmpegPCMAudio(data['url']), data=data, requester=requester)
	


def get_author_(url):
	if not url:
		return None

	yt = pytube.YouTube(url)
	yt_avatar_url = get_channel_avatar_url_(yt.channel_id)

	if not yt_avatar_url:
		return None

	author = {
		'name': yt.author,
		'channel_url': yt.channel_url,
		'icon_url': yt_avatar_url
	}

	return author

def get_channel_avatar_url_(channel_id):
	url = f"https://www.googleapis.com/youtube/v3/channels?part=snippet&id={channel_id}&fields=items%2Fsnippet%2Fthumbnails&key={config.YOUTUBE_API_KEY}"
	response = requests.get(url)
	if response.status_code != 200:
		return
	try:
		yt_avatar_url = json.loads(response.text)['items'][0]['snippet']['thumbnails']['default']['url']
		return yt_avatar_url
	except:
		return

