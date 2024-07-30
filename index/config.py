import os

class Config:
   SECRET_KEY = str(os.environ.get('SECRET_KEY','99e6db49de2bba884f87152e330539b4' ))
   SQLALCHEMY_DATABASE_URI =os.environ.get('SQLALCHEMY_DATABASE_URI ','sqlite:///site.db')
   MAIL_SERVER ='smtp.googlemail.com'
   MAIL_PORT = 587
   MAIL_USE_TLS =True
   MAIL_USERNAME = os.environ.get('EMAIL_USER')
   MAIL_PASSWORD = os.environ.get('EMAIL_PASS')
   MAIL_DEFAULT_SENDER = 'mail4project9876@gmail.com'