from flask import Blueprint, render_template, redirect, url_for, flash, request
from flask_login import login_user, logout_user, login_required, current_user
from werkzeug.security import generate_password_hash
from .. import db
from ..models import User, ReferralBonus
import random
import string

bp = Blueprint('auth', __name__)

def generate_referral_code():
    return ''.join(random.choices(string.ascii_uppercase + string.digits, k=8))

@bp.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        username = request.form['username']
        email = request.form['email']
        password = request.form['password']
        referral_code = request.form.get('referral_code')

        if User.query.filter_by(username=username).first():
            flash('用户名已存在')
            return redirect(url_for('auth.register'))
        
        if User.query.filter_by(email=email).first():
            flash('邮箱已被注册')
            return redirect(url_for('auth.register'))

        user = User(username=username, email=email)
        user.password = password
        user.referral_code = generate_referral_code()

        if referral_code:
            referrer = User.query.filter_by(referral_code=referral_code).first()
            if referrer:
                user.referrer_id = referrer.id

        db.session.add(user)
        db.session.commit()

        # 在用户创建后创建推荐奖励记录
        if referral_code and referrer:
            bonus = ReferralBonus(
                referrer_id=referrer.id,
                user_id=user.id,
                amount=50.0,  # 设置推荐奖励金额
                level=1,      # 一级推荐
                rate=0.1,     # 10%的奖励比例
                status='pending'  # 待发放状态
            )
            db.session.add(bonus)
            db.session.commit()
        
        flash('注册成功！')
        return redirect(url_for('auth.login'))

    return render_template('auth/register.html')

@bp.route('/login', methods=['GET', 'POST'])
def login():
    # 如果用户已登录，重定向到首页
    if current_user.is_authenticated:
        return redirect(url_for('main.index'))

    # 检查是否是管理员登录页面
    is_admin = request.args.get('admin', '0') == '1'
    
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        user = User.query.filter_by(username=username).first()

        if user and user.verify_password(password):
            # 检查用户是否被禁用
            if not user.is_active:
                flash('您的账户已被禁用，请联系管理员', 'error')
                return redirect(url_for('auth.login', admin=is_admin))
                
            # 如果是管理员登录页面，检查用户是否是管理员
            if is_admin and not user.is_admin:
                flash('您不是管理员，无法登录管理后台', 'error')
                return redirect(url_for('auth.login', admin=1))
            
            login_user(user)
            
            # 获取next参数，如果没有则根据用户类型跳转
            next_page = request.args.get('next')
            if next_page and next_page.startswith('/admin/') and not user.is_admin:
                next_page = None
            
            if next_page:
                return redirect(next_page)
            elif user.is_admin and is_admin:
                return redirect(url_for('admin.dashboard'))
            else:
                return redirect(url_for('main.index'))
        
        flash('用户名或密码错误', 'error')
    
    # 根据是否是管理员登录使用不同的模板
    template = 'auth/admin_login.html' if is_admin else 'auth/login.html'
    return render_template(template)

@bp.route('/logout')
@login_required
def logout():
    is_admin = request.args.get('admin', '0') == '1'
    logout_user()
    if is_admin:
        return redirect(url_for('auth.login', admin=1))
    return redirect(url_for('main.index'))