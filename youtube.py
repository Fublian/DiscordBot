import discord
import ffmpeg
from discord.ext import commands
from youtube_search import YoutubeSearch
import yt_dlp
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
  async def play(self, ctx, *, args = None):
    print(args)
    bot_channel = discord.utils.get(self.client.get_all_channels(),name = 'fubots-palace')
    if ctx.voice_client is None:
      await self.join(ctx)
    if ctx.voice_client is not None: 
      url = fix_url(args)
      if url is not None:
        await print_playing(bot_channel, url)

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
      bot_channel = discord.utils.get(self.client.get_all_channels(),name = 'fubots-palace')
      if ctx.voice_client.is_playing():
        ctx.voice_client.pause()
        await bot_channel.send('Song Paused!')
      else:
        await bot_channel.send('Nothing to pause...')
    except:
      print("No active voice_client found")




  @commands.command()
  async def resume(self, ctx):
    try:
      bot_channel = discord.utils.get(self.client.get_all_channels(),name = 'fubots-palace')
      if ctx.voice_client.is_paused():
        ctx.voice_client.resume()
        await bot_channel.send('Song Resumed!')
      else:
        await bot_channel.send('Nothing to resume...')
    except:
      print("No active voice_client found")




  @commands.command()
  async def stop(self, ctx):
    try:
      bot_channel = discord.utils.get(self.client.get_all_channels(),name = 'fubots-palace')
      ctx.voice_client.stop()
    except:
      print("No active voice_client found")


async def print_playing(channel, url):
  #try:
  yt = pytube.YouTube(url)

  yt_embed = discord.Embed(title= yt.title, url=url, color=0x18191A)
  yt_embed.set_thumbnail(url=yt.thumbnail_url)
  
  channel_thumbnail = yt.vid_info['endscreen']['endscreenRenderer']['elements'][0]['endscreenElementRenderer']['image']['thumbnails'][0]['url']
  yt_embed.set_author(name=yt.author, url=yt.channel_url, icon_url=channel_thumbnail)
  yt_embed.set_footer(text=f'{yt.views:,} views')

  await channel.send("Now playing: ", embed = yt_embed)

     

def setup(client):
    client.add_cog(youtube(client))


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
