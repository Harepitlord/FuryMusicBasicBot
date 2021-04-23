# This class is to create the bot commands and define the functional characteristics

# This import is use the system logger to log the error we have faced during the runtime
import sys

# This import help us to record the traceback produced by the error during the runtime
import traceback

# This exception class is imported to aid us in finding whether the song is playing or completed
from discord import HTTPException

# This import will be helpful in defining the commands of the bot
from discord.ext import commands

# This class imports the Music player from the musicplayer.py
from Music_player import MusicPlayer

# This import imports the youtube source class from song.py
from Song import YTDLSource

# This import brings in the discord library
import discord

# This import brings the additional asynchronous abilities to the program
import asyncio

# This import brings in the iteration tools
import itertools

# This import brings in the shuffle function from the random class
from random import shuffle

# This import brings in the request capabilities to the program
import requests

# This import brings in the file handling capabilities
import os


# Custom Exception classes for the bot
class VoiceConnectionError(commands.CommandError):
    """Custom Exception class for connection errors."""


class InvalidVoiceChannel(VoiceConnectionError):
    """Exception for cases of invalid Voice Channels."""


# Embed message for the connect function of the bot
notInChannel = discord.Embed(
    description='First join a voice channel before you use this command',
    colour=discord.Colour.blue()
)

notInSameChannel = discord.Embed(
    description='First join the same channel then use the bot commands',
    colour=discord.Colour.blue()
)

def customEmbed(description):
    return discord.Embed(
        description=description,
        colour=discord.Colour.blue()
    )


botNotInChannel = discord.Embed(
    description='I am not currently connected to voice!',
    colour=discord.Colour.blue()
)
botNotPlaying = discord.Embed(
    description='I am not currently playing anything!',
    colour=discord.Colour.blue()
)


