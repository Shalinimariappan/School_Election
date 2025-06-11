import os
from dotenv import load_dotenv

load_dotenv()

class Config:
    SECRET_KEY = os.getenv('SECRET_KEY') or 'your-secret-key-123'
    SQLALCHEMY_DATABASE_URI = 'sqlite:///election.db'
    SQLALCHEMY_TRACK_MODIFICATIONS = False