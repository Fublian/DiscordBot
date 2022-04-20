import discord
import os
from discord.ext import commands
import music
import config
import ffmpeg



def main():

	cogs = [music]
	client = commands.Bot(command_prefix='!', intents = discord.Intents.all())

	for i in range(len(cogs)):
		cogs[i].setup(client)


	print('Fubot is now live...')
	client.run(config.TOKEN)



if __name__ == "__main__":
	main()


	'''

To do:
Play Now (Skipp + add first)


Add Dedicated Channel for the BOT.
Add Lyrics Command
Standard Message Dictionary

Add Spotify Support

'''