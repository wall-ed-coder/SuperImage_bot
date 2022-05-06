import io
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
        user_state[user_id]['coefficient'] = None

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

    bot.send_message(
        message.chat.id,
        'Please pass login and password like "login=qwerty123@qwe password=123qwe"!',
        reply_markup=login_reply
    )
    # todo token

    user_state[user_id] = {
        'id': user_id,
        'image': None,
        'token': None,
        'coefficient': None,
    }
    # todo
    # получить токен по апи


def get_token(message, login, password):
    user_id = message.from_user.id
    # todo
    # получить токен по апи

    user_state[user_id]['token'] = 1

    bot.send_message(message.chat.id, 'Cool! We can start!', reply_markup=start_reply)


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

            image.save(os.path.join(cfg.IMG_SAVING_DIR, f"{user_id}_{datetime.now()}.png"))

            image_room_file = io.BytesIO()
            image.save(image_room_file, 'PNG')
            image_room_file.seek(0)
            image_room_file_request = image_room_file

            final_res_file = io.BytesIO()

            with requests.post(
                    cfg.SITE_LINK_UPLOAD_FILE,
                    data={"coefficient": coefficient, 'token': token},
                    files={'image': ('image', image_room_file_request, Image.MIME[image.format])},
                    stream=True
            ) as response:
                if response.status_code == 200:
                    response.raw.decode_content = True
                    shutil.copyfileobj(response.raw, final_res_file)
                    final_res_image = Image.open(final_res_file)
                    bot.send_photo(message.chat.id, final_res_image)

                    bot.send_message(message.chat.id, 'Your room with replaced walls', reply_markup=start_reply)
                else:
                    bot.send_message(
                        message.chat.id,
                        "Got error in server, please try again later!",
                        reply_markup=start_reply
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
        if msg.startswith("login"):
            if 'password' in msg:
                splitted = msg.split(' ')
                if len(splitted) != 2 \
                        or not splitted[0].startswith("login=") \
                        or not splitted[1].startswith("password="):
                    bot.send_message(
                        message.chat.id,
                        'Please send an password and login in right view. '
                        'View of message is "login=qwerty123@qwe password=123qwe"'
                    )
                else:
                    login = splitted[0][len("login="):]
                    password = splitted[0][len("password="):]
                    get_token(message, login, password)
            else:
                bot.send_message(
                    message.chat.id,
                    'Please send an password too. view of message is "login=qwerty123@qwe password=123qwe"'
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
    bot.polling(none_stop=True)
