import discord
import ffmpeg
from discord.ext import commands
from youtube_search import YoutubeSearch
import youtube_dl
import pytube
import validators
from requests import get


class youtube(commands.Cog):

  def __init__(self, client):
    self.client = client
    

  @commands.command()
  async def join(self, ctx):
    bot_channel = discord.utils.get(self.client.get_all_channels(),name = 'fubots-palace')
    if ctx.author.voice is None:
      await bot_channel.send("You are not connected to any voice channel...")
    else:
      voice_channel = ctx.author.voice.channel
      if ctx.voice_client is None:
        await voice_channel.connect()
      else:
        await ctx.voice_client.move_to(voice_channel)

  @commands.command()
  async def disc(self, ctx):
    bot_channel = discord.utils.get(self.client.get_all_channels(),name = 'fubots-palace')
    if ctx.voice_client is None:
      await bot_channel.send("{} is not connected to any voice channel...".format(self.client.user.name))
    else:
      await ctx.voice_client.disconnect()


  @commands.command()
  async def play(self, ctx, url = None):
    bot_channel = discord.utils.get(self.client.get_all_channels(),name = 'fubots-palace')
    if ctx.voice_client is None:
      await self.join(ctx)
    if ctx.voice_client is not None: 
      url = fix_url(url)
      if url is not None:
        ctx.voice_client.stop()
        FFMPEG_OPTIONS = {'before_options': '-reconnect 1 -reconnect_streamed 1 -reconnect_delay_max 5', 'options': '-vn'}
        YDL_OPTIONS = {'format':'bestaudio'}
        vc = ctx.voice_client

        with youtube_dl.YoutubeDL(YDL_OPTIONS) as ydl:
          info = ydl.extract_info(url,download=False)
          url2 = info['formats'][0]['url']
          source = await discord.FFmpegOpusAudio.from_probe(url2, **FFMPEG_OPTIONS)
          vc.play(source)
      else:
        await bot_channel.send("Unable to find video...")

  @commands.command()
  async def pause(self, ctx):
    bot_channel = discord.utils.get(self.client.get_all_channels(),name = 'fubots-palace')
    await ctx.voice_client.pause()
    await bot_channel.send('Song Paused!')

  @commands.command()
  async def resume(self, ctx):
    bot_channel = discord.utils.get(self.client.get_all_channels(),name = 'fubots-palace')
    await ctx.voice_client.pause()
    await bot_channel.send('Song Resumed!')
      
def setup(client):
    client.add_cog(youtube(client))

def fix_url(url, domain = 'youtube'):
  if url:
    if validators.url(url):
      if (domain in url):
        return url
    if url.find("www.") > -1 and domain in url:
      new_url = "https://" + url[url.find("www."):]
      if validators.url(new_url):
        return new_url
    new_url = youtube_search(url)
    if (new_url):
      return 'https://www.youtube.com' + new_url
  return None

def youtube_search(phrase):
  results = YoutubeSearch(phrase, max_results=1).to_dict()
  if len(results) > 0:
    return results[0]['url_suffix']
