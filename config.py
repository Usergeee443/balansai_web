import os
from dotenv import load_dotenv

load_dotenv()

class Config:
    # Database Configuration
    DB_HOST = os.getenv('DB_HOST', '146.103.126.207')
    DB_USER = os.getenv('DB_USER', 'phpmyadmin')
    DB_PASSWORD = os.getenv('DB_PASSWORD', '')
    DB_NAME = os.getenv('DB_NAME', 'BalansAiBot')
    DB_PORT = int(os.getenv('DB_PORT', 3306))

    # Telegram Bot Configuration
    TELEGRAM_BOT_TOKEN = os.getenv('TELEGRAM_BOT_TOKEN', '8087310424:AAGn99-GObyu8cU7ADPNTt950K3scdtGXUQ')
    TELEGRAM_BOT_USERNAME = os.getenv('TELEGRAM_BOT_USERNAME', 'BalansAiBot')

    # Flask Configuration
    SECRET_KEY = os.getenv('SECRET_KEY', 'dev-secret-key-change-in-production')
    DEBUG = os.getenv('DEBUG', 'True') == 'True'

    # OTP Configuration
    OTP_EXPIRY_MINUTES = int(os.getenv('OTP_EXPIRY_MINUTES', 5))
    OTP_LENGTH = int(os.getenv('OTP_LENGTH', 6))

    # Trial Period Configuration (days)
    TRIAL_PERIODS = {
        'free': 0,
        'plus': 7,
        'business': 7
    }
