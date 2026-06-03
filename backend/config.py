import os

MYSQL_HOST = os.getenv("MYSQL_HOST", "localhost")
MYSQL_USER = os.getenv("MYSQL_USER", "root")
MYSQL_PASSWORD = os.getenv("MYSQL_PASSWORD", "123456")
MYSQL_DB = os.getenv("MYSQL_DB", "smarthealth")

# Use a strong fallback to avoid weak-key JWT warnings in local environments.
SECRET_KEY = os.getenv("SECRET_KEY", "smarthealth-local-dev-secret-key-min-32-bytes")
