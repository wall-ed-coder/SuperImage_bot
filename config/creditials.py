import os

SITE_LINK = "http://127.0.0.1:5000"

SITE_LINK_UPLOAD_FILE = os.path.join(SITE_LINK, "api/uploadFile")
IMG_SAVING_DIR = "loaded_images"
MAIN_SITE_LINK = os.path.join("http://127.0.0.1:3000", "")
LOAD_IMAGE_SITE_LINK = os.path.join(SITE_LINK, "api/downloadImage")
GET_TOKEN_SITE_LINK = os.path.join(SITE_LINK, "api/getApiToken")

os.makedirs(IMG_SAVING_DIR, exist_ok=True)
