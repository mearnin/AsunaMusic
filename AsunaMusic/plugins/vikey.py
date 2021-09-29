import os
import re
import sys
import time
import ffmpeg
import asyncio
import subprocess
from typing import Callable
import requests
import wget
from asyncio import sleep
from youtube_dl import YoutubeDL
from pyrogram import Client, filters
from pyrogram.types import Message
from pytgcalls import GroupCallFactory
from config import BOT_NAME
from config import AUDIO_CALL, VIDEO_CALL
from youtube_search import YoutubeSearch
from helpers.decorators import authorized_users_only
from AsunaMusic import USER
from pyrogram.types import InlineKeyboardButton, InlineKeyboardMarkup, CallbackQuery
from helpers.admins import get_admins
from config import que
from helpers.queues import queues
from helpers.filters import command, other_filters
from PIL import Image, ImageDraw, ImageFont
from pyrogram.errors import UserAlreadyParticipant
from Python_ARQ import ARQ

ydl_opts = {
        "quiet": True,
        "geo_bypass": True,
        "nocheckcertificate": True,
}
ydl = YoutubeDL(ydl_opts)
group_call = GroupCallFactory(User, GroupCallFactory.MTPROTO_CLIENT_TYPE.PYROGRAM).get_group_call()
aiohttpsession = aiohttp.ClientSession()
arq = ARQ("https://thearq.tech", ARQ_API_KEY, aiohttpsession)

def convert_seconds(seconds):
    seconds = seconds % (24 * 3600)
    seconds %= 3600
    minutes = seconds // 60
    seconds %= 60
    return "%02d:%02d" % (minutes, seconds)


# Convert hh:mm:ss to seconds
def time_to_seconds(time):
    stringt = str(time)
    return sum(int(x) * 60 ** i for i, x in enumerate(reversed(stringt.split(":"))))


# Change image size
def changeImageSize(maxWidth, maxHeight, image):
    widthRatio = maxWidth / image.size[0]
    heightRatio = maxHeight / image.size[1]
    newWidth = int(widthRatio * image.size[0])
    newHeight = int(heightRatio * image.size[1])
    newImage = image.resize((newWidth, newHeight))
    return newImage


async def generate_cover(requested_by, title, views, duration, thumbnail):
    async with aiohttp.ClientSession() as session:
        async with session.get(thumbnail) as resp:
            if resp.status == 200:
                f = await aiofiles.open("background.png", mode="wb")
                await f.write(await resp.read())
                await f.close()

    image1 = Image.open("./background.png")
    image2 = Image.open("./etc/foreground.png")
    image3 = changeImageSize(1280, 720, image1)
    image4 = changeImageSize(1280, 720, image2)
    image5 = image3.convert("RGBA")
    image6 = image4.convert("RGBA")
    Image.alpha_composite(image5, image6).save("temp.png")
    img = Image.open("temp.png")
    draw = ImageDraw.Draw(img)
    font = ImageFont.truetype("etc/font.otf", 32)
    draw.text((205, 550), f"Title: {title}", (51, 215, 255), font=font)
    draw.text((205, 590), f"Duration: {duration}", (255, 255, 255), font=font)
    draw.text((205, 630), f"Views: {views}", (255, 255, 255), font=font)
    draw.text(
        (205, 670),
        f"Added By: {requested_by}",
        (255, 255, 255),
        font=font,
    )
    img.save("final.png")
    os.remove("temp.png")
    os.remove("background.png")
    

@Client.on_callback_query(filters.regex("pause_callback"))
async def pause_callbacc(client, CallbackQuery):
    chat_id = CallbackQuery.message.chat.id
    if chat_id in AUDIO_CALL:
        text = f"⏸ Paused !"
        await AUDIO_CALL[chat_id].set_audio_pause(True)
    elif chat_id in VIDEO_CALL:
        text = f"⏸ Paused !"
        await VIDEO_CALL[chat_id].set_video_pause(True)
    else:
        text = f"❌ Nothing is Playing !"
    await Client.answer_callback_query(
        CallbackQuery.id, text, show_alert=True
    )

@Client.on_callback_query(filters.regex("resume_callback"))
async def resume_callbacc(client, CallbackQuery):
    chat_id = CallbackQuery.message.chat.id
    if chat_id in AUDIO_CALL:
        text = f"▶️ Resumed !"
        await AUDIO_CALL[chat_id].set_audio_pause(False)
    elif chat_id in VIDEO_CALL:
        text = f"▶️ Resumed !"
        await VIDEO_CALL[chat_id].set_video_pause(False)
    else:
        text = f"❌ Nothing is Playing !"
    await Client.answer_callback_query(
        CallbackQuery.id, text, show_alert=True
    )


