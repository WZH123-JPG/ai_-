from flask import Flask
from config import config
from .extensions import db, login_manager, migrate, scheduler, csrf
from .models.user import User, AnonymousUser

def create_app(config_name='development'):
    app = Flask(__name__)
    app.config.from_object(config[config_name])
    
    # 初始化扩展
    db.init_app(app)
    login_manager.init_app(app)
    migrate.init_app(app, db)
    csrf.init_app(app)  # 初始化 CSRF 保护
    
    login_manager.login_view = 'auth.login'
    login_manager.login_message = '请先登录'
    login_manager.login_message_category = 'info'

    # 设置匿名用户类
    login_manager.anonymous_user = AnonymousUser

    with app.app_context():
        # 导入所有模型
        from .models import User, Project, Investment, DailyProfit, Withdrawal, WithdrawConfig, ReferralBonus, Recharge, ReferralRate, ChatSession
        # 设置模型关系
        from .models.relationships import setup_relationships
        setup_relationships()

        # 注册蓝图
        from .routes import main, auth, project, user, admin, agent
        app.register_blueprint(main.bp)
        app.register_blueprint(auth.bp)
        app.register_blueprint(project.bp)
        app.register_blueprint(user.bp)
        app.register_blueprint(admin.bp)
        app.register_blueprint(agent.bp)
        
        # 注册命令
        from .cli import create_admin
        app.cli.add_command(create_admin)

        # 设置定时任务
        from .tasks.profit_calculator import calculate_daily_profits
        scheduler.add_job(calculate_daily_profits, 'cron', hour=0, minute=0)  # 每天0点执行
        scheduler.start()

    return app

@login_manager.user_loader
def load_user(user_id):
    from .models import User
    return User.query.get(int(user_id))