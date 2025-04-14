from flask import Blueprint, render_template, redirect, url_for, flash, request, jsonify, current_app
from flask_login import login_required, current_user
from ..extensions import db, csrf
from ..models import User, Withdrawal, ReferralBonus, Investment, Recharge, WithdrawConfig, ReferralRate, DailyProfit
from datetime import datetime, timedelta
from sqlalchemy import func
import random
import string
import os
from werkzeug.utils import secure_filename
import re

bp = Blueprint('user', __name__, url_prefix='/user')

def save_avatar_image(file):
    """保存头像图片"""
    # 确保上传目录存在
    upload_folder = os.path.join(current_app.root_path, 'static', 'uploads')
    if not os.path.exists(upload_folder):
        os.makedirs(upload_folder)
    
    # 生成安全的文件名
    filename = secure_filename(file.filename)
    # 添加时间戳避免重名
    timestamp = datetime.now().strftime('%Y%m%d%H%M%S')
    filename = f'avatar_{timestamp}_{filename}'
    
    try:
        # 保存文件
        file_path = os.path.join(upload_folder, filename)
        file.save(file_path)
        return filename
    except Exception as e:
        current_app.logger.error(f'保存头像失败: {str(e)}')
        return None

@bp.route('/recharge')
@login_required
def recharge():
    """充值页面"""
    source = request.args.get('source', 'index')  # 默认来源为首页
    return render_template('user/recharge.html', source=source)

@bp.route('/withdraw', methods=['GET', 'POST'])
@login_required
def withdraw():
    """提现"""
    if request.method == 'POST':
        amount = float(request.form.get('amount', 0))
        
        # 获取提现配置
        config = WithdrawConfig.get_config()
        
        # 检查提现时间限制
        if not config.is_withdrawal_allowed():
            flash('当前时间不允许提现，请在工作日的{}至{}之间提现'.format(
                config.start_time, config.end_time), 'error')
            return redirect(url_for('user.withdraw'))
        
        # 检查最低提现金额
        if amount < config.min_amount:
            flash('提现金额不能低于{}'.format(config.min_amount), 'error')
            return redirect(url_for('user.withdraw'))
        
        # 检查余额
        if current_user.balance < amount:
            flash('余额不足', 'error')
            return redirect(url_for('user.withdraw'))
        
        # 计算手续费
        fee = amount * (config.fee_percentage / 100)
        actual_amount = amount - fee
        
        # 创建提现记录
        withdrawal = Withdrawal(
            user_id=current_user.id,
            amount=amount,
            fee=fee,
            actual_amount=actual_amount,
            status='pending'
        )
        
        # 扣除用户余额
        current_user.balance -= amount
        
        try:
            db.session.add(withdrawal)
            db.session.commit()
            flash('提现申请已提交，请等待审核', 'success')
        except Exception as e:
            db.session.rollback()
            flash('提现申请提交失败', 'error')
        
        return redirect(url_for('user.withdraw'))
    
    withdrawals = Withdrawal.query.filter_by(user_id=current_user.id).order_by(Withdrawal.created_at.desc()).all()
    config = WithdrawConfig.get_config()
    return render_template('user/withdraw.html', withdrawals=withdrawals, config=config)

@bp.route('/investments')
@login_required
def investments():
    # 获取用户的所有投资
    user_investments = Investment.query.filter_by(user_id=current_user.id).all()
    return render_template('user/investments.html', investments=user_investments)

