import discord
import asyncio
from  yt_source import YTSource
from async_timeout import timeout

class MusicPlayer():

	__slots__ = ('bot', '_guild', '_channel', '_cog', 'queue', 'next', 'now_playing', 'lyrics','current', 'volume')

	def __init__(self, ctx):
	    self.bot = ctx.bot
	    self._guild = ctx.guild
	    self._channel = ctx.channel
	    self._cog = ctx.cog

	    self.queue = asyncio.Queue()
	    self.next = asyncio.Event()

	    self.now_playing = None
	    self.lyrics = None

	    self.current = None
	    self.volume = .5

	    ctx.bot.loop.create_task(self.player_loop())

	async def player_loop(self):
		await self.bot.wait_until_ready()

		## While websocket is open
		while not self.bot.is_closed():
			self.next.clear()

			try:
				async with timeout(10):
					source = await self.queue.get()
			except asyncio.TimeoutError:
				return self.destroy(self._guild)


			if not isinstance(source, YTSource):
				try:
					source = await YTSource.regather_stream(source, loop=self.bot.loop)
				except Exception as e:
					await self._channel.send(f'There was an error processing your song.\n'
						f'```css\n[{e}]\n```')

					continue

			source.volume = self.volume
			self.current = source
			

			## call_soon_threadsafe is a theard-safe variant of call_soon
			## Add check if _guild.voice_client is not NONE ???
			if not self._guild.voice_client:
				return self.destroy(self._guild)

			self._guild.voice_client.play(source, after=lambda x: self.bot.loop.call_soon_threadsafe(self.next.set))
			
			embed = self.generate_embed(source, "Now Playing...")
			if embed:
				self.now_playing = await self._channel.send(embed=embed)


			'''
			else:
				self.now_playing = await self._channel.send(f'**Now Playing:** `{source.title}` requested by '
					f'`{source.requester}`')

			## Send message to correct channel
			'''

			await self.next.wait()

			source.cleanup()
			self.current = None

			try:
				await self.now_playing.delete()
			except discord.HTTPException:
				pass
	
	def empty_queue(self):
		history = []
		while self.queue.qsize() > 0:
			try:
				history.append(self.queue.get_nowait())
			except:
				pass
		return history

	def generate_embed(self, source, status):
		if not source:
			return
		yt_embed = discord.Embed(title=source.title, url=source.web_url, color=0xCC0000, description=f'Requested by `{source.requester}`')
		yt_embed.set_thumbnail(url=source.thumbnail['url'])
		yt_embed.add_field(name='Status:', value=status, inline=True)
		if source.author:
			yt_embed.set_author(name=source.author['name'], url=source.author['channel_url'], icon_url=source.author['icon_url'])

		yt_embed.set_footer(text=f'{source.views:,} views')
		return yt_embed

	def destroy(self, guild):
		return self.bot.loop.create_task(self._cog.cleanup(guild))
