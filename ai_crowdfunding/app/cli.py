import click
from flask.cli import with_appcontext
from .models import User
from . import db

@click.command('create-admin')
@click.option('--username', prompt='管理员用户名', help='管理员用户名')
@click.option('--password', prompt=True, hide_input=True, confirmation_prompt=True, help='管理员密码')
@click.option('--email', prompt='管理员邮箱', help='管理员邮箱')
@with_appcontext
def create_admin(username, password, email):
    """创建管理员用户"""
    try:
        # 检查用户是否已存在
        if User.query.filter_by(username=username).first():
            click.echo('用户名已存在')
            return
        if User.query.filter_by(email=email).first():
            click.echo('邮箱已被注册')
            return
        
        # 创建管理员用户
        admin = User(
            username=username,
            email=email,
            is_admin=True
        )
        admin.set_password(password)
        admin.generate_referral_code()
        
        # 保存到数据库
        db.session.add(admin)
        db.session.commit()
        
        click.echo('管理员创建成功')
    except Exception as e:
        click.echo(f'创建管理员失败: {e}') 