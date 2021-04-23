# To load the environment file into the program
import os
from dotenv import load_dotenv

# To create a instance of the discord bot 
from discord.ext import commands

# Importing the music bot class
import BotCommands


load_dotenv()
Discord_token = os.getenv('DISCORD_TOKEN')
cmdPrefix = '$'
bot = commands.Bot(command_prefix=cmdPrefix)
bot.remove_command('help')


def setup(bot):
    bot.add_cog(BotCommands.MusicBot(bot,cmdPrefix))



setup(bot)

bot.run(Discord_token)