@bp.route('/referrals')
@login_required
def referrals():
    # 获取直接推荐的用户（一级）
    direct_referrals = User.query.filter_by(referrer_id=current_user.id).all()
    
    # 计算团队总人数（包括二级）
    total_referrals = len(direct_referrals)
    
    # 获取今日收益
    today_start = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)
    today_earnings = db.session.query(func.sum(ReferralBonus.amount)).filter(
        ReferralBonus.referrer_id == current_user.id,
        ReferralBonus.created_at >= today_start
    ).scalar() or 0.0
    
    # 获取累计收益
    total_earnings = db.session.query(func.sum(ReferralBonus.amount)).filter(
        ReferralBonus.referrer_id == current_user.id
    ).scalar() or 0.0
    
    # 获取推荐人数（一级）
    referral_count = len(direct_referrals)
    
    # 获取分销比例
    level1_rate = ReferralRate.get_rate(1)  # 从数据库获取一级分销比例
    level2_rate = ReferralRate.get_rate(2)  # 从数据库获取二级分销比例
    
    # 构建完整的团队树形结构
    referrals = []
    for level1_user in direct_referrals:
        # 计算一级用户的总投资额
        level1_investment = db.session.query(func.sum(Investment.amount)).filter(
            Investment.user_id == level1_user.id
        ).scalar() or 0.0
        
        # 获取该一级用户发展的二级用户
        level2_users = User.query.filter_by(referrer_id=level1_user.id).all()
        children = []
        
        # 处理二级用户
        for level2_user in level2_users:
            # 计算二级用户的总投资额
            level2_investment = db.session.query(func.sum(Investment.amount)).filter(
                Investment.user_id == level2_user.id
            ).scalar() or 0.0
            
            children.append({
                'username': level2_user.username,
                'created_at': level2_user.created_at,
                'total_investment': level2_investment,
                'avatar_path': level2_user.avatar_path  # 添加头像路径
            })
            total_referrals += 1  # 增加团队总人数
        
        # 添加一级用户及其二级用户信息
        referrals.append({
            'username': level1_user.username,
            'created_at': level1_user.created_at,
            'total_investment': level1_investment,
            'avatar_path': level1_user.avatar_path,  # 添加头像路径
            'children': children  # 包含二级用户列表
        })
    
    return render_template('user/referrals.html',
                         referral_count=referral_count,
                         total_earnings=total_earnings,
                         today_earnings=today_earnings,
                         total_referrals=total_referrals,
                         level1_rate=level1_rate,
                         level2_rate=level2_rate,
                         referrals=referrals)

@bp.route('/profile')
@login_required
def profile():
    # 获取用户投资项目数量
    investments_count = Investment.query.filter_by(user_id=current_user.id).count()
    
    # 获取用户推荐人数
    referral_count = User.query.filter_by(referrer_id=current_user.id).count()
    
    # 获取实际投资收益（从每日收益表中获取）
    investment_earnings = DailyProfit.query.filter_by(
        user_id=current_user.id
    ).with_entities(func.sum(DailyProfit.amount)).scalar() or 0
    
    # 获取推荐奖励总额
    referral_earnings = db.session.query(func.sum(ReferralBonus.amount)).filter(
        ReferralBonus.referrer_id == current_user.id
    ).scalar() or 0.0
    
    total_earnings = investment_earnings + referral_earnings
    
    return render_template('user/profile.html',
                         investments_count=investments_count,
                         referral_count=referral_count,
                         total_earnings=total_earnings)

@bp.route('/earnings')
@login_required
def earnings():
    # 获取投资收益明细
    investments = Investment.query.filter_by(user_id=current_user.id).all()
    
    # 获取今日收益
    today = datetime.utcnow().date()
    # 获取今日投资收益
    today_profits = DailyProfit.query.filter_by(
        user_id=current_user.id,
        date=today
    ).all()
    today_investment_earnings = sum(profit.amount for profit in today_profits)
    
    # 获取今日推荐奖励
    today_start = datetime.utcnow().replace(hour=0, minute=0, second=0, microsecond=0)
    today_referral_earnings = db.session.query(func.sum(ReferralBonus.amount)).filter(
        ReferralBonus.referrer_id == current_user.id,
        ReferralBonus.created_at >= today_start
    ).scalar() or 0.0
    
    # 计算今日总收益（投资收益 + 推荐奖励）
    today_earnings = today_investment_earnings + today_referral_earnings
    
    # 获取累计投资收益
    total_investment_earnings = DailyProfit.query.filter_by(
        user_id=current_user.id
    ).with_entities(func.sum(DailyProfit.amount)).scalar() or 0
    
    # 获取推荐奖励明细
    referral_bonuses = ReferralBonus.query.filter_by(referrer_id=current_user.id)\
        .join(User, User.id == ReferralBonus.user_id)\
        .add_columns(User.username)\
        .all()
    
    # 转换查询结果为字典列表，包含完整信息
    bonus_list = []
    for bonus, username in referral_bonuses:
        bonus_dict = {
            'amount': bonus.amount,
            'created_at': bonus.created_at,
            'referred_username': username
        }
        bonus_list.append(bonus_dict)
    
    referral_earnings = sum(bonus.amount for bonus, _ in referral_bonuses)
    total_earnings = total_investment_earnings + referral_earnings
    
    # 获取最近7天的收益记录
    last_week = datetime.utcnow().date() - timedelta(days=7)
    daily_profits = DailyProfit.query.filter(
        DailyProfit.user_id == current_user.id,
        DailyProfit.date >= last_week
    ).order_by(DailyProfit.date.desc()).all()
    
    return render_template('user/earnings.html',
                         investments=investments,
                         referral_bonuses=bonus_list,
                         today_earnings=today_earnings,
                         total_investment_earnings=total_investment_earnings,
                         referral_earnings=referral_earnings,
                         total_earnings=total_earnings,
                         daily_profits=daily_profits)

