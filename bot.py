##########
# bot.py #
##########

import discord
from discord.ext import commands
from discord.ext.commands import has_permissions
from discord.utils import find
from pymongo import MongoClient
# pprint library is used to make the output look more pretty
from pprint import pprint
# used to import the Heroku config vars
# import boto.s3.connection
# from boto.s3.connection import S3Connection
import json
import os
from os.path import exists
import spotipy
from spotipy.oauth2 import SpotifyOAuth
import cred ## "cred" file contains bot's secret data

MONGODB_URI = cred.MONGODB_URI
# MONGODB_URI = S3Connection(os.environ['MONGODB_URI'])
# print(MONGODB_URI)

## Authorizes MusicRex to post "public playlist modifications" to its own Spotify account
scope = "playlist-modify-public"
sp = spotipy.Spotify(auth_manager=SpotifyOAuth(client_id=cred.client_id, client_secret=cred.client_secret, redirect_uri=cred.redirect_url, scope=scope))

## Connect to MongoDB
client = MongoClient(MONGODB_URI)
db = client.configsDB

## Setup
if (sp):
    # print("User ID: " + user_ID)
    print("Spotipy ready.")
    print(sp)
else:
    print("Fatal error during Spotipy init")
    raise SystemExit()
if (db != None):
    # print("User ID: " + user_ID)
    print("MongoDB ready.")
    print(db)
else:
    print("Fatal error during MongoDB init")
    raise SystemExit()
user = sp.current_user()
user_ID = user['id']

## Instantiate the bot (and test db insertion)
bot = commands.Bot(command_prefix = 'm!')
# testConfig = {"channelID": 123, "playlistName": "TEST", "playlistHref": "TEST", "maxSongs": 123}
# print("TEST DB INSERTION")
# print(db.configs.insert_one(testConfig))

## Runs when the bot loads up (worker dyno is enabled)
@bot.event
async def on_ready():
    status = str(len(bot.guilds)) + " playlists!"
    await bot.change_presence(status=discord.Status.online, activity=discord.Activity(type=discord.ActivityType.listening, name=status))
    print("Bot is ready.")

## Runs when the bot joins a server
@bot.event
async def on_guild_join(guild):
    ## Log event
    print(str(guild.id) + " has added MusicRex!")

    ## Update status
    status = str(len(bot.guilds)) + " playlists!"
    await bot.change_presence(status=discord.Status.online, activity=discord.Activity(type=discord.ActivityType.listening, name=status))

##########################
# m!help --> does not override yet
##########################
# @bot.command()
# async def help(ctx):
#     await ctx.send(
#     "Server Managers\n" +
#     "m!config - Run this to set up the bot! (Won't create a new Spotify playlist if you've use this bot before)\n" +
#     "\n" +
#     "m!getconfig - Print the config file\n" +
#     "m!rename - Rename this server's Spotify playlist\n" +
#     "m!maxsongs - Set the maximum number of songs allowed in the server's Spotify playlist (older songs will be removed to make room for new additions)\n" +
#     "m!channel - Set the channel where regular commands must be used\n" +
#     "\n" +
#     "Regular Commands\n" +
#     "m!help - Prints this guide (can be used anywhere the bot can see)\n"
#     "m!add <Spotify Track Link> - Add a song to the server's Spotify playlist\n" +
#     "m!get - Get a direct link to the server's Spotify playlist"
#     )

