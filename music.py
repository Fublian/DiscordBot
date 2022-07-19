
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
import lyrics_helper as lh

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
				return await ctx.send('This command can no be used in Private Messages.')
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
				raise VoiceConnectionError(f'Connecting to channel: <{channel}> timed out.')

		await ctx.send(f'Connected to: **{channel}**', delete_after=20)
	


	@commands.command(name='play')
	async def play_(self, ctx, *, search: str):

		url_obj = ph.evaluate_search(search)

		if url_obj['domain'] == 'www.youtube.com':
			print('youtube')
		#elif url_obj['domain'] == 'open.spotify.com':
		#	print('spotify')
		else:
			await ctx.send(f'fubot does not support the source **{url_obj["domain"]}**', delete_after=20) 
			return


		await ctx.trigger_typing()

		vc = ctx.voice_client

		if not vc:
			await ctx.invoke(self.connect_)
			is_playing = False
		else:
			is_playing = vc.is_playing()

		player = self.get_player(ctx)
		try:
			source = await YTSource.create_source(ctx, search, loop = self.client.loop, download=False)
			await player.queue.put(source)
		except Exception:
			await ctx.send(f'fubot was not able to find any video matching **{search}**', delete_after=20) 
			return
		
		if url_obj['playlist']:
			await ctx.send(f'```ini\n[fetching playlist data]\n```', delete_after=5)
			playlist = ph.get_yt_playlist(url_obj['playlist_url'])

			length = len(playlist)
			sources = await ph.create_sources(ctx, player, playlist[:5], loop = self.client.loop, download=False)
			for s in sources[1:]:
				await player.queue.put(s)

			# Generate embeded with the fist 5 songs added in the playlist
			embed = ph.generate_yt_playlist_ebmeded(sources, length, search, is_playing)
			if embed:
				await ctx.send(embed=embed)

				if len(playlist) > 5:
					# Add the rest quietly after
					sources = await ph.create_sources(ctx, player, playlist[5:], loop = self.client.loop, download=False)
					for s in sources:
						await player.queue.put(s)
				await ctx.send(f'```ini\n[Completed adding playlist to the Queue]\n```', delete_after=10)
			else:
				await ctx.send(f'```ini\n[Could not retrieve play list information]\n```', delete_after=10)



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



	@commands.command(name='play-now', aliases=['playnow'])
	async def play_now_(self, ctx, *, search: str):
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
		await self.skip_(ctx, quiet=True)

		for s in history:
			await player.queue.put(s)

		
		if url_obj['playlist']:
			await ctx.send(f'fubot does not support playlist for this action.', delete_after=20) 



	@commands.command(name='pause')
	async def pause_(self, ctx):
		vc = ctx.voice_client

		if not vc or not vc.is_playing():
			return await ctx.send('I am not currently playing anything!', delete_after=20)
		elif vc.is_paused():
			return

		player = self.get_player(ctx)
		if not player.current:
			return await ctx.send('I am not currently playing anything!', delete_after=20)


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
			return await ctx.send('I am not currently playing anything!', delete_after=20)

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
	async def skip_(self, ctx, quiet=False):
		vc = ctx.voice_client

		if not vc or not vc.is_connected():
			if (quiet):
				return
			return await ctx.send('I am not currently playing anything!', delete_after=20)

		if vc.is_paused():
			pass
		elif not vc.is_playing():
			return

		vc.stop()
		if not quiet:
			await ctx.send(f'**`{ctx.author}`**: Skipped the song!', delete_after=20)
	


	@commands.command(name='queue', aliases=['q','playlist'])
	async def queue_info_(self, ctx):
		vc = ctx.voice_client

		if not vc or not vc.is_connected():
			return await ctx.send('I am not currently connected to voice!', delete_after=20)

		player = self.get_player(ctx)
		if player.queue.empty():
			return await ctx.send('There are currently no more queued songs.', delete_after=20)

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
			await ctx.send(f'The Queue is alredy Empty!', delete_after=20)



	@commands.command(name='now_playing', aliases=['np', 'current', 'playing', 'now-play','now'])
	async def now_playing_(self, ctx):
		vc = ctx.voice_client

		if not vc or not vc.is_connected():
			return await ctx.send('I am not currently connected to voice!', delete_after=20)

		player = self.get_player(ctx)
		if not player.current:
			return await ctx.send('I am not currently playing anything!', delete_after=20)

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



	@commands.command(name='upcoming', aliases=['up-next'])
	async def upcoming(self, ctx):
		vc = ctx.voice_client

		if not vc or not vc.is_connected():
			return await ctx.send('I am not currently connected to voice!', delete_after=20)

		player = self.get_player(ctx)
		if not player.current:
			return await ctx.send('The Queue is empty, there are no upcoming song.', delete_after=20)

		
		## Attempts to grab the next song in queue
		try :
			upcoming = list(itertools.islice(player.queue._queue, 0, 1))[0]
			description = f'[**`{upcoming["title"]}`**]({upcoming["webpage_url"]})'
			embed = discord.Embed(title=f'Upcoming Track', description=description)

			await ctx.send(embed=embed)
		except IndexError:
			return await ctx.send('The Queue is empty, there are no upcoming song.', delete_after=20)
		



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



	@commands.command(name='lyrics', aliases=['lyric','text'])
	async def lyrics_(self, ctx):
		vc = ctx.voice_client

		if not vc or not vc.is_connected():
			return await ctx.send('I am not currently playing anything!', delete_after=20)

		player = self.get_player(ctx)

		if not player.current:
			return await ctx.send('I am not currently playing anything!', delete_after=20)

		resend = None

		try:
			if player.lyrics:
				# Check if we send Lyrics Commands twice for the same song
				# Then we can just resend the message rather then doing another API Call

				current_url = player.lyrics.embeds[0].to_dict()['url']
				if current_url == player.current['web_url']:
					resend = player.lyrics.embeds[0]
				await player.lyrics.delete()
		except discord.HTTPException:
			pass		

		if resend:
			player.lyrics = await ctx.send(embed=resend)
		else:
			msg = await ctx.send(f'```ini\n[Looking for Lyrics...]\n```', delete_after=10)
			lyrics = lh.get_lyrics(player.current['web_url'])


			if lyrics:
				await msg.edit(content=f'```ini\n[Found Lyrics, preparing message!]\n```', delete_after=5)
				embed = lh.generate_lyrics_ebmeded(lyrics, player.current['thumbnail'], 
					player.current['author'], player.current['web_url'])
				player.lyrics = await ctx.send(embed=embed)
			else:
				await ctx.send("Sorry, I Could not find the lyrics for the current track", delete_after=20)


	@commands.command(name='kanye', aliases=['quote', 'west', 'tips'])
	async def kanye_(self, ctx):
		url = 'https://api.kanye.rest'
		icon_url = 'https://www.pngkit.com/png/full/15-159514_music-stars-kanye-west-face-png.png'
		shop_url = 'https://shop.kanyewest.com/products/donda-album'
		try:
			response = requests.get(url)
			quote = json.loads(response.text)['quote']
		except:
			quote = "Kanye is resting..."

		kanye_embed = discord.Embed(title="\u200b", color=0x000000, description=f'{quote}')
		kanye_embed.set_author(name="Kanye West", url='https://twitter.com/kanyewest', icon_url=icon_url)
		kanye_embed.add_field(name='\u200b',value =f'[DONDA!]({shop_url})')
		await ctx.send(embed=kanye_embed)


def setup(client):
	client.add_cog(Music(client))