@bp.route('/recharge/create', methods=['POST'])
@login_required
def create_recharge():
    """创建充值订单"""
    try:
        data = request.get_json()
        if not data:
            current_app.logger.error('未接收到JSON数据')
            return jsonify({'code': 400, 'message': '请求数据格式错误'})
            
        amount = float(data.get('amount', 0))
        payment_method = data.get('payment_method')
        
        current_app.logger.info(f'接收到充值请求: amount={amount}, payment_method={payment_method}')
        
        if amount <= 0:
            return jsonify({'code': 400, 'message': '充值金额必须大于0'})
            
        if payment_method not in ['alipay', 'wechat', 'bank']:
            return jsonify({'code': 400, 'message': '不支持的支付方式'})
            
        # 生成支付流水号
        payment_no = ''.join(random.choices(string.ascii_uppercase + string.digits, k=16))
        
        # 创建充值记录
        recharge = Recharge(
            user_id=current_user.id,
            amount=amount,
            payment_method=payment_method,
            payment_no=payment_no,
            status='pending',  # 设置为待审核状态
            remarks='用户发起充值'
        )
        
        try:
            db.session.add(recharge)
            db.session.commit()
            current_app.logger.info(f'充值记录创建成功: id={recharge.id}')
            
            return jsonify({
                'code': 200,
                'message': '充值申请已提交，请等待审核',
                'data': {
                    'id': recharge.id,
                    'amount': recharge.amount,
                    'status': recharge.status,
                    'payment_no': recharge.payment_no,
                    'payment_method': recharge.payment_method
                }
            })
            
        except Exception as e:
            db.session.rollback()
            current_app.logger.error(f'数据库操作失败: {str(e)}')
            return jsonify({'code': 500, 'message': '充值失败，请重试'})
        
    except ValueError as e:
        current_app.logger.error(f'数据格式错误: {str(e)}')
        return jsonify({'code': 400, 'message': '请输入有效的充值金额'})
    except Exception as e:
        current_app.logger.error(f'充值处理异常: {str(e)}')
        return jsonify({'code': 500, 'message': '充值失败，请重试'})

