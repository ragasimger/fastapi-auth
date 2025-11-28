from urllib.parse import quote_plus

from decouple import config

DB_NAME = config("DB_NAME")
DB_DRIVER = config("DB_DRIVER", default="postgresql+asyncpg")
DB_HOST = config("DB_HOST")
DB_PORT = config("DB_PORT", default="5432")
DB_USER = config("DB_USER")
DB_PASSWORD_UNFILTERED = config("DB_PASSWORD")
DEBUG = config("DEBUG", default=False, cast=bool)


ATOMIC = config("ATOMIC", default=False, cast=bool)


DB_PASSWORD = quote_plus(DB_PASSWORD_UNFILTERED)
DB_URI = f"{DB_DRIVER}://{DB_USER}:{DB_PASSWORD}@{DB_HOST}:{DB_PORT}/{DB_NAME}"
