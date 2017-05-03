#!/usr/bin/python

import requests
import json
import datetime
import warnings
import time
import logging
import telegram
import rfc3339
from telegram.ext import Updater
from telegram.ext import CommandHandler
from telegram.ext import Job
from datetime import datetime, timedelta
from dateutil.parser import parse
from apiclient.discovery import build
from apiclient.errors import HttpError

#Cache with streamers already detected
listStreamers = []

logging.basicConfig()
warnings.filterwarnings("ignore", category=UnicodeWarning)
logging.getLogger('googleapiclient.discovery_cache').setLevel(logging.ERROR)
logging.getLogger('googleapiclient.discovery').setLevel(logging.ERROR)

execfile("config.py")

def start(bot, update):
  bot.sendMessage(chat_id=update.message.chat_id, text="Welcome!")
  
def startNotifier(bot, update, job_queue):
  #Check if user sending the command is allowed
  if(allowed_users_id.count(update.message.from_user.id) == 1):
    chat_id = update.message.chat_id
    #Start the Job to check new streamers
    jobCheckNewStreams = Job(checkNewStreams, checkTimeSeconds, context=chat_id)
    job_queue.put(jobCheckNewStreams, next_t=0.0)
    #Start the Job to check if streamers are still broadcasting
    jobCheckStreamsOnline = Job(checkStreamsOnline, checkTimeSecondsLive, context=chat_id)
    job_queue.put(jobCheckStreamsOnline, next_t=checkTimeSecondsLive)
    #Start the Job to check new videos
    jobCheckNewVideos = Job(checkNewYoutubeVideos, checkTimeSecondsYoutube, context=chat_id)
    job_queue.put(jobCheckNewVideos, next_t=0.0)
    
    bot.sendMessage(chat_id=update.message.chat_id, text='JobQueue started. You will receive notifications when new streamers start playing.')
  else:
    bot.sendMessage(chat_id=update.message.chat_id, text='You don\'t have permissions to do this.')
  
def stopNotifier(bot, update, job_queue):
  #Check if user sending the command is allowed
  if(allowed_users_id.count(update.message.from_user.id) == 1):
    for job in job_queue.jobs():
      #Stop all jobs
      job.enabled = False
      job.schedule_removal()

    bot.sendMessage(chat_id=update.message.chat_id, text='JobQueue stopped.')
  else:
    bot.sendMessage(chat_id=update.message.chat_id, text='You don\'t have permissions to do this.')
  
def checkNewStreams(bot, job):
  #Request all streamers playing the game
  twitch_api_stream_url = "https://api.twitch.tv/kraken/streams/" + "?client_id=" + twitch_client_id + "&game=" + game_name + "&limit=100"

  streamer_html = requests.get(twitch_api_stream_url)
  streamer = json.loads(streamer_html.content)
  
  print "Finding new streamers..."

  #If we receive an error from Twitch don't do anything and we will try again next time
  if(streamer_html.status_code != 200):
    print "Error received while requesting data from Twitch."
    return

  for i in streamer['streams']:
    #Check if the streamer is not already on the cache
    if i['channel']['display_name'] not in listStreamers:
      #If not included, we include and and send a message through Telegram
      print 'Found Streamer: ' + i['channel']['display_name']
      listStreamers.append(i['channel']['display_name'])
      
      if i['channel']['followers'] > thresholdTwitchFollowers:
        bot.sendMessage(job.context, text='New stream for ' + game_name + ': <a href="' + i['channel']['url'] + '">' + i['channel']['display_name'] + '</a>' + ' (' + str(i['channel']['followers']) + ' followers)', parse_mode=telegram.ParseMode.HTML)

def checkStreamsOnline(bot, job):
  #Remove streamers that are offline or playing another game
  print 'Mantaining Streamers list...'
  for entry in listStreamers:
    #Request channel info
    twitch_api_stream_id_url = "https://api.twitch.tv/kraken/streams/" + str(entry) + "?client_id=" + twitch_client_id

    streamer_id_html = requests.get(twitch_api_stream_id_url)
    streamer_id = json.loads(streamer_id_html.content)
    
    #If we receive an error from Twitch don't do anything and we will try again next time
    if(streamer_id_html.status_code != 200):
      print "Error received while requesting data from Twitch."
      return
    
    if(streamer_id['stream'] is None):
      print 'Deleted Streamer: ' + entry
      listStreamers.remove(entry)
    elif(streamer_id['stream']['channel']['game'] != game_name):
      print 'Deleted Streamer: ' + entry
      listStreamers.remove(entry)
      
def checkNewYoutubeVideos(bot, job):
  youtube = build("youtube", "v3",
    developerKey=youtube_developer_key)
    
  date_to_check = rfc3339.rfc3339(datetime.utcnow() - timedelta(seconds=checkTimeSecondsYoutube), True, False)

  # Call the search.list method to retrieve results matching the specified query term.
  search_response = youtube.search().list(
    q=game_name,
    type="video",
    order="date",
    part="id,snippet",
    publishedAfter=date_to_check,
    maxResults=25
  ).execute()

  videos = []

  # Parse the result and get the data for each video
  for search_result in search_response.get("items", []):
    search_channel_response = youtube.channels().list(
      id=search_result["snippet"]["channelId"],
      part="snippet,statistics"
    ).execute()
      
    print 'Found Video: ' + search_result["snippet"]["title"]
    
    if int(search_channel_response.get("items", [])[0]["statistics"]["subscriberCount"]) > thresholdYoutubeSubscribers:
      bot.sendMessage(job.context, text='New video for ' + game_name + ': <a href="https://www.youtube.com/watch?v=' + search_result["id"]["videoId"] + '">' + search_result["snippet"]["title"] + '</a>' + ' (' + search_channel_response.get("items", [])[0]["snippet"]["title"] + ' - ' + search_channel_response.get("items", [])[0]["statistics"]["subscriberCount"] + ' subscribers)', parse_mode=telegram.ParseMode.HTML)
  
def main():
  updater = Updater(token=telegram_token)
  dispatcher = updater.dispatcher

  #Bot commands
  dispatcher.add_handler(CommandHandler('start', start))
  dispatcher.add_handler(CommandHandler('startnotifier', startNotifier, pass_job_queue=True))
  dispatcher.add_handler(CommandHandler('stopnotifier', stopNotifier, pass_job_queue=True))
  
  updater.start_polling()
  
  updater.idle()
  
if __name__ == '__main__':
  main()