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
    return user_id in user_state and user_state[user_id]['token'] is not None


bot = telebot.TeleBot(TOKEN)
super_image_url = SITE_LINK_UPLOAD_FILE

keyboard2 = types.ReplyKeyboardMarkup(True)
keyboard2.row('/start_processing')

keyboard3 = types.ReplyKeyboardMarkup(True)
keyboard3.row('/login')

keyboard4 = types.ReplyKeyboardMarkup(True)
keyboard4.row('/start')

user_state = {}


@bot.message_handler(content_types=['text'])
def coefs_message(message):
    user_id = message.from_user.id
    if not user_exist(user_id, user_state):
        smth_went_wrong(message.chat.id)
    msg_text = message.text
    if 'coefficient' in msg_text:
        if msg_text.startswith('coefficient='):
            if str(msg_text[-1]).isdigit() and int(msg_text[-1]) in [2, 4, 8]:
                user_state[user_id]['coefficient'] = int(msg_text[-1])
                if user_state[user_id]['image']:
                    bot.send_message(
                        message.chat.id,
                        'Cool! We can improve image! Please select /start_processing',
                        reply_markup=keyboard2
                    )
                else:
                    bot.send_message(
                        message.chat.id,
                        'Cool! Now we need to get an image! Please upload it by image or document!',
                        reply_markup=keyboard2
                    )
            else:
                bot.send_message(
                    message.chat.id,
                    'Please select right coefficient: '
                    'you can do it just wrote coefficient=2, coefficient=4 or coefficient=8',
                    reply_markup=keyboard2
                )
    else:
        bot.send_message(
            message.chat.id,
            'Please load right coefficient: you can do it just wrote coefficient=2, coefficient=4 or coefficient=8',
            reply_markup=keyboard2
        )


@bot.message_handler(commands=['start'])
def start_message(message):
    user_id = message.from_user.id

    if user_exist(user_id, user_state):
        user_state[user_id]['image'] = None
        user_state[user_id]['coefficient'] = None

        bot.send_message(
            message.chat.id,
            'We can start! Please load coefficient of improving image by '
            '/coefficient=2 or /coefficient=4 or /coefficient=8 and upload an image by image or document!',
            reply_markup=keyboard2
        )
    else:
        bot.send_message(
            message.chat.id,
            'Hello! This is Super Image Bot, it helps you to get high resolution image from low resolution, enjoy! '
            f'Before we start, you need to registrate in {SITE_LINK}. Thanks!',
            reply_markup=keyboard3
        )


def smth_went_wrong(chat_id, msg=None):
    bot.send_message(chat_id, msg if msg else 'Something went wrong!, Please tap /start', reply_markup=keyboard4)


@bot.message_handler(commands=['help'])
def help_message(message):
    help_message_str = f"""
    This bot will help you to get SR images from LR.
    To start you need to select /start, then select /login, login to the bot(or create an account on {SITE_LINK}, 
    then text 'upload image', upload image by image or file and select 'Start processing...'
    """
    bot.send_message(message.chat.id, help_message_str, reply_markup=keyboard4)


@bot.message_handler(commands=['login'])
def login_message(message):
    user_id = message.from_user.id

    user_state[user_id] = {
        'id': user_id,
        'image': None,
        'token': 1,
        'coefficient': None,
    }
    # todo
    # добавить загрузку coefficient и чтобы везде он проверялся
    # получить токен по апи
    bot.send_message(message.chat.id, 'Cool! We can start!', reply_markup=keyboard4)


@bot.message_handler(commands=['start_processing'])
def check_message(message):
    user_id = message.from_user.id

    if not user_exist(user_id, user_state):
        smth_went_wrong(message.chat.id)
    else:
        if user_state[user_id]['image'] is None:
            bot.send_message(message.chat.id, 'Please load image')
        elif user_state[user_id]['coefficient'] is None:
            bot.send_message(message.chat.id, 'Please choose coefficient by /coefficient=2/4/8', reply_markup=keyboard2)
        else:
            bot.send_message(message.chat.id, 'Please wait....', reply_markup=keyboard4)

            image = user_state[user_id]['image']
            coefficient = user_state[user_id]['coefficient']
            token = user_state[user_id]['token']

            image.save(os.path.join(IMG_SAVING_DIR, f"{user_id}_{datetime.now()}.png"))

            image_room_file = io.BytesIO()
            image.save(image_room_file, 'PNG')
            image_room_file.seek(0)
            image_room_file_request = image_room_file

            final_res_file = io.BytesIO()

            with requests.post(
                    super_image_url,
                    data={"coefficient": coefficient, 'token': token},
                    files={'image': ('image', image_room_file_request, Image.MIME[image.format])},
                    stream=True
            ) as response:
                if response.status_code == 200:
                    response.raw.decode_content = True
                    shutil.copyfileobj(response.raw, final_res_file)
                    final_res_image = Image.open(final_res_file)
                    bot.send_photo(message.chat.id, final_res_image)

                    bot.send_message(message.chat.id, 'Your room with replaced walls', reply_markup=keyboard4)
                else:
                    smth_went_wrong(message.chat.id, "Got error in server, please try again later!")


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

            user_state[user_id]['image'] = image
            bot.send_message(message.chat.id, 'Image loaded!', reply_markup=keyboard2)

        elif message.content_type == 'photo':
            file_info = bot.get_file(message.photo[-1].file_id)
            downloaded_file = bot.download_file(file_info.file_path)
            image = io.BytesIO(downloaded_file)
            image = Image.open(image)

            user_state[user_id]['image'] = image
            bot.send_message(message.chat.id, 'Image loaded!', reply_markup=keyboard2)

        else:
            smth_went_wrong(message.chat.id)


if __name__ == '__main__':
    bot.polling(none_stop=True)