@bp.route('/create_withdrawal', methods=['POST'])
@login_required
@csrf.exempt  # 如果使用自定义的 CSRF 处理
def create_withdrawal():
    """创建提现申请"""
    try:
        # 验证 CSRF 令牌
        csrf_token = request.form.get('csrf_token')
        if not csrf_token:
            return jsonify({'code': 403, 'message': 'CSRF 验证失败'})

        amount = float(request.form.get('amount', 0))
        bank_name = request.form.get('bank_name')
        bank_card_number = request.form.get('bank_account')  # 从表单获取的是bank_account
        bank_account_name = request.form.get('account_name')  # 从表单获取的是account_name
        
        if not all([amount, bank_name, bank_card_number, bank_account_name]):
            return jsonify({'code': 400, 'message': '请填写完整的提现信息'})
        
        # 获取提现配置
        config = WithdrawConfig.get_config()
        
        # 检查提现时间限制
        if not config.is_withdrawal_allowed():
            return jsonify({
                'code': 400, 
                'message': f'当前时间不允许提现，请在{config.allowed_days_display}的{config.start_time}至{config.end_time}之间提现'
            })
        
        # 检查最低提现金额
        if amount < config.min_amount:
            return jsonify({'code': 400, 'message': f'提现金额不能低于{config.min_amount}元'})
        
        # 检查余额
        if current_user.balance < amount:
            return jsonify({'code': 400, 'message': '余额不足'})
        
        # 计算手续费和实际到账金额
        fee = amount * (config.fee_percentage / 100)
        actual_amount = amount - fee
        
        # 创建提现记录
        withdrawal = Withdrawal(
            user_id=current_user.id,
            amount=amount,
            fee=fee,
            actual_amount=actual_amount,
            bank_name=bank_name,
            bank_card_number=bank_card_number,
            bank_account_name=bank_account_name,
            status='pending'
        )
        
        # 扣除用户余额
        current_user.balance -= amount
        
        db.session.add(withdrawal)
        db.session.commit()
        
        return jsonify({'code': 200, 'message': '提现申请已提交，请等待审核'})
        
    except Exception as e:
        db.session.rollback()
        current_app.logger.error(f'提现申请失败: {str(e)}')
        return jsonify({'code': 500, 'message': '提现申请提交失败，请重试'})

@bp.route('/recharge_list')
@login_required
def recharge_list():
    """充值记录页面"""
    # 获取筛选参数
    payment_method = request.args.get('payment_method', '')
    start_date = request.args.get('start_date', '')
    end_date = request.args.get('end_date', '')

    # 构建查询
    query = Recharge.query.filter_by(user_id=current_user.id)
    
    # 应用筛选条件
    if payment_method:
        query = query.filter_by(payment_method=payment_method)
    
    if start_date:
        try:
            start_datetime = datetime.strptime(start_date, '%Y-%m-%d')
            query = query.filter(Recharge.created_at >= start_datetime)
        except ValueError:
            flash('开始日期格式无效', 'error')
    
    if end_date:
        try:
            # 将结束日期设置为当天的23:59:59
            end_datetime = datetime.strptime(end_date, '%Y-%m-%d') + timedelta(days=1) - timedelta(seconds=1)
            query = query.filter(Recharge.created_at <= end_datetime)
        except ValueError:
            flash('结束日期格式无效', 'error')

    # 按创建时间倒序排序
    recharges = query.order_by(Recharge.created_at.desc()).all()
    
    return render_template('user/recharge_list.html', recharges=recharges)

@bp.route('/withdrawals')
@login_required
def withdrawals():
    """提现记录页面"""
    # 获取筛选参数
    payment_method = request.args.get('payment_method', '')
    start_date = request.args.get('start_date', '')
    end_date = request.args.get('end_date', '')

    # 构建查询
    query = Withdrawal.query.filter_by(user_id=current_user.id)
    
    # 支付方式映射
    payment_method_map = {
        'alipay': '支付宝',
        'wechat': '微信',
        'bank': '银行卡'
    }
    
    # 应用筛选条件
    if payment_method and payment_method in payment_method_map:
        query = query.filter_by(bank_name=payment_method_map[payment_method])
    
    if start_date:
        try:
            start_datetime = datetime.strptime(start_date, '%Y-%m-%d')
            query = query.filter(Withdrawal.created_at >= start_datetime)
        except ValueError:
            flash('开始日期格式无效', 'error')
    
    if end_date:
        try:
            # 将结束日期设置为当天的23:59:59
            end_datetime = datetime.strptime(end_date, '%Y-%m-%d') + timedelta(days=1) - timedelta(seconds=1)
            query = query.filter(Withdrawal.created_at <= end_datetime)
        except ValueError:
            flash('结束日期格式无效', 'error')

    # 按创建时间倒序排序
    withdrawals = query.order_by(Withdrawal.created_at.desc()).all()
    
    return render_template('user/withdrawals.html', withdrawals=withdrawals)

@bp.route('/settings')
@login_required
def settings():
    """设置页面"""
    return render_template('user/settings.html')

