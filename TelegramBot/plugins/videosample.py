from TelegramBot.helpers.gdrivehelper import GoogleDriveHelper
from TelegramBot.helpers.functions import *

from pyrogram.errors import MessageNotModified
from pyrogram import Client, filters
from pyrogram.types import Message

from urllib.parse import unquote
import subprocess
import datetime
import requests
import asyncio
import httpx
import shlex 
import time
import json
import re

#thumbnail of the video file.
thumb_path = f"download/thumb.jpg"
thumb = requests.get("https://te.legra.ph/file/508f1cd599bb3d9352e88.jpg", allow_redirects=True)
open(thumb_path, "wb").write(thumb.content)
                                                           
async def generate_videosample_from_link(
        message,
        replymsg,
        file_url,
        duration,        
        headers,
        file_name,
        timestamp, 
):
    """
    Generates videosamples from direct download links using ffmpeg.
    """

    await replymsg.edit(f"Generating {duration} minutes video sample from `{unquote(file_name)}`, please wait ...")
    
    rand_str = randstr()
    makedir(f"download/videosample_{rand_str}")
    output_path = f"download/videosample_{rand_str}/{file_name}"

    ffmpeg_command = f"ffmpeg -headers '{headers}' -y -i {file_url} -ss {timestamp} -t 00:0{int(duration)}:00  -c:v copy -c:a copy {output_path}" 
    shell_output = await async_subprocess(ffmpeg_command)
    if os.path.getsize(output_path) > 1900000000:
    	shutil.rmtree(f"download/videosample_{rand_str}")
    	return await replymsg.edit("Sample file is larger than 2GB. Can not upload large sample files wich exceed Telegram Limits.")

    await replymsg.edit("Uploading the video file. Please wait...")
    await message.reply_video(video=output_path, caption=f"[**{duration}min Sample**] {file_name}", thumb=thumb_path, quote=True)
    
    #clearing the storage.
    await replymsg.delete()
    shutil.rmtree(f"download/videosample_{rand_str}")



async def gdrive_videosample(message, url, duration):
    """
    Generate video sample From Google Drive links.
    """

    replymsg = await message.reply_text("Checking your given gdrive Link...", quote=True)
    try:
        drive = GoogleDriveHelper()
        metadata = drive.get_metadata(url)
        file_name = metadata["name"]

        if "video" not in metadata["mimeType"]:
            return await replymsg.edit("can only generate screenshots from video file.**")

        file_url = drive.get_ddl_link(url)
        bearer_token = drive.get_bearer_token()
        headers = f"Authorization: Bearer {bearer_token}"

        total_duration = await async_subprocess(
            f"ffprobe -headers '{headers}' -v error -show_entries format=duration -of default=noprint_wrappers=1:nokey=1 {file_url}")
        total_duration = float(total_duration.strip())                    
        
        #Generate a random timestamp between first 15-20% of the movie. 
        timestamp = total_duration * (random.uniform(15, 20) / 100) 
         	
        #convering final timestamp into HH:MM:SS format
        timestamp = str(datetime.timedelta(seconds=int(timestamp))) 

        await generate_videosample_from_link(
            message,
            replymsg,
            file_url,
            duration,
            headers,
            file_name,
            timestamp)
            
    except MessageNotModified: pass
    except Exception as error:
        await replymsg.edit(
            f"Something went wrong while processing Gdrive link. Make sure the links is public and not rate limited.")


async def ddl_videosample(message, url,  duration):
    """
    Generate video sample from Direct Download links.
    """

    replymsg = await message.reply_text(f"Checking direct download url....**", quote=True)
    try:
        file_url = f"'{url}'"
        file_name = re.search(".+/(.+)", url).group(1)

        headers = "user-agent: Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/84.0.4136.7 Safari/537.36"
        
        #calculate total duration of the video file.
        total_duration = await async_subprocess(
            f"ffprobe -v error -show_entries format=duration -of default=noprint_wrappers=1:nokey=1 {file_url}")
        total_duration = float(total_duration.strip())
        
        #Generate a random timestamp between first 15-20% of the movie. 
        timestamp = total_duration * (random.uniform(15, 20) / 100)                                       
        
        #convering final timestamp into HH:MM:SS format
        timestamp = str(datetime.timedelta(seconds=int(timestamp))) 

        await generate_videosample_from_link(
            message,
            replymsg,
            file_url,
            duration,            
            headers,
            file_name,
            timestamp)

    except MessageNotModified: pass
    except Exception as error:
        return await replymsg.edit(
            f"Something went wrong! Make sure that URL is for a non-IP specific, downloadable video file that returns a proper response code without any required headers.")


