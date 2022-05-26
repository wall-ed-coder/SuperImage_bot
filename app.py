import io
import json
import os
import shutil
from datetime import datetime

import requests
import telebot
from PIL import Image
from telebot import types

from config.sec_config import TOKEN
import config.creditials as cfg

bot = telebot.TeleBot(TOKEN)
user_state = {}

login_reply = types.ReplyKeyboardMarkup(True)
login_reply.row('/login')

start_processing_reply = types.ReplyKeyboardMarkup(True)
start_processing_reply.row('/start_processing')

start_reply = types.ReplyKeyboardMarkup(True)
start_reply.row('/start')


def user_exist(user_id):
    return user_id in user_state and user_state[user_id]['token'] is not None


@bot.message_handler(commands=['start'])
def start_message(message):
    user_id = message.from_user.id

    if user_exist(user_id):
        user_state[user_id]['image'] = None

        bot.send_message(
            message.chat.id,
            'Please load coefficient of improving image by wrote '
            'coefficient=N where N in [2, 4, 8] and upload an image by image or document!',
            reply_markup=start_processing_reply
        )
    else:
        bot.send_message(
            message.chat.id,
            'Hello! This is Super Image Bot, it helps you to get high resolution image from low resolution, enjoy! '
            f'Before we start, you need to registrate in {cfg.MAIN_SITE_LINK}. Thanks!',
            reply_markup=login_reply
        )


@bot.message_handler(commands=['login'])
def login_message(message):
    user_id = message.from_user.id

    user_state[user_id] = {
        'id': user_id,
        'image': None,
        'token': None,
        'coefficient': None,
    }

    bot.send_message(
        message.chat.id,
        'Please pass login and password like "email=qwerty123@qwe.ru password=123qwe"!',
        reply_markup=login_reply
    )


def get_token(message, email, password):
    user_id = message.from_user.id
    try:
        with requests.post(
                cfg.GET_TOKEN_SITE_LINK,
                json={"email": email, 'password': password},
        ) as response:
            response_text = json.loads(response.text)
            if response.status_code == 200:
                bot.send_message(message.chat.id, 'Cool! We can start!', reply_markup=start_reply)
                user_state[user_id]['token'] = response_text.get('token')
            else:
                bot.send_message(message.chat.id, f'Sorry but it failed! {response_text.get("msg")}', reply_markup=login_reply)
    except:
        bot.send_message(message.chat.id, f'Sorry but it failed! Please try again later', reply_markup=login_reply)



@bot.message_handler(commands=['start_processing'])
def start_processing_message(message):
    user_id = message.from_user.id

    if user_exist(user_id):
        if user_state[user_id]['image'] is None:
            bot.send_message(
                message.chat.id,
                'Please upload an image by image or document!',
                reply_markup=start_processing_reply
            )
        elif user_state[user_id]['coefficient'] is None:
            bot.send_message(
                message.chat.id,
                'Please load coefficient of improving image by wrote coefficient=N where N in [2, 4, 8]',
                reply_markup=start_processing_reply
            )
        else:
            bot.send_message(message.chat.id, 'Please wait....')

            image = user_state[user_id]['image']
            coefficient = user_state[user_id]['coefficient']
            token = user_state[user_id]['token']
            file_name = f"{user_id}_{datetime.now()}.png"
            image.save(os.path.join(cfg.IMG_SAVING_DIR, file_name))

            image_room_file = io.BytesIO()
            image.save(image_room_file, 'PNG')
            image_room_file.seek(0)
            image_room_file_request = image_room_file

            final_res_file = io.BytesIO()
            try:
                with requests.post(
                        cfg.SITE_LINK_UPLOAD_FILE,
                        data={"coefficient": coefficient, },
                        headers={'apiToken': token},
                        files={'image': ('image', image_room_file_request, Image.MIME[image.format])},
                        stream=True
                ) as response:
                    if response.status_code == 200:
                        txt = json.loads(response.text)
                        if txt.get("success"):
                            with requests.post(
                                cfg.LOAD_IMAGE_SITE_LINK,
                                data={"image": json.loads(response.text).get('msg')},
                            ) as response2:
                                response2.raw.decode_content = True
                                shutil.copyfileobj(response2.raw, final_res_file)
                                final_res_image = io.BytesIO(response2.content)
                                final_res_image.name = f"{user_id}_{datetime.now()}.png"
                                new_path = os.path.join(cfg.IMG_SAVING_DIR, f"{user_id}_{datetime.now()}.png")
                                Image.open(io.BytesIO(response2.content)).save(new_path)
                                bot.send_document(message.chat.id, final_res_image)
                                bot.send_message(message.chat.id, 'Your Super Resolution Image! :)', reply_markup=start_reply)
                        else:
                            bot.send_message(
                                message.chat.id,
                                f"Got error in server, please try again later! {txt.get('msg')}",
                                reply_markup=start_processing_reply
                            )
                    else:
                        bot.send_message(
                            message.chat.id,
                            f"Got error in server, please try again later! {json.loads(response.text).get('msg')}",
                            reply_markup=start_processing_reply
                        )
            except:
                bot.send_message(
                    message.chat.id,
                    f"Got error in server, please try again later!",
                    reply_markup=start_processing_reply
                )
    else:
        bot.send_message(message.chat.id, 'Please login to the system!', reply_markup=login_reply)


