import io
import os
import shutil
from datetime import datetime

import requests
import telebot
from PIL import Image
from telebot import types

from config.sec_config import TOKEN
from config.creditials import SITE_LINK_UPLOAD_FILE, IMG_SAVING_DIR, SITE_LINK


def user_exist(user_id, user_state):
    return user_id in user_state


bot = telebot.TeleBot(TOKEN)
super_image_url = SITE_LINK_UPLOAD_FILE

keyboard1 = types.ReplyKeyboardMarkup(True)
keyboard1.row('Upload Image')

keyboard3 = types.ReplyKeyboardMarkup(True)
keyboard3.row('/login')

keyboard2 = types.ReplyKeyboardMarkup(True)
keyboard2.row('Start processing...')

keyboard4 = types.ReplyKeyboardMarkup(True)
keyboard4.row('/start')

user_state = {}


@bot.message_handler(commands=['start'])
def start_message(message):
    user_id = message.from_user.id

    if user_exist(user_id, user_state):
        user_state[user_id]['image'] = None
        user_state[user_id]['status'] = None
        user_state[user_id]['coefficient'] = None

        bot.send_message(
            message.chat.id,
            'We can start!',
            reply_markup=keyboard1
        )
    else:
        bot.send_message(
            message.chat.id,
            'Hello! This is Super Image Bot, it helps you to get high resolution image from low resolution, enjoy! '
            f'Before we start, you need to registrate in {SITE_LINK}. Thanks!',
            reply_markup=keyboard3
        )


def smth_went_wrong(chat_id):
    bot.send_message(chat_id, 'Something went wrong!, Please tap /start', reply_markup=keyboard4)


@bot.message_handler(commands=['help'])
def help_message(message):
    help_message_str = f"""
    This bot will help you to get SR images from LR.
    To start you need to select /start, then select /login, login to the bot(or create an account on {SITE_LINK}, 
    then text 'upload image', upload image by image or file and select 'Start processing...'
    """
    bot.send_message(message.chat.id, help_message_str, reply_markup=keyboard1)


@bot.message_handler(commands=['login'])
def login_message(message):
    user_id = message.from_user.id

    user_state[user_id] = {
        'id': user_id,
        'image': None,
        'status': None,
        'token': None,
        'coefficient': None,
    }
    # todo
    # добавить загрузку coefficient и чтобы везде он проверялся
    # получить токен по апи

    pass


@bot.message_handler(content_types=['text'])
def check_message(message):
    user_id = message.from_user.id

    if not user_exist(user_id, user_state):
        smth_went_wrong(message.chat.id)
    else:
        if message.text == 'Upload Image':
            bot.send_message(message.chat.id, 'Please load image')
            user_state[user_id]['status'] = 'upload image'
        elif message.text == 'Start processing...':
            bot.send_message(message.chat.id, 'Please wait....', reply_markup=keyboard4)

            if user_state[user_id]['image'] is not None:
                image_room = user_state[user_id]['image']

                image_room.save(os.path.join(IMG_SAVING_DIR, f"{user_id}_{datetime.now()}.png"))

                image_room_file = io.BytesIO()
                image_room.save(image_room_file, 'PNG')
                image_room_file.seek(0)
                image_room_file_request = image_room_file

                final_res_file = io.BytesIO()

                with requests.post(
                        super_image_url,
                        # data={"coefficient": coefficient},
                        files={'image': ('image', image_room_file_request, Image.MIME[image_room.format])},
                        stream=True
                ) as response:
                    response.raw.decode_content = True
                    shutil.copyfileobj(response.raw, final_res_file)
                final_res_image = Image.open(final_res_file)
                bot.send_photo(message.chat.id, final_res_image)

                bot.send_message(message.chat.id, 'Your room with replaced walls', reply_markup=keyboard4)
            else:
                bot.send_message(message.chat.id, 'Please try other Images!', reply_markup=keyboard4)
        else:
            bot.send_message(message.chat.id, 'Please try other Images!', reply_markup=keyboard4)


@bot.message_handler(content_types=['document', 'photo'])
def handle_image(message):
    user_id = message.from_user.id

    if not user_exist(user_id, user_state):
        smth_went_wrong(message.chat.id)
    else:
        if message.content_type == 'document':
            file_info = bot.get_file(message.document.file_id)
            downloaded_file = bot.download_file(file_info.file_path)
            image = io.BytesIO(downloaded_file)
            image = Image.open(image)

            if user_state[user_id]['status'] == 'upload image':
                user_state[user_id]['image'] = image
                user_state[user_id]['status'] = None
                bot.send_message(message.chat.id, 'Image loaded!', reply_markup=keyboard2)
            else:
                smth_went_wrong(message.chat.id)

        elif message.content_type == 'photo':
            file_info = bot.get_file(message.photo[-1].file_id)
            downloaded_file = bot.download_file(file_info.file_path)
            image = io.BytesIO(downloaded_file)
            image = Image.open(image)

            if user_state[user_id]['status'] == 'upload image':
                user_state[user_id]['image'] = image
                user_state[user_id]['status'] = None
                bot.send_message(message.chat.id, 'Image loaded!', reply_markup=keyboard2)
            else:
                smth_went_wrong(message.chat.id)
        else:
            smth_went_wrong(message.chat.id)


if __name__ == '__main__':
    bot.polling(none_stop=True)