async def telegram_videosample(message, client, duration):
    """
    Generate video  from Telegram Video Files.
    """ 

    try:
    	message = message.reply_to_message
    	if message.text:
    		return await message.reply_text("Reply to a proper video file to Generate Screenshots.", quote=True)
    	elif message.media.value == "video":
    		media = message.video
    	elif message.media.value == "document":
    		media = message.document
    	else:
    		return await message.reply_text("can only generate screenshots from video file....", quote=True)
    	
    	file_name = str(media.file_name)
    	mime = media.mime_type
    	file_size = media.file_size
    	if message.media.value == "document" and "video" not in mime:
    		return await message.reply_text("can only generate screenshots from video file. Please wait....", quote=True)
    		
    	replymsg = await message.reply_text(f"Generating {duration} min video sample from `{unquote(file_name)}`, please wait ...", quote=True)
    	rand_str = randstr()
    	makedir(f"download/videosample_{rand_str}")
    	download_path = f"download/videosample_{rand_str}/{file_name}"
    	
    	async for chunk in client.stream_media(message, limit=5):
    		with open(f"{download_path}", 'ab') as f: f.write(chunk)
    	
    	mediainfo_json = await async_subprocess(f"mediainfo '{download_path}' --Output=JSON")
    	mediainfo_json = json.loads(mediainfo_json)
    	total_duration = mediainfo_json["media"]["track"][0]["Duration"]
   
    	bitrate = float(file_size)/float(total_duration)
    	os.remove(download_path)
    	
    	#limit of partial file to be downloaded from given time duration 
    	download_limit: int = ((bitrate)*(duration*60))*0.000001
    	async for chunk in client.stream_media(message, limit=int(download_limit)):
    	    with open(f"{download_path}", "ab") as file:
    	    	file.write(chunk)
    	    	
    	#fixing the file metadata.
    	output_path = f"download/videosample_{rand_str}/output_{file_name}"
    	ffmpeg_command = f"ffmpeg -i '{download_path}' -c copy -metadata duration=10000 '{output_path}'"
    	await async_subprocess(ffmpeg_command) 	
    	await message.reply_video(video=output_path, caption=f"[**{duration}min Sample**] {file_name}", thumb=thumb_path, quote=True)
    	
    	await replymsg.delete()
    	shutil.rmtree(f"download/videosample_{rand_str}")
    	
    except Exception as error:
        await message.reply_text(f"Something went wrong while processing your query!!", quote=True)
     
           	
           	        	      	         	      	 

sample_duration = [
    [
        InlineKeyboardButton("1min",  callback_data="videosample_1"),
        InlineKeyboardButton("5min",  callback_data="videosample_5"),
        InlineKeyboardButton("10min", callback_data="videosample_10")
    ]
]

info_dictionary: dict = { }
@Client.on_callback_query(filters.regex("videosample_"))
async def videosample_duration(client,  CallbackQuery):
	duration = int(CallbackQuery.data.split("_")[-1])
	message_id = CallbackQuery.message.reply_to_message.id
	await  client.delete_messages(CallbackQuery.message.chat.id, CallbackQuery.message.id)
	
	message  = info_dictionary[message_id]["message"]	
	type = info_dictionary[message_id]["type"]	
	
	if type == "gdrive":
		return await gdrive_videosample(message, info_dictionary[message_id]["url"], duration)
	elif type == "ddl":
		return await ddl_videosample(message, info_dictionary[message_id]["url"], duration)
	else:
		return await telegram_videosample(message, info_dictionary[message_id]["client"], duration)
		
	
	
@Client.on_message(filters.command(["sample", "trim"]))
async def video_sample(client: Client, message: Message):
    """
    Generates Screenshots from ddl, gdrive or Telegram file.
    """
    
    if message.reply_to_message:    	 	
    	info_dictionary[message.id] = {}
    	info_dictionary[message.id]["message"] = message
    	info_dictionary[message.id]["client"] = client 
    	info_dictionary[message.id]["type"] = "telegram" 	
    	return await message.reply_text("Choose time duration of sample video.", reply_markup=InlineKeyboardMarkup(sample_duration), quote=True)    	
    	        	             	    
    if len(message.command) < 2:
    	return await message.reply_text(
    	"Generates video samples from GoogleDrive links, Telegram files or direct download links." , quote=True)
    	
    user_input = message.text.split(None, 1)[1]    
    if url_match := re.search(r"https://drive\.google\.com/\S+", user_input):
    	url = url_match.group(0)    	
    	info_dictionary[message.id] = {}
    	info_dictionary[message.id]["message"] = message
    	info_dictionary[message.id]["type"] = "gdrive"
    	info_dictionary[message.id]["url"] = url    	
    	return await message.reply_text("Choose time duration of sample video.", reply_markup=InlineKeyboardMarkup(sample_duration), quote=True)    	
    	        	
    if url_match := re.search(r"https?://([\w_-]+(?:(?:\.[\w_-]+)+))([\w.,@?^=%&:\/~+#-]*[\w@?^=%&\/~+#-])", user_input):
    	url = url_match.group(0)	
    	info_dictionary[message.id] = {}
    	info_dictionary[message.id]["message"] = message
    	info_dictionary[message.id]["type"] = "ddl"
    	info_dictionary[message.id]["url"] = url    	
    	return await message.reply_text("Choose time duration of sample video.", reply_markup=InlineKeyboardMarkup(sample_duration), quote=True)    	   	        	
    else: return await message.reply_text("This type of link is not supported.", quote=True)
	
	