##########################
# m!config
##########################
@bot.command()
@has_permissions(manage_guild=True)
async def config(ctx):
    def check(m: discord.Message):
        # m = discord.Message.
        return m.author.id == ctx.author.id and m.channel.id == ctx.channel.id
        # checking for both original author and channel

    ## Get the playlist name
    playlistName = ''
    while len(playlistName) > 200 or len(playlistName) == 0:
        await ctx.send("Enter the name you'd like to give your server's public playlist (change this anytime with \"m!rename\")")
        msg = await bot.wait_for('message', check=check, timeout=30)
        playlistName = msg.content
    await msg.add_reaction("🎵")
    # print(playlistName)

    ## Get the number of max songs
    maxSongs = -1
    await ctx.send("Enter the max number of songs you'd like the playlist to have. Oldest songs will be removed to make room for new additions (change this anytime with \"m!maxsongs\")")
    while maxSongs <= 0:
        msg = await bot.wait_for('message', check=check, timeout=30)
        try:
            maxSongs = int(msg.content)
            if maxSongs <= 0:
                raise Exception()
            await msg.add_reaction("🎵")
        except Exception as e:
            # print("User entered non-integer maxSongs")
            await msg.add_reaction("❌")
    # print(maxSongs)

    ## Get the target channel ID
    channelID = -1
    await ctx.send("Enter the channel ID of where you would like commands to be used (change this anytime with \"m!channel\")")
    while channelID <= 0:
        msg = await bot.wait_for('message', check=check, timeout=60)
        try:
            channelID = int(msg.content)
            if channelID <= 0:
                raise Exception()
            await msg.add_reaction("🎵")
        except Exception as e:
            # print("User entered non-integer channelID.")
            await msg.add_reaction("❌")
    # print(channelID)

    ## Setup for config
    serverID = ctx.guild.id
    newConfig = {
        '_id': serverID,
        'channelID': channelID,
        'playlistName': playlistName,
        'playlistHref': '',
        'maxSongs': maxSongs
    }

    ## If no config doc exists, create a playlist and insert a new doc
    if db.configs.find_one({'_id': serverID}) is None:
        playlist = sp.user_playlist_create(user=user_ID, name=playlistName)
        newConfig['playlistHref'] = playlist['external_urls']['spotify']
        db.configs.insert_one(newConfig)
    ## Config doc exists, update playlist information and update doc
    else:
        newConfig['playlistHref'] = db.configs.find_one({'_id': serverID})['playlistHref']
        sp.playlist_change_details(newConfig['playlistHref'], name=playlistName)
        db.configs.update_one({'_id': serverID}, {"$set": newConfig})

    ## Log event
    print(str(serverID) + " New Config: " + json.dumps(db.configs.find_one({'_id': serverID})))

    ## Success!
    await ctx.send("🎵 Okay! You're all set up! Go ahead and add a song with \"m!add <spotify link>\"")

##########################
# m!getconfig
##########################
@bot.command()
@has_permissions(manage_guild=True)
async def getconfig(ctx):
    serverID = ctx.guild.id

    ## If config exists, react to command
    if db.configs.find_one({'_id': serverID}) is not None:
        ## Load config doc
        config = db.configs.find_one({'_id': serverID})
        await ctx.send(json.dumps(config, sort_keys=True, indent=4))
        ## Log event
        print(str(serverID) + " GetConfig " + str(config))
    ## No config exists, send error message
    else:
        ## Failure...
        await ctx.send("This server's playlist hasn't been set up yet. Use \"m!config\" to start!")

##########################
# m!rename
##########################
@bot.command()
@has_permissions(manage_guild=True)
async def rename(ctx):
    def check(m: discord.Message):
        # m = discord.Message.
        return m.author.id == ctx.author.id and m.channel.id == ctx.channel.id
        # checking for both original author and channel

    serverID = ctx.guild.id

    ## If config exists, react to command
    if db.configs.find_one({'_id': serverID}) is not None:
        ## Load config doc
        config = db.configs.find_one({'_id': serverID})
        ## Get the new playlist name
        await ctx.send("Enter the name you'd like to give your server's public playlist")
        msg = await bot.wait_for('message', check=check, timeout=30)
        config['playlistName'] = msg.content
        ## Update playlist name and config doc, and log event
        try:
            sp.playlist_change_details(config['playlistHref'], name=config['playlistName'])
            db.configs.update_one({'_id': serverID}, {'$set': config})
            ## Success!
            print(str(serverID) + " New Config (rename): " + json.dumps(db.configs.find_one({'_id': serverID})))
            await msg.add_reaction("🎵")
        except Exception as e:
            await msg.add_reaction("❌")
    ## No config exists, send error message
    else:
        ## Failure...
        await ctx.send("This server's playlist hasn't been set up yet. Use \"m!config\" to start!")

