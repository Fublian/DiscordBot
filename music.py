
import requests
import ffmpeg

from youtube_search import YoutubeSearch
import yt_dlp
import pytube
import validators
from requests import get

import config
import json

import discord
from discord.ext import commands
import asyncio
import itertools
import sys
import traceback
from functools import partial

from  musicplayer import MusicPlayer
from yt_source import YTSource
import playlist_helper as ph

class VoiceConnectionError(commands.CommandError):
	"""Custom Exception Class"""

class InvalidVoiceChannel(Exception):
	pass
	"""Custom Exception Class"""


class Music(commands.Cog):

	__slots__ = ('client', 'players')

	def __init__(self, client):
		self.client = client
		self._playing_msg_id = None
		self.players = {}

	async def cleanup(self, guild):
		try:
			await guild.voice_client.disconnect()
		except AttributeError:
			pass

		try:
			del self.players[guild.id]
		except KeyError:
			pass


	async def __local_check(self, ctx):
		if not ctx.guild:
			raise commands.NoPrivateMessage
		return True


	async def __error(self, ctx, error):
		if isinstance(error, commands.NoPrivateMessage):
			try:
				return await ctx.send('Test This command can no be used in Private Messages.')
			except discord.HTTPException:
				pass
		elif isinstance(error, InvalidVoiceChannel):
			await ctx.send('Error connecting to Voice Channel. '
				'Please make sure you are in a valid channel or provide me with one')

		print('Ignoring exception in command {}:'.format(ctx.command), file=sys.stderr)
		traceback.print_exception(type(error), error, error.__traceback__, file=sys.stderr)


	def get_player(self, ctx):
		try:
			player = self.players[ctx.guild.id]
		except KeyError:
			player = MusicPlayer(ctx)
			self.players[ctx.guild.id] = player
		return player



	@commands.command(name='connect', aliases=['join'])
	async def connect_(self, ctx, *, channel: discord.VoiceChannel=None):
		if not channel:
			try:
				channel = ctx.author.voice.channel
			except AttributeError:
				#raise InvalidVoiceChannel('No channel to join...')
				await ctx.send('Error connecting to Voice Channel. '
				'Please make sure you are in a valid channel or provide me with one')
				return

		vc = ctx.voice_client

		if vc:
			if vc.channel.id == channel.id:
				return
			try:
				await vc.move_to(channel)
			except asyncio.TimeoutError:
				raise VoiceConnectionError(f'Moving to channel: <{channel}> timed out.')

		else:
			try:
				await channel.connect()
			except asyncio.TimeoutError:
				raise VoiceConnectionError(f'Moving to channel: <{channel}> timed out.')

		await ctx.send(f'Connected to: **{channel}**', delete_after=20)
	

	@commands.command(name='play')
	async def play_(self, ctx, *, search: str):

		url_obj = ph.evaluate_search(search)
		

		if url_obj['domain'] != 'www.youtube.com':
			await ctx.send(f'fubot does not support the source **{url_obj["domain"]}**', delete_after=20) 
			return


		await ctx.trigger_typing()

		vc = ctx.voice_client

		if not vc:
			await ctx.invoke(self.connect_)

		player = self.get_player(ctx)

		source = await YTSource.create_source(ctx, search, loop = self.client.loop, download=False)

		await player.queue.put(source)

		
		if url_obj['playlist']:
			await ctx.send(f'```ini\n[fetching playlist data]\n```', delete_after=5)
			playlist = ph.get_yt_playlist(url_obj['playlist_url'])

			length = len(playlist)
			sources = await ph.create_sources(ctx, player, playlist[:5], loop = self.client.loop, download=False)
			for s in sources[1:]:
				await player.queue.put(s)

			# Generate embeded with the fist 5 songs added in the playlist
			embed = ph.generate_yt_playlist_ebmeded(sources, length, search)

			await ctx.send(embed=embed)

			if len(playlist) > 5:
				# Add the rest quietly after
				sources = await ph.create_sources(ctx, player, playlist[5:], loop = self.client.loop, download=False)
				for s in sources:
					await player.queue.put(s)
			await ctx.send(f'```ini\n[Completed adding playlist to the Queue]\n```', delete_after=10)

	@commands.command(name='play-next', aliases=['queue-next','put-next', 'top'])
	async def play_next_(self, ctx, *, search: str):

		url_obj = ph.evaluate_search(search)
		

		if url_obj['domain'] != 'www.youtube.com':
			await ctx.send(f'fubot does not support the source **{url_obj["domain"]}**', delete_after=20) 
			return


		await ctx.trigger_typing()

		vc = ctx.voice_client

		if not vc:
			await ctx.invoke(self.connect_)

		player = self.get_player(ctx)
		source = await YTSource.create_source(ctx, search, loop = self.client.loop, download=False, quiet = True)
		history = player.empty_queue()

		await player.queue.put(source)

		await ctx.send(f'```ini\n[Added {source["title"]} first in the Queue]\n```', delete_after=15)

		for s in history:
			await player.queue.put(s)

		
		if url_obj['playlist']:
			await ctx.send(f'fubot does not support playlist for this action.', delete_after=20) 



	@commands.command(name='empty', aliases=['empty-queue', 'clear', 'clear-queue'])
	async def empty_queue_(self, ctx):
		vc = ctx.voice_client

		if not vc or not vc.is_connected():
			return await ctx.send('I am not currently playing anything!', delete_after=20)

		player = self.get_player(ctx)
		history = player.empty_queue()
		if len(history):
			await ctx.send(f'**`{ctx.author}`**: Cleared the Queue! ({len(history)} tracks removed)')
		else:
			await ctx.send(f'The Queue is alredy Empty!')



	@commands.command(name='pause')
	async def pause_(self, ctx):
		vc = ctx.voice_client

		if not vc or not vc.is_playing():
			return await ctx.send('I am not currently playing anything!', delete_after=20)
		elif vc.is_paused():
			return

		player = self.get_player(ctx)
		if not player.current:
			return await ctx.send('I am not currently playing anything!')


		try:
			## Try to remove currently playing message
			await player.now_playing.delete()
		except discord.HTTPException:
			pass

		vc.pause()
		await ctx.send(f'**`{ctx.author}`**: paused the song!')

		embed = player.generate_embed(player.current, "Song Paused")
		player.now_playing = await ctx.send(embed=embed)



	@commands.command(name='resume')
	async def resume_(self, ctx):
		vc = ctx.voice_client

		if not vc or not vc.is_connected():
			return await ctx.send('I am not currently playing anything!', delete_after=20)
		elif not vc.is_paused():
			return


		player = self.get_player(ctx)
		if not player.current:
			return await ctx.send('I am not currently playing anything!')

		try:
			## Try to remove currently playing message
			await player.now_playing.delete()
		except discord.HTTPException:
			pass

		vc.resume()
		await ctx.send(f'**`{ctx.author}`**: resumed the song!')

		embed = player.generate_embed(player.current, "Song Resumed")
		player.now_playing = await ctx.send(embed=embed)


	@commands.command(name='skip', aliases=['next'])
	async def skip_(self, ctx):
		vc = ctx.voice_client

		if not vc or not vc.is_connected():
			return await ctx.send('I am not currently playing anything!', delete_after=20)

		if vc.is_paused():
			pass
		elif not vc.is_playing():
			return

		vc.stop()
		await ctx.send(f'**`{ctx.author}`**: Skipped the song!')

	@commands.command(name='queue', aliases=['q','playlist'])
	async def queue_info_(self, ctx):
		vc = ctx.voice_client

		if not vc or not vc.is_connected():
			return await ctx.send('I am not currently connected to voice!', delete_after=20)

		player = self.get_player(ctx)
		if player.queue.empty():
			return await ctx.send('There are currently no more queued songs.')

		## Grabs the first 5 Queued Songs
		upcoming = list(itertools.islice(player.queue._queue, 0, 5))
		
		longest = len(max([song['title'] for song in upcoming], key=len))
		length = len(player.queue._queue)

		#fmt_queue = '\n'.join(f'**`{song["title"]}`**' for song in upcoming)
		fmt_queue = '\n'.join(f'**` {i+1}. {song["title"]+(longest-len(song["title"]))*" "}   `**' for i, song in enumerate(upcoming))
		if length > 5:
			fmt_queue += f'\n**` \u22EE `**\n'

		embed = discord.Embed(title=f'Upcoming Tracks', description=fmt_queue)
		embed.set_author(name=ctx.guild.name, url="", icon_url=ctx.guild.icon_url)
		embed.set_footer(text=f'{len(upcoming)} of {length} in total')

		await ctx.send(embed=embed)


	@commands.command(name='now_playing', aliases=['np', 'current', 'playing', 'now-play','now'])
	async def now_playing_(self, ctx):
		vc = ctx.voice_client

		if not vc or not vc.is_connected():
			return await ctx.send('I am not currently connected to voice!', delete_after=20)

		player = self.get_player(ctx)
		if not player.current:
			return await ctx.send('I am not currently playing anything!')

		try:
			## Try to remove currently playing message
			await player.now_playing.delete()
		except discord.HTTPException:
			pass

		status = "Now Playing..."
		if vc.is_paused():
			status = "Song Paused"
		embed = player.generate_embed(player.current, status)

		player.now_playing = await ctx.send(embed=embed)



	@commands.command(name='volume', aliases=['vol'])
	async def change_volume_(self, ctx, *, vol: float):
		vc = ctx.voice_client

		if not vc or not vc.is_connected():
			return await ctx.send('I am not currently connected to voice!', delete_after=20)

		if not 0 < vol < 101:
			return await ctx.send('Please enter a value between 1 and 100')

		player = self.get_player(ctx)

		if vc.source:
			vc.source.volume = vol / 100
			await ctx.send(f'**`{ctx.author}`**: Set the volume to **{vol}%**')


	@commands.command(name='stop', aliases=['disc', 'disconnect', 'end', 'leave'])
	async def stop_(self, ctx):
		vc = ctx.voice_client

		if not vc or not vc.is_connected():
			return await ctx.send('I am not currently playing anything!', delete_after=20)

		await self.cleanup(ctx.guild)

