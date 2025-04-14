from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager
from flask_migrate import Migrate
from flask_wtf.csrf import CSRFProtect
from apscheduler.schedulers.background import BackgroundScheduler

# 创建扩展实例
db = SQLAlchemy()
login_manager = LoginManager()
migrate = Migrate()
scheduler = BackgroundScheduler()
csrf = CSRFProtect()

# 配置登录管理器
login_manager.login_view = 'auth.login'
login_manager.login_message = '请先登录'
login_manager.login_message_category = 'info' 