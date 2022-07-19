import discord
import traceback
import io
import os
from discord.ext import commands
import music
import config
import ffmpeg

filter_excs = (commands.CommandNotFound, commands.CheckFailure, commands.ChannelNotFound)
def main():

	cogs = [music]
	client = commands.Bot(command_prefix='!', intents=discord.Intents.all(), case_insensitive=True)

	for i in range(len(cogs)):
		cogs[i].setup(client)

	@client.event
	async def on_error(event, *args, **kwargs):
		"""Error handler for all events."""
		s = traceback.format_exc()
		content = f'Ignoring exception in {event}\n{s}'
		print(content)

	@client.event
	async def on_command_error(ctx: commands.Context, exc: Exception):
		if isinstance(exc, filter_excs):
			return
		if isinstance(exc, commands.MissingRequiredArgument):
			return await ctx.send('Missing url or search term...', delete_after=20)
		
		# Log the error and bug the owner.
		exc = getattr(exc, 'original', exc)
		#lines = ''.join(traceback.format_exception(exc.__class__, exc, exc.__traceback__))
		#lines = f'Ignoring exception in command {ctx.command}:\n{lines}'
		print(f'Ingorning Error: {exc.__class__}\nThrown Error: {exc}')

	print('Fubot is now live...')
	client.run(config.TOKEN)



if __name__ == "__main__":
	main()


	'''

To do:
	Standard Message Dictionary

	Add Spotify Support
	Add SoundCloud
	Add Youtube Music

'''