@Client.on_callback_query(filters.regex("end_callback"))
async def end_callbacc(client, CallbackQuery):
    chat_id = CallbackQuery.message.chat.id
    if chat_id in AUDIO_CALL:
        text = f"⏹️ Stopped !"
        await AUDIO_CALL[chat_id].stop()
        AUDIO_CALL.pop(chat_id)
    elif chat_id in VIDEO_CALL:
        text = f"⏹️ Stopped !"
        await VIDEO_CALL[chat_id].stop()
        VIDEO_CALL.pop(chat_id)
    else:
        text = f"❌ Nothing is Playing !"
    await Client.answer_callback_query(
        CallbackQuery.id, text, show_alert=True
    )
    await Client.send_message(
        chat_id=CallbackQuery.message.chat.id,
        text=f"✅ **Streaming Stopped & Left The Video Chat !**"
    )
    await CallbackQuery.message.delete()
    

@Client.on_callback_query(filters.regex("cls"))
async def cls_callbacc(client, CallbackQuery):
  chat_id = CallbackQuery.message.chat.id
  await CallbackQuery.message.delete()

keyboard = InlineKeyboardMarkup(
  [
      [
        InlineKeyboardButton(
          text="⏸️pause",
          callback_data="pause_callback",),
        InlineKeyboardButton(
          text="▶️Resume",
          callback_data="resume_callback",),
      ],
      [
        InlineKeyboardButton(
          text="⏹️Stop",
          callback_data="stop_callback",)
      ],
  ]
)