##########################
# m!maxsongs
##########################
@bot.command()
@has_permissions(manage_guild=True)
async def maxsongs(ctx):
    def check(m: discord.Message):
        # m = discord.Message.
        return m.author.id == ctx.author.id and m.channel.id == ctx.channel.id
        # checking for both original author and channel

    serverID = ctx.guild.id

    ## If config exists, react to command
    if db.configs.find_one({'_id': serverID}) is not None:
        ## Load config doc
        config = db.configs.find_one({'_id': serverID})
        ## Get the new maxSongs
        maxSongs = -1
        await ctx.send("Enter the max number of songs you'd like the playlist to have. Older songs will be removed to make room for new additions")
        while maxSongs <= 0:
            msg = await bot.wait_for('message', check=check, timeout=30)
            try:
                maxSongs = int(msg.content)
                if maxSongs <= 0:
                    raise Exception()
                config['maxSongs'] = maxSongs
                db.configs.update_one({'_id': serverID}, {'$set': config})
                await msg.add_reaction("🎵")
            except Exception as e:
                # print("User entered non-integer maxSongs")
                await msg.add_reaction("❌")
        ## Success!
        print(str(serverID) + " New Config (maxsongs): " + json.dumps(db.configs.find_one({'_id': serverID})))
    ## No config exists, send error message
    else:
        ## Failure...
        await ctx.send("This server's playlist hasn't been set up yet. Use \"m!config\" to start!")

##########################
# m!channel
##########################
@bot.command()
@has_permissions(manage_guild=True)
async def channel(ctx):
    def check(m: discord.Message):
        # m = discord.Message.
        return m.author.id == ctx.author.id and m.channel.id == ctx.channel.id
        # checking for both original author and channel

    serverID = ctx.guild.id

    ## If config exists, react to command
    if db.configs.find_one({'_id': serverID}) is not None:
        ## Load config doc
        config = db.configs.find_one({'_id': serverID})
        ## Get the new channelID
        channelID = -1
        await ctx.send("Enter the channel ID of where you would like commands to be used")
        while channelID <= 0:
            msg = await bot.wait_for('message', check=check, timeout=60)
            try:
                channelID = int(msg.content) # throws exception if non-integer entry
                config['channelID'] = channelID
                db.configs.update_one({'_id': serverID}, {'$set': config})
                await msg.add_reaction("🎵")
            except Exception as e:
                # print("User entered non-integer channelID.")
                await msg.add_reaction("❌")
        ## Success!
        print(str(serverID) + " New Config (channel): " + json.dumps(db.configs.find_one({'_id': serverID})))
    ## No config exists, send error message
    else:
        ## Failure...
        await ctx.send("This server's playlist hasn't been set up yet. Use \"m!config\" to start!")

##########################
# m!add
##########################
@bot.command()
async def add(ctx, uri):
    serverID = ctx.guild.id

    ## If config exists, react to command
    if db.configs.find_one({'_id': serverID}) is not None:
        ## Load config doc
        config = db.configs.find_one({'_id': serverID})
        playlistHref = config['playlistHref']
        channelID = config['channelID']
        ## If the message was sent in the target channel, add the track to the server playlist and log event
        if (ctx.message.channel.id == channelID):
            tracks = [uri]
            try:
                sp.user_playlist_add_tracks(user_ID, playlistHref, tracks)
                ## Success!
                await ctx.message.add_reaction("🎵")
            except Exception as e:
                ## Failure...
                await ctx.message.add_reaction("❌")
            finally:
                print(str(serverID) + " Add Track: " + uri)
    ## No config exists, send error message
    else:
        ## Failure...
        await ctx.send("This server's playlist hasn't been set up yet. Use \"m!config\" to start!")

##########################
# m!get
##########################
@bot.command()
async def get(ctx):
    serverID = ctx.guild.id

    ## Load data from config file or send error message if none exists
    if db.configs.find_one({'_id': serverID}) is not None:
        ## Load config doc
        config = db.configs.find_one({'_id': serverID})
        playlistHref = config['playlistHref']
        channelID = config['channelID']
        ## If the message was sent in the target channel, add the track to the server playlist and log event
        if (ctx.message.channel.id == channelID):
            await ctx.send(playlistHref)
            print(str(serverID) + " Get Playlist: " + playlistHref)
    ## No config exists, send error message
    else:
        ## Failure...
        await ctx.send("This server's playlist hasn't been set up yet. Use \"m!config\" to start!")


## FIRE UP THE BOT
# https://c.tenor.com/uczt3KrTY5MAAAAC/engines-top-gun-maverick.gif
bot.run(cred.bot_token)
