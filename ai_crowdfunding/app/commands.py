import click
from flask.cli import with_appcontext
from . import db
from .models import User

@click.command('reset-password')
@click.argument('username')
@click.argument('new_password')
@with_appcontext
def reset_password_command(username, new_password):
    """重置用户密码"""
    user = User.query.filter_by(username=username).first()
    if user is None:
        click.echo(f'用户 {username} 不存在')
        return
    
    user.set_password(new_password)
    db.session.commit()
    click.echo(f'已重置用户 {username} 的密码')