@Client.on_message(filters.command("play") &  other_filters)
async def play_command(client, message: Message):
    global queues
    msg = await message.reply_text("📶 Processing")
    administrators = await get_admins(message.chat)
    chatid = message.chat.id
    
    try:
        await USER.get_me()
    except:
        user.first_name = "helper"
    
    wow = user.id
    banned = client.get_chat_member(chatid, filter="kicked")
    try:
        await client.get_chat_member(chatid, wow)
    except:
        for administrator in administrators:
            if administrator == message.from_user.id:
                try:
                    invitelink = await client.export_chat_invite_link(chatid)
                except:
                    await msg.edit("**🤦 Add me as an admin first")
                return
                try:
                    await USER.join_chat(invitelink)
                    await USER.send_message("✅  userbot joined this chat")
                except UserAlreadyParticipant:
                    pass
                except Exception:
                    if wow in  banned:
                        await msg.edit("**❌User bot is banned in this chat! Please unban it first")
                    else:
                        await msg.edit("**🟥 Flood wait error")
    try:
        await USER.get_chat(chatid)
    except:
        await msg.edit(f"**Please add userbot manually")
        return
    
    media = message.reply_to_message
    
    if not media and not '' in message.text:
        await msg.edit("❌ give me something to play in VC")
    
    elif '' in message.text:
        text = message.text.split('', 1)
        vid = text[1]
        user_id = message.from_user.id
        user_name = message.from_user.first_name
        rpk = "[" + user_name + "](tg://user?id=" + str(user_id) + ")"
        return await msg.edit("Processing...")
        if 'https' not in vid:
            try:
                results = Videosearch(vid, max_results=5).to_dict()
            except:
                await msg.edit("Give me something to play")
        # Looks like hell. Aren't it?? FUCK OFF
            try:
                toxxt = "**Select the song you want to play**\n\n"
                j = 0
                useer = user_name
                emojilist = [
                    "1️⃣",
                    "2️⃣",
                    "3️⃣",
                    "4️⃣",
                    "5️⃣",
            ]

                while j < 5:
                    toxxt += f"{emojilist[j]} <b>Title - [{results[j]['title']}](https://youtube.com{results[j]['url_suffix']})</b>\n"
                    toxxt += f" ╚ <b>Duration</b> - {results[j]['duration']}\n"
                    toxxt += f" ╚ <b>Views</b> - {results[j]['views']}\n"
                    toxxt += f" ╚ <b>Channel</b> - {results[j]['channel']}\n\n"

                    j += 1
                koyboard = InlineKeyboardMarkup(
                [
                    [
                        InlineKeyboardButton(
                            "1️⃣", callback_data=f"plll 0|{query}|{user_id}"
                        ),
                        InlineKeyboardButton(
                            "2️⃣", callback_data=f"plll 1|{query}|{user_id}"
                        ),
                        InlineKeyboardButton(
                            "3️⃣", callback_data=f"plll 2|{query}|{user_id}"
                        ),
                    ],
                    [
                        InlineKeyboardButton(
                            "4️⃣", callback_data=f"plll 3|{query}|{user_id}"
                        ),
                        InlineKeyboardButton(
                            "5️⃣", callback_data=f"plll 4|{query}|{user_id}"
                        ),
                    ],
                    [InlineKeyboardButton(text="❌ Close", callback_data="cls")],
                ]
            )

                await msg.edit(toxxt, reply_markup=koyboard, disable_web_page_preview=True)
            # WHY PEOPLE ALWAYS LOVE PORN ?? (A point to think)
                return
            # Returning to pornhub
            except:
                await msg.edit("No Enough results to choose.. Starting direct play..")

            # print(results)
                try:
                    url = f"https://youtube.com{results[0]['url_suffix']}"
                    title = results[0]["title"][:40]
                    thumbnail = results[0]["thumbnails"][0]
                    thumb_name = f"thumb{title}.jpg"
                    thumb = requests.get(thumbnail, allow_redirects=True)
                    open(thumb_name, "wb").write(thumb.content)
                    duration = results[0]["duration"]
                    results[0]["url_suffix"]
                    views = results[0]["views"]

                except Exception as e:
                    await msg.edit(
                        "Song not found.Try another song or maybe spell it properly."
                )
                    print(str(e))
                    return
                try:
                    secmul, dur, dur_arr = 1, 0, duration.split(":")
                    for i in range(len(dur_arr) - 1, -1, -1):
                        dur += int(dur_arr[i]) * secmul
                        secmul *= 60
                    if (dur / 60) >    DURATION_LIMIT:
                        await msg.edit(
                        f"❌ Videos longer than {DURATION_LIMIT} minutes aren't allowed to play!"
                    )
                        return
                except:
                    pass
                requested_by = message.from_user.first_name
                await generate_cover(requested_by, title, views, duration, thumbnail)
                vid_call = VIDEO_CALL.get(chatid)
                if vid_call:
                    await VIDEO_CALL[chatid].stop()
                    VIDEO_CALL.pop(chatid)
                    await sleep(3)
                else:
                    msg.edit("starting play!")
                try:
                    chat_id = get_chat_id(message.chat)
                    que[chat_id] = []
                    qeue = que.get(chat_id)
                    s_name = title
                    r_by = message.from_user
                    loc = url
                    appendable = [s_name, r_by, loc]
                    qeue.append(appendable)
                    await sleep(2)
                    await group_call.join(chatid)
                    await group_call.start_video(url, with_audio=True, repeat=False)
                    await message.reply_photo(
                        photo="final.png",
                        reply_markup=keyboard,
                        caption="▶️ **Playing</b> here the song requested by {} via Youtube Music 😎**".format(
                        message.from_user.mention()
                            ),
                    )
                    os.remove("final.png")
                    await msg.delete()
                except Exception as e:
                    print(e)
    
    
        elif 'https' in vid:
            await msg.edit("**Processing**")
            try:
                results = YoutubeSearch(vid, max_results=1).to_dict()
                url = f"https://youtube.com{results[0]['url_suffix']}"
            # print(results)
                title = results[0]["title"][:40]
                thumbnail = results[0]["thumbnails"][0]
                thumb_name = f"thumb{title}.jpg"
                thumb = requests.get(thumbnail, allow_redirects=True)
                open(thumb_name, "wb").write(thumb.content)
                duration = results[0]["duration"]
                results[0]["url_suffix"]
                views = results[0]["views"]

            except Exception as e:
                await msg.edit(
                    "Song not found.Try another song or maybe spell it properly."
                )
                print(str(e))
                return
            try:
                secmul, dur, dur_arr = 1, 0, duration.split(":")
                for i in range(len(dur_arr) - 1, -1, -1):
                    dur += int(dur_arr[i]) * secmul
                    secmul *= 60
                if (dur / 60) > DURATION_LIMIT:
                    await msg.edit(
                         f"❌ Videos longer than {DURATION_LIMIT} minutes aren't allowed to play!"
                    )
                    return
            except:
                pass
            requested_by = message.from_user.first_name
            await generate_cover(requested_by, title, views, duration, thumbnail)
            vid_call = VIDEO_CALL.get(chatid)
            if vid_call:
                await VIDEO_CALL[chatid].stop()
                VIDEO_CALL.pop(chatid)
                await sleep(3)
            try:
                chat_id = get_chat_id(message.chat)
                que[chat_id] = []
                qeue = que.get(chat_id)
                s_name = title
                r_by = message.from_user
                loc = url
                appendable = [s_name, r_by, loc]
                qeue.append(appendable)
                await sleep(2)
                await group_call.join(chatid)
                await group_call.start_video(url, with_audio=True, repeat=False)
                await message.reply_photo(
                    photo="final.png",
                    reply_markup=keyboard,
                    caption="▶️ **Playing</b> here the song requested by {} via Youtube Music 😎**".format(
                        message.from_user.mention()
                    ),
                )
                os.remove("final.png")
                await msg.delete()
            except Exception as e:
                print(str(e))


    elif media.video or media.document:
        if round(audio.duration / 60) > DURATION_LIMIT:
            await msg.edit(
                f"❌ Videos longer than {DURATION_LIMIT} minute(s) aren't allowed to play!"
            )
            return
        await msg.edit(f"Downloading..")
        file_name = get_file_name(media)
        title = file_name
        thumb_name = "https://telegra.ph/file/f6086f8909fbfeb0844f2.png"
        thumbnail = thumb_name
        duration = round(media.duration / 60)
        views = "Locally added"
        requested_by = message.from_user.first_name
        await generate_cover(requested_by, title, views, duration, thumbnail)
        vid_call = VIDEO_CALL.get(chatid)
        if vid_call:
            await VIDEO_CALL[chatid].stop()
            VIDEO_CALL.pop(chatid)
            await sleep(3)
            await message.reply_photo(
                  photo="final.png",
                  reply_markup="keyboard",
                  caption="**playing the locally added file",
                  )
            await message.delete()
    
