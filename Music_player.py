# This class will implement the music player for the bot.
# The bot will use the instance of this class for each guild

# This brings in the functionality of the discord library
import discord

# This is used to implement the asynchronous operations like building a dynamic queue
import asyncio

# This timeout class is used to create a asynchronous timer
from async_timeout import timeout

# This is used to call upon the YTDLsource class
from Song import YTDLSource

# This function will let us to get the required voice client of the bot.
from discord.utils import get

# This exception class is imported to aid us in finding whether the song is playing or completed
from discord import HTTPException


class MusicPlayer:
    # Instance of this class will be destroyed if the bot leaves the voice channel

    __slots__ = ('bot', '_guild', '_channel', '_cog', 'queue', 'next', 'current', 'np', 'volume', 'playlist')

    def __init__(self, ctx):
        self.bot = ctx.bot
        self._guild = ctx.guild
        self._channel = ctx.channel
        self._cog = ctx.cog

        self.playlist = []
        self.queue = asyncio.Queue()
        self.next = asyncio.Event()

        self.np = None  # Now playing message
        self.volume = .5
        self.current = None

        ctx.bot.loop.create_task(self.player_loop())

    async def player_loop(self):
        # This will be the main audio player for the bot in specific server/guild
        await self.bot.wait_until_ready()

        while not self.bot.is_closed():
            self.next.clear()

            try:
                # Wait for the next song.
                # If we timeout cancel the player and disconnect from the voice client
                async with timeout(300):
                    # It will await till the user enters another song
                    source = await self.queue.get()
                    if source['title'] not in self.playlist:
                        continue

            except asyncio.TimeoutError:
                # Destroys the player of the specific guild
                return self.destroy(self._guild)

            if not isinstance(source, YTDLSource):
                # If the source was a probably a stream then,
                # the stream must be regathered to prevent stream expiration
                try:
                    source = await YTDLSource.regather_stream(source, loop=self.bot.loop)
                except Exception as e:
                    await self._channel.send(f'There was an error processing your song.\n'f'```css\n[{e}]\n```')

                    continue

            source.volume = self.volume
            self.current = source
            voice = get(self.bot.voice_clients, guild=self._guild)

            voice.play(source, after=lambda _: self.bot.loop.call_soon_threadsafe(self.next.set))
            self.np = await self._channel.send(embed=discord.Embed(description=f'**Now Playing:** **[{source.title}]**({source.web_url}) '
                                                                               f'requested by'f'**[{source.requester}]**'))
            self.playlist.remove(source['title'])

            await self.next.wait()

            # Making sure the FFmpeg process is cleaned up.
            source.cleanup()
            self.current = None

            try:
                # We are no longer playing this song
                await self.np.delete()

            except HTTPException:
                pass

    def destroy(self, guild):
        # The bot will disconnect from the voice client and cleanup the player data
        return self.bot.loop.create_task(self._cog.cleanup(guild))
