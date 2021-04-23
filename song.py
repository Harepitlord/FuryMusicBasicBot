# This class is to create a stream for the required song or download it

# This youtube_dl is used to search the songs and download it from the youtube platform
import youtube_dl

# This Embed class is used to create a custom embed message for the specific class
import discord

# This is used to use the bot functions and commands
from discord.ext import commands

# This is used to implement the asynchronous operations like building a dynamic queue
import asyncio

# This is used to create a coroutine in the async event loop
from functools import partial

# This is used to create a asynchronous timer
from async_timeout import timeout

YTDL_OPTS = {
    "default_search": "auto",
    "format": "bestaudio/best",
    "quiet": True,
    "noplaylist": True,
    "restrictfilenames": True,
    "no_warnings": True,
    "outtmpl": 'downloads/%(extractor)s-%(id)s-%(title)s.%(ext)s',
    'nocheckcertificate': True,
    'ignoreerrors': False,
    'logtostderr': False,
    'source_address': '0.0.0.0'  # ipv6 addresses cause issues sometimes
}

ffmpegopts = {
    'before_options': '-nostdin -reconnect 1 -reconnect_streamed 1 -reconnect_delay_max 5',
    'options': '-vn'
}

ytdl = youtube_dl.YoutubeDL(YTDL_OPTS)


class YTDLSource(discord.PCMVolumeTransformer):

    def __init__(self, source, *, data, requester):
        super().__init__(source)

        self.requester = requester

        self.title = data.get('title')
        self.web_url = data.get('webpage_url')

    def __getitem__(self, item: str):
        # This funtion allows us to access attributes similar to a  dictionary accessing
        return self.__getattribute__(item)

    @classmethod
    async def create_source(cls, ctx, search: str, *, loop, download=False):
        loop = loop or asyncio.get_event_loop()

        to_run = partial(ytdl.extract_info, url=search, download=download)
        data = await loop.run_in_executor(None, to_run)

        if 'entries' in data:
            data = data['entries'][0]

        if download:
            source = ytdl.prepare_filename(data)
        else:
            return {'webpage_url': data['webpage_url'], 'requester': ctx.author, 'title': data['title']}

        return cls(discord.FFmpegPCMAudio(source, **ffmpegopts), data=data, requester=ctx.author)

    @classmethod
    async def regather_stream(cls, data, *, loop):
        # It is used to prepare a stream, instead of downloading as the youtube links will expire.
        loop = loop or asyncio.get_event_loop()
        requester = data['requester']

        to_run = partial(ytdl.extract_info, url=data['webpage_url'], download=False)
        data = await loop.run_in_executor(None, to_run)

        return cls(discord.FFmpegPCMAudio(source=data['url'], **ffmpegopts), data=data, requester=requester)