# This class defines the structure of the bot with commands
class MusicBot(commands.Cog):
    # This class will be the structure of music bot
    __slots__ = ('bot', 'players','cmdPrefix')

    def __init__(self, bot,cmd):
        self.bot = bot
        self.players = {}
        self.cmdPrefix = cmd

    # This function is cleanup the music player once the bot leaves the voice channel
    async def cleanup(self, guild):
        try:
            await guild.voice_client.disconnect()

        except AttributeError:
            pass

        try:
            del self.players[guild.id]

        except KeyError:
            pass

    # Local error handling functions to record the error happened during runtime
    async def __local_check(self, ctx):
        # A local check which applies to all commands in this cog.
        if not ctx.guild:
            raise commands.NoPrivateMessage
        return True

    async def __error(self, ctx, error):
        # A local error handler for all errors arising from commands in this cog

        if isinstance(error, commands.NoPrivateMessage):
            try:
                return await ctx.send(embed=customEmbed('This command can not be used in Private Message.'))

            except HTTPException:
                pass

        elif isinstance(error, InvalidVoiceChannel):
            await ctx.send(embed=customEmbed(
                'Error connecting to Voice Channel.\n''Please make sure you are in a valid channel or provide me with '
                'one'))

        print(f'Ignoring exception in command {ctx.command}:', file=sys.stderr)
        traceback.print_exception(type(error), error, error.__traceback__, file=sys.stderr)
        return

    def get_player(self, ctx):
        # This function will retrieve the guild player or generate one for the specific guild
        try:
            player = self.players[ctx.guild.id]
        except KeyError:
            player = MusicPlayer(ctx)
            self.players[ctx.guild.id] = player

        return player

    def embedAddField(self,embed : discord.Embed,name:str,value:str,inline:bool=False):
        embed.add_field(name=name,value=value,inline=inline)

    # Bot commands
    @commands.command(name='connect', aliases=['join'], pass_context=True)
    async def connect(self, ctx, *, channel: discord.VoiceChannel = None):

        # This function will connect the bot to the voice client
        # The channel is an optional parameter
        # The optional parameter can be used when the bot needs to be moved to another voice channel

        if not channel:
            try:
                channel = ctx.author.voice.channel

            except AttributeError:
                await ctx.send(embed=notInChannel)
                return

        vc = ctx.voice_client

        if ctx.guild.voice_client == ctx.message.author.voice.channel:
            await ctx.send(embed=notInSameChannel)
            return

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

        await ctx.send(embed=customEmbed(f'Connected to: **{channel}**'))

    @commands.command(name='play', aliases=['sing'], pass_context=True)
    async def play(self, ctx, *,search: str):

        # Requests a song and add it to the queue
        # This command attempts to join a valid voice channel if the bot is not already in one.
        #  Uses YTDL to automatically search and retieve a song

        # search is a required parameter which will be used to search the song

        await ctx.trigger_typing()

        vc = ctx.voice_client

        if not vc:
            await ctx.invoke(self.connect)

        player = self.get_player(ctx)

        # Converting the multi word search request from tuple to a single string
        s = ''
        for _ in search:
            s += _ + ' '

        search = s

        # If download is False, sources will be a dict which will be used later to regather the stream.
        # If download is True, sources will be a discord.FFmpegPCMAudio with a VolumeTransformer.

        source = await YTDLSource.create_source(ctx, search, loop=self.bot.loop, download=False)
        if player.current:
            await ctx.send(
            embed=customEmbed(f"**`{ctx.author}: Added`** **[{source['title']}]({source['webpage_url']}) to the Queue.]**"))
        player.playlist.append(source['title'])
        await player.queue.put(source)

    @commands.command(name='pause', pass_context=True)
    async def pause(self, ctx):
        # This function will pause the song
        vc = ctx.voice_client

        if not vc or not vc.is_playing():
            return await ctx.send(embed=botNotPlaying, delete_after=20)
        elif vc.is_paused():
            return

        vc.pause()
        await ctx.send(embed=customEmbed(f'**`{ctx.author}`**: Paused the song!'))

    @commands.command(name='resume', pass_context=True)
    async def resume(self, ctx):
        # This function will resume the song playback
        vc = ctx.voice_client

        if not vc or not vc.is_connected():
            return await ctx.send(embed=botNotPlaying, delete_after=20)

        elif not vc.is_paused():
            return

        vc.resume()
        await ctx.send(embed=customEmbed(f'**`{ctx.author}`**: Resumed the song!'))

    @commands.command(name='skip', aliases=['next'], pass_context=True)
    async def skip(self, ctx):

        # Skip the song
        vc = ctx.voice_client

        if not vc or not vc.is_connected():
            return await ctx.send(embed=botNotPlaying, delete_after=20)

        if vc.is_paused():
            pass

        elif not vc.is_playing():
            return

        self.get_player(ctx).playlist.remove(vc.source['title'])
        vc.stop()
        await ctx.send(embed=customEmbed(f'**`{ctx.author}`**: Skipped the song!'))
        return


    @commands.command(name='queue', aliases=['q'], pass_context=True)
    async def queue_info(self, ctx):
        # Retrieve a basic queue of upcoming songs.
        vc = ctx.voice_client

        if not vc or not vc.is_connected():
            return await ctx.send(embed=botNotInChannel, delete_after=20)

        player = self.get_player(ctx)
        if player.queue.empty():
            return await ctx.send(embed=customEmbed(description=f'There are currently no more queued songs'))

        # Grab up to 10 entries from the queue
        upcoming = list(itertools.islice(player.queue._queue, 0, 15))

        queueList = discord.Embed(
            title=f'Upcoming - Total {player.queue.qsize()}',
            colour=discord.Colour.blue()
        )
        for _,i in zip(upcoming,range(1,len(upcoming))):
            queueList.add_field(name=i,value=f"**[{_['title']}]**({_['webpage_url']})",inline=True)
        queueList.set_author(name=ctx.message.author,icon_url=ctx.message.author.avatar_url)
        queueList.set_footer(text=f'If you want to see the complete queue use {self.cmdPrefix}queueall')
        await ctx.send(embed=queueList)

    @commands.command(name='now_playing', aliases=['np', 'current', 'playing'], pass_context=True)
    async def now_playing(self, ctx):
        # This displays the information about the currently playing song
        vc = ctx.voice_client

        if not vc or not vc.is_connected():
            return await ctx.send(embed=botNotInChannel)

        player = self.get_player(ctx)
        if not player.current:
            return await ctx.send(embed=botNotPlaying)

        try:
            # Removing our previous now_playing message
            await player.np.delete()

        except HTTPException:
            pass

        player.np = await ctx.send(embed=customEmbed(
            description=f"**Now Playing:** **[{vc.source['title']}]**({vc.source['webpage_url']})"
                        f"requested by **[{vc.source['requester']}]**"
        ))

    @commands.command(name='volume', aliases=['vol'], pass_context=True)
    async def change_volume(self, ctx, *, vol: float):
        # This function changes the player volume
        # value = 1 to 100

        vc = ctx.voice_client

        if not vc or not vc.is_connected():
            return await ctx.send(embed=botNotInChannel)

        if not 0 < vol < 101:
            return await ctx.send(customEmbed('Please enter a value between 1 and 100.'))

        player = self.get_player(ctx)

        if vc.source:
            vc.source.volume = vol // 100

        player.volume = vol // 100

        await ctx.send(embed=customEmbed(f'**{ctx.author}]**: Set the volume to **{vol}%**'))

    @commands.command(name='stop', pass_context=True)
    async def stop(self, ctx):
        """Stop the currently playing song and destroy the player.
                !Warning!
                    This will destroy the player assigned to your guild, also deleting any queued songs and settings.
                """
        vc = ctx.voice_client

        if not vc or not vc.is_connected():
            return await ctx.send(embed=botNotPlaying)

        await self.cleanup(ctx.guild)

    @commands.command(name='playall', pass_context=True)
    async def playAll(self, ctx):
        # This function adds songs in bulk from a file sent to the bot

        await ctx.trigger_typing()

        vc = ctx.voice_client

        if not vc:
            await ctx.invoke(self.connect)

        fileUrl = ctx.message.attachments[0].url
        if fileUrl is None:
            if os.path.exists(f'currentPlaylist/{ctx.guild.id}.txt'):
                pass
            else:
                await ctx.send('No file has been attached to the message.')
        else:
            file = requests.get(fileUrl)
            with open(f'currentPlaylist/{ctx.guild.id}.txt', 'wb') as wp:
                wp.write(file.content)

        player = self.get_player(ctx)
        with open(f'currentPlaylist/{ctx.guild.id}.txt', 'r') as sg:
            for search in sg:

                source = await YTDLSource.create_source(ctx, search, loop=self.bot.loop, download=False)
                await ctx.send(
                    embed=customEmbed(
                        f"{ctx.author.mention}: Added [{source['title']}]({source['webpage_url']}) to the Queue.]"))
                player.playlist.append(source['title'])
                if player.queue.empty():
                    await player.queue.put(source)
                    await asyncio.sleep(1)
                else:
                    await player.queue.put(source)


    @commands.command(name='shuffle', pass_context=True)
    async def shuffle(self, ctx):
        # This shuffle the play queue using the random library
        player = self.get_player(ctx)
        shuffle(player.queue._queue)
        await ctx.send(embed=customEmbed(f'{ctx.author.mention}: The queue has been shuffled.'))
        return

    @commands.command(name='clear',pass_context=True)
    async def clear(self,ctx):
        player = self.get_player(ctx)
        player.queue = asyncio.Queue()
        player.playlist =[]
        await ctx.send(embed= customEmbed(f"{ctx.author.mention}: Cleared the queue. "))

    @commands.command(pass_context=True)
    async def hello(self, ctx):
        await ctx.send(f'Hello! {ctx.author}')
        return

    @commands.command(name='ping', pass_context=True)
    async def ping(self, ctx):
        await ctx.send(embed=customEmbed(str(int(ctx.bot.latency * 1000)) + 'ms'))

    @commands.command(name='help',pass_context=True)
    async def help(self,ctx,cmd : str = None ):
        embed = discord.Embed(
                title= "Fury Music's bot Commands",
                colour=discord.Colour.blue()
            )

        if cmd is None:
            self.embedAddField(embed,name='Music Commands',value='play, queue, q, pause, resume, playall, shuffle, volume, vol, current, playing, np, skip, next')
            self.embedAddField(embed,name='PlayList commands',value='playlist, playlists, playlist, playlist save, playlist add, playlist remove')
            self.embedAddField(embed,name='Additional commands',value='echo, hello, ping, help')
            embed.set_footer(text=f'use {self.cmdPrefix}help <command> for better description')


        elif cmd == "play":
            self.embedAddField(embed,name="Play Command",value=f'{self.cmdPrefix}play <name or url>\n'
                                                      'It will play the requested song or else add it to the queue')

        elif cmd in ["queue","q"]:
            self.embedAddField(embed,name="Queue command",value=f"{self.cmdPrefix}{cmd}")

        elif cmd == "pause":
            self.embedAddField(embed,name='Pause Command',value=f'{self.cmdPrefix}pause\n'
                            'It will pause the playback i.e., current song')

        elif cmd == "resume":
            self.embedAddField(embed,name='Resume Command',value=f'{self.cmdPrefix}resume\n'
                            'It will resume the playback i.e., current song')

        elif cmd == "playall":
            self.embedAddField(embed,name='Playall Command',value=f'{self.cmdPrefix}playall <file>\n'
                               'Add a file and in optional comments add this command to load the songs in the file\n'
                               'The file which been attached must be a text file and a song name in a line.')

        elif cmd == "shuffle":
            self.embedAddField(embed,name='Shuffle Command',value=f'{self.cmdPrefix}shuffle\n'
                               'It will shuffle the current queue list.')

        elif cmd in ["volume","vol"]:
            self.embedAddField(embed,name='Volume Command',value=f'{self.cmdPrefix}{cmd} <value in range the of 1 to 100 >'
                                                                 f'It will change the volume level.')

        elif cmd == ["current","playing","np"]:
            self.embedAddField(embed,name='Current song Command',value=f"{self.cmdPrefix}{cmd}\n"
                                                                  f"It will display the details of the current song which is playing.")

        elif cmd == ["next","skip"]:
            self.embedAddField(embed,name="Skip Command",value=f"{self.cmdPrefix}{cmd}\n"
                                                               f"It will skip the current song and move to next.")

        elif cmd == ["echo"]:
            self.embedAddField(embed,name="Echo Command",value=f"{self.cmdPrefix}{cmd} < string >\n"
                                                               f"The bot echo the contents given next to the echo command.")

        elif cmd == ["hello"]:
            self.embedAddField(embed,name='Hello Command',value=f"{self.cmdPrefix}{cmd}\n It will wave back at you.")

        elif cmd == ["ping"]:
            self.embedAddField(embed,name="Ping Command",value=f"{self.cmdPrefix}{cmd}\n It will send the latency value in ms to the channel.")



        embed.set_author(name=f'{ctx.message.author}', icon_url=f'{ctx.message.author.avatar_url}')
        await ctx.send(embed=embed)
