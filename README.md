# MusicRex
This Discord bot implements Discord, Spotify, and MongoDB API in order to create a public Spotify playlist that your Discord server's members can all add songs to!\
https://discord.com/api/oauth2/authorize?client_id=988964938238271488&permissions=3136&scope=bot

# Documentation
### Server Managers:
**m!config** - Run this to set up the bot! (Won't create a new Spotify playlist if you've use this bot before)\
**m!getconfig** - Print the config file\
**m!rename** - Rename this server's Spotify playlist\
**m!maxsongs** - Set the maximum number of songs allowed in the server's Spotify playlist (older songs will be removed to make room for new additions)\
**m!channel** - Set the channel where regular commands must be used
### Regular Commands
**m!help** - Prints this guide (can be used anywhere the bot can see)\
**m!add** <Spotify Track Link> - Add a song to the server's Spotify playlist\
**m!get** - Get a direct link to the server's Spotify playlist