def setup(client):
	client.add_cog(Music(client))


	'''

	@commands.command()
	async def disc(self, ctx):
		bot_channel = discord.utils.get(self.client.get_all_channels(), name=config.BOT_CHANNEL_NAME)
		if ctx.voice_client is None:
			await bot_channel.send(f"{self.client.user.name} is not connected to any voice channel...")
		else:
			await ctx.voice_client.disconnect()




	@commands.Cog.listener()
	async def on_voice_state_update(self, member, before, after):
	# Make sure we triggered the event
	if not member.id == self.client.user.id:
		return

	# Check if it was a Join event
	elif before.channel is None:
		voice = after.channel.guild.voice_client
		time = 0
		while True:
		await asyncio.sleep(1)
		time = time + 1
		#if voice.is_playing() and not voice.is_paused():
		if voice.is_playing() or voice.is_paused():
			time = 0

		current_msg = self.get_playing_msg_id()

		if not voice.is_playing() and not voice.is_paused() and current_msg and time > 4:
			try:
			self.set_playing_msg_id(None)
			new_embed = edit_embed(current_msg.embeds[0], description="Finished")
			await current_msg.edit(embed=new_embed)

			except:
			print("coudn't update message")

		if time == config.INACTIVITY_TIMER:
			await voice.disconnect()
		if not voice.is_connected():
			break




	

	


	def set_playing_msg_id(self, msg_id):
		self._playing_msg_id = msg_id


	def get_playing_msg_id(self):
		return self._playing_msg_id


	 @commands.command()
	 async def join(self, ctx):
	bot_channel = discord.utils.get(self.client.get_all_channels(), name=config.BOT_CHANNEL_NAME)
	if ctx.author.voice is None:
		await bot_channel.send("You are not connected to any voice channel...")
	else:
		voice_channel = ctx.author.voice.channel
		if ctx.voice_client is None:
		await voice_channel.connect()
		else:
		await ctx.voice_client.move_to(voice_channel)



	@commands.command(name='play', aliases=['spela'])
	async def play_(self, ctx, *, args = None):
	bot_channel = discord.utils.get(self.client.get_all_channels(), name=config.BOT_CHANNEL_NAME)
	if ctx.voice_client is None:
		await self.join(ctx)
	if ctx.voice_client is not None:
		domain = find_domain(args)
		url = fix_url(args, domain)
		if url is not None:

		embed_msg = create_embed(url, domain)
		msg_id = await bot_channel.send(embed = embed_msg)

		self.set_playing_msg_id(msg_id)

		ctx.voice_client.stop()
		FFMPEG_OPTIONS = {'before_options': '-reconnect 1 -reconnect_streamed 1 -reconnect_delay_max 5', 'options': '-vn'}
		YDL_OPTIONS = {'format': 'bestaudio/best'}

		with yt_dlp.YoutubeDL(YDL_OPTIONS) as ydl:
			info = ydl.extract_info(url,download=False)
			url2 = info['url']
			source = await discord.FFmpegOpusAudio.from_probe(url2, **FFMPEG_OPTIONS)
			ctx.voice_client.play(source)
		
		else:
		await bot_channel.send("Unable to find video...")






	@commands.command()
	async def pause(self, ctx):
		try:
			bot_channel = discord.utils.get(self.client.get_all_channels(), name=config.BOT_CHANNEL_NAME)
			if ctx.voice_client.is_playing():

				current_msg = self.get_playing_msg_id()
				new_embed = edit_embed(current_msg.embeds[0], description="Paused")
				await current_msg.edit(embed=new_embed)

				ctx.voice_client.pause()
			else:
				print('Nothing to pause...')
		except:
			print("No active voice_client found")


	


	@commands.command()
	async def resume(self, ctx):
		try:
			bot_channel = discord.utils.get(self.client.get_all_channels(), name=config.BOT_CHANNEL_NAME)
			if ctx.voice_client.is_paused():

				current_msg = self.get_playing_msg_id()
				new_embed = edit_embed(current_msg.embeds[0], description="Now playing...")
				await current_msg.edit(embed=new_embed)

				ctx.voice_client.resume()
			else:
				print('Nothing to resume...')
		except:
			print("No active voice_client found")


def edit_embed(embed, **kwargs):

	if "title" in kwargs: 
		title = kwargs.get("title")
	else:
		title = embed.title

	if "url" in kwargs: 
		url = kwargs.get("url")
	else:
		url = embed.url

	if "color" in kwargs: 
		color = kwargs.get("color")
	else:
		color = embed.color

	if "description" in kwargs: 
		description = kwargs.get("description")
	else:
		description = embed.description

	new_embed = discord.Embed(title=title, url=url, color=color, description=description)
	new_embed.set_thumbnail(url=embed.thumbnail.url)
	new_embed.set_author(name=embed.author.name, url=embed.author.url, icon_url=embed.author.icon_url)
	new_embed.set_footer(text=embed.footer.text)
	return new_embed


def find_domain(url):
	domains = ['youtube']
	domain = 'youtube' ## Default Domain (Search will be done on youtube)
	for dom in domains:
		if dom in url:
			domain = dom
	return domain

def fix_url(url, domain = 'youtube'):
	if url:
		if validators.url(url) and domain in url:
			return url
		if url.find("www.") > -1 and domain in url:
			new_url = "https://" + url[url.find("www."):]
			if validators.url(new_url):
				return new_url
		new_url = youtube_search(url)
		if new_url:
			return 'https://www.youtube.com' + new_url
	return None


def youtube_search(phrase):
	results = YoutubeSearch(phrase, max_results=1).to_dict()
	if len(results) > 0:
		return results[0]['url_suffix']


'''