@bot.message_handler(content_types=['document', 'photo'])
def handle_image(message):
    user_id = message.from_user.id

    if user_exist(user_id):
        if message.content_type == 'document':
            file_info = bot.get_file(message.document.file_id)
            downloaded_file = bot.download_file(file_info.file_path)
            image = io.BytesIO(downloaded_file)
            image = Image.open(image)

            user_state[user_id]['image'] = image
            bot.send_message(message.chat.id, 'Image loaded!', reply_markup=start_processing_reply)

        elif message.content_type == 'photo':
            file_info = bot.get_file(message.photo[-1].file_id)
            downloaded_file = bot.download_file(file_info.file_path)
            image = io.BytesIO(downloaded_file)
            image = Image.open(image)

            user_state[user_id]['image'] = image
            bot.send_message(message.chat.id, 'Image loaded!', reply_markup=start_processing_reply)

        else:
            bot.send_message(
                message.chat.id,
                "Something went wrong. Please try again later!",
                reply_markup=start_reply
            )

    else:
        bot.send_message(message.chat.id, "You need to login first!", reply_markup=login_reply)


@bot.message_handler(content_types=['text'])
def check_message(message):
    user_id = message.from_user.id
    msg = str(message.text).strip()

    if user_id in user_state:
        if msg.startswith("email"):
            if 'password' in msg:
                splitted = msg.split(' ')
                if len(splitted) != 2 \
                        or not splitted[0].startswith("email=") \
                        or not splitted[1].startswith("password="):
                    bot.send_message(
                        message.chat.id,
                        'Please send an password and email in right view. '
                        'View of message is "email=qwerty123@qwe.ru password=123qwe"'
                    )
                else:
                    login = splitted[0][len("email="):]
                    password = splitted[1][len("password="):]
                    get_token(message, login, password)
            else:
                bot.send_message(
                    message.chat.id,
                    'Please send an password too. view of message is "email=qwerty123@qwe.ru password=123qwe"'
                )
        elif msg.startswith("coefficient"):
            if msg[-1].isdigit() and int(msg[-1]) in [2, 4, 8]:
                user_state[user_id]['coefficient'] = int(msg[-1])
                bot.send_message(
                    message.chat.id,
                    'Cool! Coefficient was loaded!'
                )
            else:
                bot.send_message(
                    message.chat.id,
                    'Wrong view of the coefficient, please enter it like coefficient=N, N in [2,4,8]'
                )
        else:
            pass
    else:
        bot.send_message(message.chat.id, 'Please login first!', reply_markup=login_reply)


if __name__ == '__main__':
    from time import sleep
    print("Start to running BOT")
    for i in range(3, 0, -1):
        print(f"Bot will run after {i} seconds!")
        sleep(1)
    print("Let's go")
    bot.polling(none_stop=True)

