#!/usr/bin/python

#Game to check
game_name = ""
#Twitch Client ID
twitch_client_id = ""
#Youtube Developer Key
youtube_developer_key = ""
#Telegram Bot Token received from BotFather
telegram_token = ""
#Telegram Users allowed to start/stop the job
allowed_users_id = []

#Time between checks with Twitch API for new streams
checkTimeSeconds = 120
#Time between checks with Twitch API for checking live streams
checkTimeSecondsLive = 600
#Time between checks with Youtube API
checkTimeSecondsYoutube = 900
#Threshold of followers/subscribes to send notification to Telegram
thresholdTwitchFollowers = 1000
thresholdYoutubeSubscribers = 2000