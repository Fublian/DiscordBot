import discord
import os
from discord.ext import commands
import youtube
import ffmpeg

TOKEN = 'OTUzOTc5MzMxMzU1NDg4Mjg2.YjMcfA.WP7Z7ewwCqc55UHy7Uig3WgZBcI'


cogs = [youtube]

client = commands.Bot(command_prefix='!', intents = discord.Intents.all())

for i in range(len(cogs)):
  cogs[i].setup(client)

client.run(TOKEN)