@bp.route('/update_username', methods=['POST'])
@login_required
def update_username():
    """处理用户名修改"""
    new_username = request.form.get('new_username')
    
    if not new_username:
        flash('请输入新的用户名', 'error')
        return redirect(url_for('user.edit_username'))
    
    # 验证用户名长度
    if len(new_username) < 3 or len(new_username) > 20:
        flash('用户名长度必须在3-20个字符之间', 'error')
        return redirect(url_for('user.edit_username'))
    
    # 验证用户名格式
    if not re.match(r'^[a-zA-Z0-9_]+$', new_username):
        flash('用户名只能包含字母、数字和下划线', 'error')
        return redirect(url_for('user.edit_username'))
    
    # 检查用户名是否已被使用
    if User.query.filter(User.username == new_username, User.id != current_user.id).first():
        flash('该用户名已被使用', 'error')
        return redirect(url_for('user.edit_username'))
    
    try:
        current_user.username = new_username
        db.session.commit()
        flash('用户名修改成功', 'success')
        return redirect(url_for('user.settings'))
    except Exception as e:
        db.session.rollback()
        flash('用户名修改失败，请稍后重试', 'error')
        return redirect(url_for('user.edit_username'))

@bp.route('/update_password', methods=['POST'])
@login_required
def update_password():
    """更新密码"""
    current_password = request.form.get('current_password')
    new_password = request.form.get('new_password')
    confirm_password = request.form.get('confirm_password')
    
    if not current_password or not new_password or not confirm_password:
        flash('所有密码字段都必须填写', 'error')
        return redirect(url_for('user.edit_password'))
    
    if new_password != confirm_password:
        flash('新密码和确认密码不匹配', 'error')
        return redirect(url_for('user.edit_password'))
    
    if not current_user.verify_password(current_password):
        flash('当前密码不正确', 'error')
        return redirect(url_for('user.edit_password'))
    
    current_user.password = new_password
    db.session.commit()
    flash('密码更新成功', 'success')
    return redirect(url_for('user.settings'))

@bp.route('/edit_username')
@login_required
def edit_username():
    """修改用户名页面"""
    return render_template('user/edit_username.html')

@bp.route('/edit_password')
@login_required
def edit_password():
    """修改密码页面"""
    return render_template('user/edit_password.html')

@bp.route('/verify_identity')
@login_required
def verify_identity():
    """实名认证页面"""
    return render_template('user/verify_identity.html')

@bp.route('/payment_settings')
@login_required
def payment_settings():
    """支付设置页面"""
    return render_template('user/payment_settings.html')

@bp.route('/notification_settings')
@login_required
def notification_settings():
    """通知设置页面"""
    return render_template('user/notification_settings.html')

@bp.route('/update_avatar', methods=['POST'])
@login_required
def update_avatar():
    """更新用户头像"""
    if 'avatar' not in request.files:
        flash('没有选择文件', 'error')
        return redirect(url_for('user.profile'))
    
    file = request.files['avatar']
    if file.filename == '':
        flash('没有选择文件', 'error')
        return redirect(url_for('user.profile'))
    
    # 检查文件类型
    allowed_extensions = {'png', 'jpg', 'jpeg', 'gif'}
    if not ('.' in file.filename and file.filename.rsplit('.', 1)[1].lower() in allowed_extensions):
        flash('不支持的文件类型', 'error')
        return redirect(url_for('user.profile'))
    
    # 检查文件大小（限制为5MB）
    if len(file.read()) > 5 * 1024 * 1024:  # 5MB in bytes
        flash('文件大小不能超过5MB', 'error')
        return redirect(url_for('user.profile'))
    
    # 重置文件指针
    file.seek(0)
    
    try:
        # 删除旧头像
        if current_user.avatar_path and current_user.avatar_path != 'default-avatar.jpg':
            old_avatar_path = os.path.join(current_app.root_path, 'static', 'uploads', current_user.avatar_path)
            if os.path.exists(old_avatar_path):
                os.remove(old_avatar_path)
        
        # 保存新头像
        filename = save_avatar_image(file)
        if filename:
            current_user.avatar_path = filename
            db.session.commit()
            flash('头像更新成功', 'success')
        else:
            flash('头像上传失败', 'error')
    except Exception as e:
        db.session.rollback()
        flash('头像更新失败', 'error')
    
    return redirect(url_for('user.profile'))

# ... 其他现有的路由保持不变 ...