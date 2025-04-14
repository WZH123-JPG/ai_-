from flask import Blueprint, render_template, redirect, url_for, flash, request, session, jsonify, abort, send_file, current_app
from functools import wraps
from app.models.user import User
from app.models import Project, Investment, DailyProfit, ReferralBonus, Withdrawal, WithdrawConfig, Recharge, ReferralRate, Role, ChatModels
from app import db
from datetime import datetime, timedelta
from sqlalchemy import func
from werkzeug.security import generate_password_hash
from app.models.investment import Investment
from flask import g
import os
from werkzeug.utils import secure_filename
import pandas as pd
import io
from sqlalchemy.orm import joinedload
from flask_wtf import FlaskForm
from wtforms import StringField, PasswordField, SubmitField
from wtforms.validators import DataRequired
from app.forms.ai_model import AIModelForm

bp = Blueprint('admin', __name__, url_prefix='/admin')

# 允许的图片文件扩展名
ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif'}

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

def save_project_image(file):
    """保存项目图片"""
    if file and allowed_file(file.filename):
        filename = secure_filename(file.filename)
        # 生成唯一文件名
        unique_filename = f"{datetime.now().strftime('%Y%m%d%H%M%S')}_{filename}"
        # 确保上传目录存在
        upload_folder = os.path.join(current_app.root_path, 'static', 'uploads')
        if not os.path.exists(upload_folder):
            os.makedirs(upload_folder)
        # 保存文件
        file.save(os.path.join(upload_folder, unique_filename))
        return unique_filename
    return None

def admin_session_required(f):
    """管理员会话验证装饰器"""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'admin_id' not in session:
            flash('请先登录', 'error')
            return redirect(url_for('admin.login'))
        admin = User.query.get(session['admin_id'])
        if not admin or not admin.can_access_backend():
            session.pop('admin_id', None)
            flash('无效的管理员会话', 'error')
            return redirect(url_for('admin.login'))
        return f(*args, **kwargs)
    return decorated_function

def permission_required(permission_code):
    """权限检查装饰器"""
    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            if 'admin_id' not in session:
                flash('请先登录', 'error')
                return redirect(url_for('admin.login'))
            admin = User.query.get(session['admin_id'])
            if not admin or not admin.has_permission(permission_code):
                flash('没有权限执行此操作', 'error')
                return redirect(url_for('admin.index'))
            return f(*args, **kwargs)
        return decorated_function
    return decorator

def role_required(*roles):
    """角色检查装饰器"""
    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            if 'admin_id' not in session:
                flash('请先登录', 'error')
                return redirect(url_for('admin.login'))
            admin = User.query.get(session['admin_id'])
            if not admin or not any(admin.has_role(role) for role in roles):
                flash('没有权限访问此页面', 'error')
                return redirect(url_for('admin.dashboard'))
            return f(*args, **kwargs)
        return decorated_function
    return decorator

@bp.route('/')
@admin_session_required
def index():
    """管理后台首页"""
    return redirect(url_for('admin.dashboard'))

class AdminLoginForm(FlaskForm):
    """管理员登录表单"""
    username = StringField('用户名', validators=[DataRequired()])
    password = PasswordField('密码', validators=[DataRequired()])
    submit = SubmitField('登录')

class AddAgentForm(FlaskForm):
    """添加代理表单"""
    username = StringField('用户名', validators=[DataRequired()])
    password = PasswordField('密码', validators=[DataRequired()])
    email = StringField('邮箱', validators=[DataRequired()])
    submit = SubmitField('添加')

class CreateProjectForm(FlaskForm):
    """创建项目表单"""
    name = StringField('项目名称', validators=[DataRequired()])
    description = StringField('项目描述', validators=[DataRequired()])
    target_amount = StringField('目标金额', validators=[DataRequired()])
    share_price = StringField('份额单价', validators=[DataRequired()])
    total_shares = StringField('总份额', validators=[DataRequired()])
    daily_roi = StringField('日收益率', validators=[DataRequired()])
    end_date = StringField('结束日期', validators=[DataRequired()])
    submit = SubmitField('创建')

class EditProjectForm(FlaskForm):
    """编辑项目表单"""
    name = StringField('项目名称', validators=[DataRequired()])
    description = StringField('项目描述', validators=[DataRequired()])
    target_amount = StringField('目标金额', validators=[DataRequired()])
    share_price = StringField('份额单价', validators=[DataRequired()])
    total_shares = StringField('总份额', validators=[DataRequired()])
    daily_roi = StringField('日收益率', validators=[DataRequired()])
    end_date = StringField('结束日期', validators=[DataRequired()])
    submit = SubmitField('保存修改')

@bp.route('/login', methods=['GET', 'POST'])
def login():
    """管理员登录"""
    if 'admin_id' in session:
        return redirect(url_for('admin.index'))
    
    form = AdminLoginForm()
    if form.validate_on_submit():
        user = User.query.filter_by(username=form.username.data).first()
        
        if user and user.verify_password(form.password.data):
            # 检查用户是否被禁用
            if not user.is_active:
                flash('您的账户已被禁用，请联系管理员', 'error')
                return redirect(url_for('admin.login'))
            
            # 检查是否有后台访问权限
            if not user.can_access_backend():
                flash('您没有后台访问权限', 'error')
                return redirect(url_for('admin.login'))
            
            # 使用独立的管理员会话，不影响用户端登录状态
            session['admin_id'] = user.id
            flash('登录成功', 'success')
            return redirect(url_for('admin.index'))
        else:
            flash('用户名或密码错误，或者没有后台访问权限', 'error')
    
    return render_template('admin/login.html', form=form)

@bp.route('/logout')
@admin_session_required
def logout():
    """管理员退出登录"""
    # 只清除管理员会话，不影响用户端登录状态
    session.pop('admin_id', None)
    flash('已退出登录', 'success')
    return redirect(url_for('admin.login'))

@bp.route('/dashboard')
@admin_session_required
def dashboard():
    """管理后台首页"""
    # 获取当前管理员
    admin = User.query.get(session['admin_id'])
    
    # 获取今日日期范围
    today = datetime.utcnow().date()
    today_start = datetime.combine(today, datetime.min.time())
    today_end = datetime.combine(today, datetime.max.time())
    
    # 根据角色获取不同的统计数据
    if admin.has_role('admin'):
        # 管理员可以看到所有数据
        stats = {
            'total_users': User.query.count(),
            'total_investments': db.session.query(func.sum(Investment.amount)).scalar() or 0,
            'total_withdrawals': db.session.query(func.sum(Withdrawal.amount)).scalar() or 0,
            'total_recharges': db.session.query(func.sum(Recharge.amount)).filter_by(status='completed').scalar() or 0,
            # 今日数据
            'today_users': User.query.filter(User.created_at.between(today_start, today_end)).count(),
            'today_investments': db.session.query(func.sum(Investment.amount)).filter(
                Investment.created_at.between(today_start, today_end)
            ).scalar() or 0,
            'today_withdrawals': db.session.query(func.sum(Withdrawal.amount)).filter(
                Withdrawal.created_at.between(today_start, today_end)
            ).scalar() or 0,
            'today_recharges': db.session.query(func.sum(Recharge.amount)).filter(
                Recharge.created_at.between(today_start, today_end),
                Recharge.status == 'completed'
            ).scalar() or 0
        }
    elif admin.has_role('agent'):
        # 代理只能看到自己的下级数据
        subordinate_ids = [u.id for u in User.query.filter_by(referrer_id=admin.id).all()]
        stats = {
            'total_users': User.query.filter(
                (User.referrer_id == admin.id) |
                (User.referrer_id.in_(subordinate_ids))
            ).count(),
            'total_investments': db.session.query(func.sum(Investment.amount)).filter(
                Investment.user_id.in_([admin.id] + subordinate_ids)
            ).scalar() or 0,
            'total_withdrawals': db.session.query(func.sum(Withdrawal.amount)).filter(
                Withdrawal.user_id.in_([admin.id] + subordinate_ids)
            ).scalar() or 0,
            'total_recharges': db.session.query(func.sum(Recharge.amount)).filter(
                Recharge.user_id.in_([admin.id] + subordinate_ids),
                Recharge.status == 'completed'
            ).scalar() or 0,
            # 今日数据
            'today_users': User.query.filter(
                User.created_at.between(today_start, today_end),
                (User.referrer_id == admin.id) |
                (User.referrer_id.in_(subordinate_ids))
            ).count(),
            'today_investments': db.session.query(func.sum(Investment.amount)).filter(
                Investment.created_at.between(today_start, today_end),
                Investment.user_id.in_([admin.id] + subordinate_ids)
            ).scalar() or 0,
            'today_withdrawals': db.session.query(func.sum(Withdrawal.amount)).filter(
                Withdrawal.created_at.between(today_start, today_end),
                Withdrawal.user_id.in_([admin.id] + subordinate_ids)
            ).scalar() or 0,
            'today_recharges': db.session.query(func.sum(Recharge.amount)).filter(
                Recharge.created_at.between(today_start, today_end),
                Recharge.user_id.in_([admin.id] + subordinate_ids),
                Recharge.status == 'completed'
            ).scalar() or 0
        }
    else:  # staff
        # 员工只能看到自己发展的客户数据
        customer_ids = [u.id for u in User.query.filter_by(referrer_id=admin.id).all()]
        stats = {
            'total_users': len(customer_ids),
            'total_investments': db.session.query(func.sum(Investment.amount)).filter(
                Investment.user_id.in_(customer_ids)
            ).scalar() or 0,
            'total_withdrawals': db.session.query(func.sum(Withdrawal.amount)).filter(
                Withdrawal.user_id.in_(customer_ids)
            ).scalar() or 0,
            'total_recharges': db.session.query(func.sum(Recharge.amount)).filter(
                Recharge.user_id.in_(customer_ids),
                Recharge.status == 'completed'
            ).scalar() or 0,
            # 今日数据
            'today_users': User.query.filter(
                User.created_at.between(today_start, today_end),
                User.id.in_(customer_ids)
            ).count(),
            'today_investments': db.session.query(func.sum(Investment.amount)).filter(
                Investment.created_at.between(today_start, today_end),
                Investment.user_id.in_(customer_ids)
            ).scalar() or 0,
            'today_withdrawals': db.session.query(func.sum(Withdrawal.amount)).filter(
                Withdrawal.created_at.between(today_start, today_end),
                Withdrawal.user_id.in_(customer_ids)
            ).scalar() or 0,
            'today_recharges': db.session.query(func.sum(Recharge.amount)).filter(
                Recharge.created_at.between(today_start, today_end),
                Recharge.user_id.in_(customer_ids),
                Recharge.status == 'completed'
            ).scalar() or 0
        }
    
    # 获取最近活动数据
    recent_activities = []
    
    if admin.has_role('staff'):
        # 员工只能看到自己客户的活动
        customer_ids = [u.id for u in User.query.filter_by(referrer_id=admin.id).all()]
        
        # 最近注册的客户
        recent_users = User.query.filter(
            User.id.in_(customer_ids)
        ).order_by(User.created_at.desc()).limit(5).all()
        
        # 最近的投资记录
        recent_investments = Investment.query.filter(
            Investment.user_id.in_(customer_ids)
        ).order_by(Investment.created_at.desc()).limit(5).all()
        
        # 最近的提现记录
        recent_withdrawals = Withdrawal.query.filter(
            Withdrawal.user_id.in_(customer_ids)
        ).order_by(Withdrawal.created_at.desc()).limit(5).all()
    else:
        # 管理员和代理可以看到相应范围内的所有活动
        if admin.has_role('admin'):
            # 最近注册的用户
            recent_users = User.query.order_by(User.created_at.desc()).limit(5).all()
            # 最近的投资记录
            recent_investments = Investment.query.order_by(Investment.created_at.desc()).limit(5).all()
            # 最近的提现记录
            recent_withdrawals = Withdrawal.query.order_by(Withdrawal.created_at.desc()).limit(5).all()
        else:  # agent
            subordinate_ids = [u.id for u in User.query.filter_by(referrer_id=admin.id).all()]
            user_ids = [admin.id] + subordinate_ids
            
            # 最近注册的用户
            recent_users = User.query.filter(
                User.referrer_id.in_(user_ids)
            ).order_by(User.created_at.desc()).limit(5).all()
            
            # 最近的投资记录
            recent_investments = Investment.query.filter(
                Investment.user_id.in_(user_ids)
            ).order_by(Investment.created_at.desc()).limit(5).all()
            
            # 最近的提现记录
            recent_withdrawals = Withdrawal.query.filter(
                Withdrawal.user_id.in_(user_ids)
            ).order_by(Withdrawal.created_at.desc()).limit(5).all()
    
    # 添加活动到列表
    for user in recent_users:
        recent_activities.append({
            'type': 'user',
            'description': f'新用户 {user.username} 注册了账号',
            'time': user.created_at.strftime('%Y-%m-%d %H:%M:%S')
        })
    
    for inv in recent_investments:
        recent_activities.append({
            'type': 'investment',
            'description': f'用户 {inv.user.username} 投资了 ¥{inv.amount:.2f}',
            'time': inv.created_at.strftime('%Y-%m-%d %H:%M:%S')
        })
    
    for w in recent_withdrawals:
        recent_activities.append({
            'type': 'withdrawal',
            'description': f'用户 {w.user.username} 申请提现 ¥{w.amount:.2f}',
            'time': w.created_at.strftime('%Y-%m-%d %H:%M:%S')
        })
    
    # 按时间排序所有活动
    recent_activities.sort(key=lambda x: x['time'], reverse=True)
    recent_activities = recent_activities[:10]  # 只保留最近10条
    
    # 准备图表数据
    # 获取过去7天的数据
    past_days = 7
    dates = [(today - timedelta(days=i)) for i in range(past_days-1, -1, -1)]
    daily_stats = {
        'dates': [d.strftime('%Y-%m-%d') for d in dates],
        'users': [],
        'investments': [],
        'withdrawals': [],
        'recharges': []
    }
    
    for date in dates:
        start = datetime.combine(date, datetime.min.time())
        end = datetime.combine(date, datetime.max.time())
        
        if admin.has_role('staff'):
            # 员工只看自己客户的数据
            customer_ids = [u.id for u in User.query.filter_by(referrer_id=admin.id).all()]
            
            # 新增客户数
            daily_stats['users'].append(
                User.query.filter(
                    User.created_at.between(start, end),
                    User.id.in_(customer_ids)
                ).count()
            )
            
            # 投资金额
            daily_stats['investments'].append(
                db.session.query(func.sum(Investment.amount))
                .filter(
                    Investment.created_at.between(start, end),
                    Investment.user_id.in_(customer_ids)
                ).scalar() or 0
            )
            
            # 提现金额
            daily_stats['withdrawals'].append(
                db.session.query(func.sum(Withdrawal.amount))
                .filter(
                    Withdrawal.created_at.between(start, end),
                    Withdrawal.user_id.in_(customer_ids)
                ).scalar() or 0
            )
            
            # 充值金额
            daily_stats['recharges'].append(
                db.session.query(func.sum(Recharge.amount))
                .filter(
                    Recharge.created_at.between(start, end),
                    Recharge.user_id.in_(customer_ids),
                    Recharge.status == 'completed'
                ).scalar() or 0
            )
        else:
            # 管理员和代理看各自范围内的数据
            if admin.has_role('admin'):
                # 新增用户数
                daily_stats['users'].append(
                    User.query.filter(User.created_at.between(start, end)).count()
                )
                
                # 投资金额
                daily_stats['investments'].append(
                    db.session.query(func.sum(Investment.amount))
                    .filter(Investment.created_at.between(start, end))
                    .scalar() or 0
                )
                
                # 提现金额
                daily_stats['withdrawals'].append(
                    db.session.query(func.sum(Withdrawal.amount))
                    .filter(Withdrawal.created_at.between(start, end))
                    .scalar() or 0
                )
                
                # 充值金额
                daily_stats['recharges'].append(
                    db.session.query(func.sum(Recharge.amount))
                    .filter(
                        Recharge.created_at.between(start, end),
                        Recharge.status == 'completed'
                    ).scalar() or 0
                )
            else:  # agent
                subordinate_ids = [u.id for u in User.query.filter_by(referrer_id=admin.id).all()]
                user_ids = [admin.id] + subordinate_ids
                
                # 新增用户数
                daily_stats['users'].append(
                    User.query.filter(
                        User.created_at.between(start, end),
                        User.referrer_id.in_(user_ids)
                    ).count()
                )
                
                # 投资金额
                daily_stats['investments'].append(
                    db.session.query(func.sum(Investment.amount))
                    .filter(
                        Investment.created_at.between(start, end),
                        Investment.user_id.in_(user_ids)
                    ).scalar() or 0
                )
                
                # 提现金额
                daily_stats['withdrawals'].append(
                    db.session.query(func.sum(Withdrawal.amount))
                    .filter(
                        Withdrawal.created_at.between(start, end),
                        Withdrawal.user_id.in_(user_ids)
                    ).scalar() or 0
                )
                
                # 充值金额
                daily_stats['recharges'].append(
                    db.session.query(func.sum(Recharge.amount))
                    .filter(
                        Recharge.created_at.between(start, end),
                        Recharge.user_id.in_(user_ids),
                        Recharge.status == 'completed'
                    ).scalar() or 0
                )
    
    return render_template('admin/dashboard.html',
                         admin=admin,
                         stats=stats,
                         recent_activities=recent_activities,
                         daily_stats=daily_stats)

@bp.route('/users')
@admin_session_required
@role_required('admin', 'agent')
def users():
    """用户列表页面"""
    # 获取当前管理员
    admin = User.query.get(session['admin_id'])
    
    page = request.args.get('page', 1, type=int)
    per_page = 10
    username = request.args.get('username', '').strip()
    
    # 构建查询
    query = User.query
    
    # 如果是代理，只能看到自己的下级用户
    if admin.has_role('agent'):
        query = query.filter(
            (User.referrer_id == admin.id) |  # 直接下级
            (User.referrer_id.in_(  # 员工的下级
                db.session.query(User.id).filter_by(referrer_id=admin.id)
            ))
        )
    
    # 如果有用户名筛选条件，添加过滤
    if username:
        query = query.filter(User.username.ilike(f'%{username}%'))
    
    # 获取用户列表，按注册时间倒序排序
    users = query.order_by(User.created_at.desc()).paginate(
        page=page, per_page=per_page, error_out=False)
    
    return render_template('admin/users.html', 
                         admin=admin,  # 添加 admin 变量
                         users=users,
                         username=username)

@bp.route('/users/<int:user_id>')
@admin_session_required
@role_required('admin', 'agent', 'staff')
def user_detail(user_id):
    """用户详情页面"""
    try:
        user = User.query.get_or_404(user_id)
        admin = User.query.get(session['admin_id'])
    
        # 权限检查
        if admin.has_role('agent'):
            # 代理只能查看自己的下级用户
            if user.referrer_id != admin.id and user.referrer_id not in [
                u.id for u in User.query.filter_by(referrer_id=admin.id).all()
            ]:
                flash('没有权限查看此用户', 'error')
                return redirect(url_for('admin.users'))
        elif admin.has_role('staff'):
            # 员工只能查看自己发展的用户
            if user.referrer_id != admin.id:
                flash('没有权限查看此用户', 'error')
                return redirect(url_for('admin.my_customers'))
        
        # 获取用户的投资记录
        investments = Investment.query.filter_by(user_id=user.id).all()
        
        # 获取用户的提现记录
        withdrawals = Withdrawal.query.filter_by(user_id=user.id).all()
        
        # 获取推荐人数
        referral_count = User.query.filter_by(referrer_id=user.id).count()
        
        # 如果用户是员工，获取其客户列表
        customers = None
        if user.has_role('staff'):
            customers = User.query.filter_by(referrer_id=user.id).all()
            # 为每个客户计算投资总额和收益总额
            for customer in customers:
                customer.total_investment = db.session.query(func.sum(Investment.amount))\
                    .filter(Investment.user_id == customer.id).scalar() or 0
                customer.total_profit = db.session.query(func.sum(DailyProfit.amount))\
                    .filter(DailyProfit.user_id == customer.id).scalar() or 0
        
        return render_template('admin/user_detail.html', 
                             admin=admin,
                             user=user,
                             investments=investments,
                             withdrawals=withdrawals,
                             referral_count=referral_count,
                             customers=customers,
                             func=func,
                             Investment=Investment,
                             ReferralBonus=ReferralBonus)
                             
    except Exception as e:
        # 记录错误并返回错误页面
        current_app.logger.error(f'访问用户详情页面时发生错误: {str(e)}')
        flash('系统错误，请稍后重试', 'error')
        return redirect(url_for('admin.dashboard'))

@bp.route('/projects')
@admin_session_required
@role_required('admin')
def projects():
    """项目列表页面 - 仅管理员可见"""
    # 获取当前管理员
    admin = User.query.get(session['admin_id'])
    
    page = request.args.get('page', 1, type=int)
    per_page = 10
    project_name = request.args.get('project_name', '').strip()
    
    # 构建查询
    query = Project.query
    
    # 如果有项目名称筛选条件，添加过滤
    if project_name:
        query = query.filter(Project.name.ilike(f'%{project_name}%'))
    
    # 获取项目列表，按创建时间倒序排序
    projects = query.order_by(Project.created_at.desc()).paginate(
        page=page, per_page=per_page, error_out=False)
    
    return render_template('admin/projects.html', 
                         admin=admin,
                         projects=projects,
                         project_name=project_name)

@bp.route('/projects/<int:project_id>')
@admin_session_required
@role_required('admin')
def project_detail(project_id):
    """项目详情页面"""
    try:
        # 获取当前管理员信息
        admin = User.query.get(session['admin_id'])
        project = Project.query.get_or_404(project_id)
        
        # 获取项目的投资统计
        total_investment = db.session.query(func.sum(Investment.amount))\
            .filter(Investment.project_id == project.id).scalar() or 0
            
        # 获取项目的总收益
        total_profit = db.session.query(func.sum(DailyProfit.amount))\
            .filter(DailyProfit.project_id == project.id).scalar() or 0
            
        # 获取投资人数
        investor_count = db.session.query(func.count(Investment.user_id.distinct()))\
            .filter(Investment.project_id == project.id).scalar() or 0
        
        return render_template('admin/project_detail.html', 
                             admin=admin,
                             project=project,
                             total_investment=total_investment,
                             total_profit=total_profit,
                             investor_count=investor_count)
                             
    except Exception as e:
        current_app.logger.error(f'访问项目详情页面时发生错误: {str(e)}')
        flash('系统错误，请稍后重试', 'error')
        return redirect(url_for('admin.projects'))

@bp.route('/projects/create', methods=['GET', 'POST'])
@admin_session_required
@role_required('admin')
def project_create():
    """创建新项目"""
    # 获取当前管理员信息
    admin = User.query.get(session['admin_id'])
    form = CreateProjectForm()
    
    if form.validate_on_submit():
        # 处理图片上传
        image = request.files.get('image')
        image_path = save_project_image(image)
        if not image_path:
            flash('请上传有效的项目图片（PNG, JPG, JPEG, GIF）', 'error')
            return redirect(request.url)

        try:
            project = Project(
                name=form.name.data,
                description=form.description.data,
                image_path=image_path,
                target_amount=float(form.target_amount.data),
                share_price=float(form.share_price.data),
                total_shares=int(form.total_shares.data),
                available_shares=int(form.total_shares.data),  # 初始可用份额等于总份额
                daily_roi=float(form.daily_roi.data) / 100,  # 转换为小数
                end_date=datetime.strptime(form.end_date.data, '%Y-%m-%d')
            )
            db.session.add(project)
            db.session.commit()
            flash('项目创建成功', 'success')
            return redirect(url_for('admin.projects'))
        
        except ValueError as e:
            flash('请输入有效的数字', 'error')
        except Exception as e:
            db.session.rollback()
            flash(f'创建失败：{str(e)}', 'error')
        
        return redirect(url_for('admin.project_create'))
    
    return render_template('admin/project_create.html', admin=admin, form=form)

@bp.route('/projects/<int:project_id>/edit', methods=['GET', 'POST'])
@admin_session_required
@role_required('admin')
def project_edit(project_id):
    """编辑项目"""
    # 获取当前管理员信息
    admin = User.query.get(session['admin_id'])
    project = Project.query.get_or_404(project_id)
    form = EditProjectForm()
    
    if form.validate_on_submit():
        try:
            # 处理图片上传
            image = request.files.get('image')
            if image:
                # 如果上传了新图片
                image_path = save_project_image(image)
                if image_path:
                    # 删除旧图片
                    if project.image_path and project.image_path != 'default_project.jpg':
                        old_image_path = os.path.join('app', 'static', 'uploads', project.image_path)
                        if os.path.exists(old_image_path):
                            os.remove(old_image_path)
                    # 更新图片路径
                    project.image_path = image_path

            # 更新项目信息
            project.name = form.name.data
            project.description = form.description.data
            project.target_amount = float(form.target_amount.data)
            project.share_price = float(form.share_price.data)
            project.daily_roi = float(form.daily_roi.data) / 100  # 转换为小数
            project.end_date = datetime.strptime(form.end_date.data, '%Y-%m-%d')
            
            db.session.commit()
            flash('项目更新成功', 'success')
            return redirect(url_for('admin.project_detail', project_id=project.id))
            
        except ValueError as e:
            flash('请输入有效的数字', 'error')
        except Exception as e:
            db.session.rollback()
            flash(f'更新失败：{str(e)}', 'error')
            
        return redirect(url_for('admin.project_edit', project_id=project_id))
    
    # GET请求，填充表单数据
    form.name.data = project.name
    form.description.data = project.description
    form.target_amount.data = project.target_amount
    form.share_price.data = project.share_price
    form.daily_roi.data = project.daily_roi * 100  # 转换为百分比
    form.end_date.data = project.end_date.strftime('%Y-%m-%d')
    
    return render_template('admin/project_edit.html', 
                         admin=admin,
                         project=project,
                         form=form)

@bp.route('/withdrawals')
@admin_session_required
@role_required('admin')
def withdrawals():
    """提现管理页面 - 仅管理员可见"""
    # 获取当前管理员信息
    admin = User.query.get(session['admin_id'])
    
    page = request.args.get('page', 1, type=int)
    status = request.args.get('status', '')  # 默认值改为空字符串
    username = request.args.get('username', '').strip()
    
    # 获取待处理提现数量
    pending_count = Withdrawal.query.filter_by(status='pending').count()
    
    # 构建查询
    query = Withdrawal.query.join(Withdrawal.user)
    
    # 添加筛选条件
    if status and status in ['pending', 'approved', 'rejected']:  # 只有当状态不为空且有效时才添加筛选
        query = query.filter(Withdrawal.status == status)
    if username:
        query = query.filter(User.username.ilike(f'%{username}%'))
    
    # 获取分页数据
    withdrawals = query.order_by(Withdrawal.created_at.desc()).paginate(
        page=page, per_page=10, error_out=False
    )
    return render_template('admin/withdrawals.html', 
                         admin=admin,
                         withdrawals=withdrawals, 
                         pending_count=pending_count,
                         status=status,
                         username=username)

@bp.route('/withdrawals/<int:id>/approve', methods=['POST'])
@admin_session_required
@role_required('admin')
def approve_withdrawal(id):
    """通过提现申请"""
    # 获取当前管理员信息
    admin = User.query.get(session['admin_id'])
    
    withdrawal = Withdrawal.query.get_or_404(id)
    if withdrawal.status != 'pending':
        flash('该提现申请已处理', 'error')
        return redirect(url_for('admin.withdrawals', status=withdrawal.status))
    
    withdrawal.status = 'approved'
    withdrawal.processed_at = datetime.utcnow()
    withdrawal.processed_by = admin.id  # 记录处理人
    db.session.commit()
    flash('提现申请已通过', 'success')
    return redirect(url_for('admin.withdrawals', status='approved'))

@bp.route('/withdrawals/<int:id>/reject', methods=['POST'])
@admin_session_required
@role_required('admin')
def reject_withdrawal(id):
    """拒绝提现申请"""
    # 获取当前管理员信息
    admin = User.query.get(session['admin_id'])
    
    withdrawal = Withdrawal.query.get_or_404(id)
    if withdrawal.status != 'pending':
        flash('该提现申请已处理', 'error')
        return redirect(url_for('admin.withdrawals', status=withdrawal.status))
    
    # 退还用户余额
    user = withdrawal.user
    user.balance += withdrawal.amount
    
    withdrawal.status = 'rejected'
    withdrawal.processed_at = datetime.utcnow()
    withdrawal.processed_by = admin.id  # 记录处理人
    db.session.commit()
    flash('提现申请已拒绝，金额已退还用户账户', 'success')
    return redirect(url_for('admin.withdrawals', status='rejected'))

@bp.route('/withdraw_config', methods=['GET', 'POST'])
@admin_session_required
@role_required('admin')
def withdraw_config():
    """提现配置页面 - 仅管理员可见"""
    # 获取当前管理员信息
    admin = User.query.get(session['admin_id'])
    
    config = WithdrawConfig.get_config()
    form = FlaskForm()  # 用于CSRF保护
    
    if request.method == 'POST':
        try:
            config.min_amount = float(request.form.get('min_amount', 100))
            config.max_amount = float(request.form.get('max_amount', 50000))
            config.fee_percentage = float(request.form.get('fee_percentage', 2.0))
            config.daily_limit = int(request.form.get('daily_limit', 3))
            
            # 处理允许提现的星期
            allowed_days = request.form.getlist('allowed_days')
            if not allowed_days:  # 如果没有选择任何星期
                flash('请至少选择一个允许提现的星期', 'error')
                return redirect(url_for('admin.withdraw_config'))
            config.allowed_days = ','.join(sorted(allowed_days))  # 保存为逗号分隔的字符串
            
            db.session.commit()
            flash('提现配置已更新', 'success')
        except ValueError:
            flash('请输入有效的数字', 'error')
        except Exception as e:
            db.session.rollback()
            flash('更新失败：' + str(e), 'error')
        
        return redirect(url_for('admin.withdraw_config'))
    
    return render_template('admin/withdraw_config.html', 
                         admin=admin,
                         config=config,
                         form=form)

@bp.route('/recharges')
@admin_session_required
@role_required('admin')
def recharges():
    """充值管理页面 - 仅管理员可见"""
    # 获取当前管理员信息
    admin = User.query.get(session['admin_id'])
    
    page = request.args.get('page', 1, type=int)
    per_page = 10
    username = request.args.get('username', '').strip()
    payment_method = request.args.get('payment_method', '')
    
    # 构建查询
    recharges_query = db.session.query(
        Recharge, User
    ).join(
        User, User.id == Recharge.user_id
    )
    
    # 添加筛选条件
    if username:
        recharges_query = recharges_query.filter(User.username.ilike(f'%{username}%'))
    if payment_method:
        recharges_query = recharges_query.filter(Recharge.payment_method == payment_method)
    
    # 按创建时间倒序排序
    recharges_query = recharges_query.order_by(Recharge.created_at.desc())
    
    # 分页
    pagination = recharges_query.paginate(page=page, per_page=per_page, error_out=False)
    
    # 转换为列表
    recharges_list = [(recharge, user) for recharge, user in pagination.items]
    
    return render_template('admin/recharges.html',
                         admin=admin,
                         recharges=pagination,
                         recharges_list=recharges_list,
                         username=username,
                         payment_method=payment_method)

@bp.route('/recharges/<int:recharge_id>/approve', methods=['POST'])
@admin_session_required
@role_required('admin')
def approve_recharge(recharge_id):
    """审批充值记录"""
    recharge = Recharge.query.get_or_404(recharge_id)
    
    if recharge.status != 'pending':
        flash('该充值记录已被处理', 'error')
        return redirect(url_for('admin.recharges'))
    
    # 更新充值状态
    recharge.status = 'completed'
    recharge.completed_at = datetime.utcnow()
    
    # 更新用户余额
    user = User.query.get(recharge.user_id)
    user.balance += recharge.amount
    
    try:
        db.session.commit()
        flash('充值审批成功', 'success')
    except Exception as e:
        db.session.rollback()
        flash('充值审批失败', 'error')
    
    return redirect(url_for('admin.recharges'))

@bp.route('/recharges/<int:recharge_id>/reject', methods=['POST'])
@admin_session_required
@role_required('admin')
def reject_recharge(recharge_id):
    """拒绝充值记录"""
    recharge = Recharge.query.get_or_404(recharge_id)
    
    if recharge.status != 'pending':
        flash('该充值记录已被处理', 'error')
        return redirect(url_for('admin.recharges'))
    
    # 更新充值状态
    recharge.status = 'failed'
    recharge.completed_at = datetime.utcnow()
    
    try:
        db.session.commit()
        flash('已拒绝充值申请', 'success')
    except Exception as e:
        db.session.rollback()
        flash('操作失败', 'error')
    
    return redirect(url_for('admin.recharges'))

@bp.route('/referral_rates', methods=['GET', 'POST'])
@admin_session_required
@role_required('admin')
def referral_rates():
    """分销比例配置页面 - 仅管理员可见"""
    # 获取当前管理员信息
    admin = User.query.get(session['admin_id'])
    
    if request.method == 'POST':
        try:
            # 获取表单数据
            level1_rate = float(request.form.get('level1_rate', 0.1))
            level2_rate = float(request.form.get('level2_rate', 0.05))
            
            # 验证数据
            if not (0 <= level1_rate <= 1 and 0 <= level2_rate <= 1):
                flash('分销比例必须在0到1之间', 'error')
                return redirect(url_for('admin.referral_rates'))
            
            # 更新或创建一级分销比例
            level1 = ReferralRate.query.filter_by(level=1).first()
            if level1:
                level1.rate = level1_rate
            else:
                level1 = ReferralRate(level=1, rate=level1_rate)
                db.session.add(level1)
            
            # 更新或创建二级分销比例
            level2 = ReferralRate.query.filter_by(level=2).first()
            if level2:
                level2.rate = level2_rate
            else:
                level2 = ReferralRate(level=2, rate=level2_rate)
                db.session.add(level2)
            
            db.session.commit()
            flash('分销比例配置已更新', 'success')
            
        except ValueError:
            flash('请输入有效的数字', 'error')
        except Exception as e:
            db.session.rollback()
            flash('保存失败：' + str(e), 'error')
            
        return redirect(url_for('admin.referral_rates'))
    
    # GET请求：显示当前配置
    level1_rate = ReferralRate.get_rate(1)
    level2_rate = ReferralRate.get_rate(2)
    
    return render_template('admin/referral_rates.html',
                         admin=admin,
                         level1_rate=level1_rate,
                         level2_rate=level2_rate)

@bp.route('/staff')
@role_required('agent')
@admin_session_required
def staff():
    """员工管理页面 - 代理专用"""
    try:
        # 获取当前管理员信息
        admin = User.query.get(session.get('admin_id'))
        if not admin:
            current_app.logger.error('会话中的 admin_id 无效')
            flash('会话已过期，请重新登录', 'error')
            return redirect(url_for('admin.login'))
            
        # 验证用户角色
        if not admin.has_role('agent'):
            current_app.logger.error(f'用户 {admin.username} 尝试访问员工管理页面，但没有代理角色')
            flash('您没有权限访问此页面', 'error')
            return redirect(url_for('admin.dashboard'))
        
        page = request.args.get('page', 1, type=int)
        per_page = 10
        
        try:
            # 获取当前代理下的所有员工
            staff_query = User.query.join(User.role).filter(
                User.referrer_id == admin.id,
                Role.name == 'staff'  # 使用 Role.name 而不是 has 方法
            )
            
            staff_list = staff_query.paginate(page=page, per_page=per_page, error_out=False)
            
            # 为每个员工计算客户数量
            for staff in staff_list.items:
                staff.customer_count = User.query.filter_by(referrer_id=staff.id).count()
            
            return render_template('admin/staff.html', 
                                admin=admin,  # 传递 admin 变量
                                staff_list=staff_list)
                                
        except Exception as e:
            current_app.logger.error(f'查询员工列表时发生错误: {str(e)}')
            flash('获取员工列表失败，请稍后重试', 'error')
            return redirect(url_for('admin.dashboard'))
                             
    except Exception as e:
        # 记录错误并返回错误页面
        current_app.logger.error(f'访问员工管理页面时发生错误: {str(e)}')
        flash('系统错误，请稍后重试', 'error')
        return redirect(url_for('admin.dashboard'))

@bp.route('/my_customers')
@admin_session_required
@role_required('staff')
def my_customers():
    """员工查看自己的客户列表"""
    try:
        admin = User.query.get(session['admin_id'])
        page = request.args.get('page', 1, type=int)
        per_page = 10
        
        # 获取当前员工推荐的用户
        customers = User.query.filter_by(referrer_id=admin.id)\
            .order_by(User.created_at.desc())\
            .paginate(page=page, per_page=per_page)
            
        # 为每个客户计算投资总额和收益总额
        for customer in customers.items:
            customer.total_investment = db.session.query(func.sum(Investment.amount))\
                .filter(Investment.user_id == customer.id).scalar() or 0
            customer.total_profit = db.session.query(func.sum(DailyProfit.amount))\
                .filter(DailyProfit.user_id == customer.id).scalar() or 0
        
        # 只传递推广码
        referral_code = admin.referral_code
        
        return render_template('admin/my_customers.html', 
                             admin=admin,
                             customers=customers, 
                             func=func, 
                             Investment=Investment,
                             referral_code=referral_code)
                             
    except Exception as e:
        current_app.logger.error(f'访问我的客户页面时发生错误: {str(e)}')
        flash('系统错误，请稍后重试', 'error')
        return redirect(url_for('admin.dashboard'))

@bp.route('/users/<int:user_id>/disable', methods=['POST'])
@admin_session_required
@role_required('admin', 'agent', 'staff')
def disable_user(user_id):
    """禁用用户账户"""
    user = User.query.get_or_404(user_id)
    admin = User.query.get(session['admin_id'])
    
    # 检查权限
    if admin.has_role('agent'):
        # 获取代理的所有下级用户ID（包括员工和客户）
        staff_ids = [u.id for u in User.query.filter_by(referrer_id=admin.id).all()]
        customer_ids = [u.id for u in User.query.filter(User.referrer_id.in_(staff_ids)).all()]
        if user.id not in staff_ids and user.id not in customer_ids:
            abort(403)  # 代理只能操作自己区域内的用户
    elif admin.has_role('staff') and user.referrer_id != admin.id:
        abort(403)  # 员工只能操作自己的客户
        
    user.is_active = False
    db.session.commit()
    flash('用户已禁用', 'success')
    return redirect(url_for('admin.users'))

@bp.route('/users/<int:user_id>/enable', methods=['POST'])
@admin_session_required
@role_required('admin', 'agent', 'staff')
def enable_user(user_id):
    """启用用户账户"""
    user = User.query.get_or_404(user_id)
    admin = User.query.get(session['admin_id'])
    
    # 检查权限
    if admin.has_role('agent'):
        # 获取代理的所有下级用户ID（包括员工和客户）
        staff_ids = [u.id for u in User.query.filter_by(referrer_id=admin.id).all()]
        customer_ids = [u.id for u in User.query.filter(User.referrer_id.in_(staff_ids)).all()]
        if user.id not in staff_ids and user.id not in customer_ids:
            abort(403)  # 代理只能操作自己区域内的用户
    elif admin.has_role('staff') and user.referrer_id != admin.id:
        abort(403)  # 员工只能操作自己的客户
        
    user.is_active = True
    db.session.commit()
    flash('用户已启用', 'success')
    return redirect(url_for('admin.users'))

@bp.route('/staff/add', methods=['GET', 'POST'])
@admin_session_required
@role_required('agent')
def add_staff():
    """添加新员工 - 代理专用"""
    admin = User.query.get(session['admin_id'])
    form = FlaskForm()  # 添加FlaskForm用于CSRF保护
    
    if form.validate_on_submit():
        username = request.form.get('username')
        password = request.form.get('password')
        email = request.form.get('email')
        
        # 检查用户名是否已存在
        if User.query.filter_by(username=username).first():
            flash('用户名已存在', 'error')
            return redirect(url_for('admin.add_staff'))
            
        # 检查邮箱是否已存在
        if email and User.query.filter_by(email=email).first():
            flash('邮箱已被使用', 'error')
            return redirect(url_for('admin.add_staff'))
            
        # 创建新员工账户
        staff = User(
            username=username,
            email=email,
            referrer_id=admin.id,  # 设置推荐人为当前代理
            is_active=True
        )
        staff.password = password  # 使用password属性设置密码
        
        # 设置员工角色
        staff_role = Role.query.filter_by(name='staff').first()
        if staff_role:
            staff.role = staff_role
        
        try:
            db.session.add(staff)
            db.session.commit()
            flash('员工添加成功', 'success')
            return redirect(url_for('admin.staff'))
        except Exception as e:
            db.session.rollback()
            flash('添加失败：' + str(e), 'error')
            return redirect(url_for('admin.add_staff'))
    
    return render_template('admin/add_staff.html', admin=admin, form=form)

@bp.route('/staff/<int:staff_id>/disable', methods=['POST'])
@admin_session_required
@role_required('agent')
def disable_staff(staff_id):
    """禁用员工账户"""
    staff = User.query.get_or_404(staff_id)
    admin = User.query.get(session['admin_id'])
    
    # 检查是否是当前代理的员工
    if staff.referrer_id != admin.id:
        abort(403)
    
    staff.is_active = False
    db.session.commit()
    return jsonify({'success': True, 'message': '员工账户已禁用'})

@bp.route('/staff/<int:staff_id>/enable', methods=['POST'])
@admin_session_required
@role_required('agent')
def enable_staff(staff_id):
    """启用员工账户"""
    staff = User.query.get_or_404(staff_id)
    admin = User.query.get(session['admin_id'])
    
    # 检查是否是当前代理的员工
    if staff.referrer_id != admin.id:
        abort(403)
    
    staff.is_active = True
    db.session.commit()
    return jsonify({'success': True, 'message': '员工账户已启用'})

@bp.route('/agents')
@admin_session_required
@role_required('admin')
def agents():
    """代理列表页面 - 仅管理员可见"""
    # 获取当前管理员
    admin = User.query.get(session['admin_id'])
    
    page = request.args.get('page', 1, type=int)
    per_page = 10
    username = request.args.get('username', '').strip()
    
    # 构建查询
    query = User.query.join(User.role).filter(Role.name == 'agent')
    
    # 如果有用户名筛选条件，添加过滤
    if username:
        query = query.filter(User.username.ilike(f'%{username}%'))
    
    # 获取代理列表，按注册时间倒序排序
    agents = query.order_by(User.created_at.desc()).paginate(
        page=page, per_page=per_page, error_out=False)
    
    # 为每个代理计算下属员工数和客户数
    for agent in agents.items:
        # 计算员工数
        agent.staff_count = User.query.join(User.role).filter(
            User.referrer_id == agent.id,
            Role.name == 'staff'
        ).count()
        
        # 计算客户数（包括直接客户和员工发展的客户）
        staff_ids = [u.id for u in User.query.filter_by(referrer_id=agent.id).all()]
        agent.customer_count = User.query.filter(
            (User.referrer_id == agent.id) |
            (User.referrer_id.in_(staff_ids))
        ).count()
    
    return render_template('admin/agents.html', 
                         admin=admin,  # 添加 admin 变量
                         agents=agents, 
                         username=username)

@bp.route('/agents/add', methods=['GET', 'POST'])
@admin_session_required
@role_required('admin')
def add_agent():
    """添加新代理 - 仅管理员可见"""
    # 获取当前管理员信息
    admin = User.query.get(session['admin_id'])
    form = AddAgentForm()
    
    if form.validate_on_submit():
        # 检查用户名是否已存在
        if User.query.filter_by(username=form.username.data).first():
            flash('用户名已存在', 'error')
            return redirect(url_for('admin.add_agent'))
            
        # 创建新代理账户
        agent = User(
            username=form.username.data,
            email=form.email.data,
            is_active=True
        )
        agent.password = form.password.data
        
        # 设置代理角色
        agent_role = Role.query.filter_by(name='agent').first()
        if agent_role:
            agent.role = agent_role
        
        try:
            db.session.add(agent)
            db.session.commit()
            flash('代理添加成功', 'success')
            return redirect(url_for('admin.agents'))
        except Exception as e:
            db.session.rollback()
            flash('添加失败：' + str(e), 'error')
            return redirect(url_for('admin.add_agent'))
    
    return render_template('admin/add_agent.html', admin=admin, form=form)

@bp.route('/agents/<int:agent_id>/disable', methods=['POST'])
@admin_session_required
@role_required('admin')
def disable_agent(agent_id):
    """禁用代理账户"""
    agent = User.query.get_or_404(agent_id)
    
    # 确保目标用户是代理
    if not agent.has_role('agent'):
        abort(400)
    
    agent.is_active = False
    db.session.commit()
    return jsonify({'success': True, 'message': '代理账户已禁用'})

@bp.route('/agents/<int:agent_id>/enable', methods=['POST'])
@admin_session_required
@role_required('admin')
def enable_agent(agent_id):
    """启用代理账户"""
    agent = User.query.get_or_404(agent_id)
    
    # 确保目标用户是代理
    if not agent.has_role('agent'):
        abort(400)
    
    agent.is_active = True
    db.session.commit()
    return jsonify({'success': True, 'message': '代理账户已启用'})

@bp.route('/agents/<int:agent_id>')
@admin_session_required
@role_required('admin')
def agent_detail(agent_id):
    """代理详情页面"""
    # 获取当前管理员
    admin = User.query.get(session['admin_id'])
    
    agent = User.query.get_or_404(agent_id)
    
    # 确保目标用户是代理
    if not agent.has_role('agent'):
        abort(404)
    
    # 获取代理的员工列表
    staff_list = User.query.join(User.role).filter(
        User.referrer_id == agent.id,
        Role.name == 'staff'
    ).all()
    
    # 获取代理的客户列表（包括直接客户和员工发展的客户）
    staff_ids = [staff.id for staff in staff_list]
    customers = User.query.filter(
        (User.referrer_id == agent.id) |
        (User.referrer_id.in_(staff_ids))
    ).all()
    
    # 为每个员工计算客户数和业绩
    for staff in staff_list:
        staff.customer_count = User.query.filter_by(referrer_id=staff.id).count()
        staff.total_investment = db.session.query(func.sum(Investment.amount))\
            .join(User)\
            .filter(User.referrer_id == staff.id)\
            .scalar() or 0
    
    # 计算代理的总业绩
    agent.total_investment = db.session.query(func.sum(Investment.amount))\
        .join(User)\
        .filter(
            (User.referrer_id == agent.id) |
            (User.referrer_id.in_(staff_ids))
        ).scalar() or 0
    
    return render_template('admin/agent_detail.html', 
                         admin=admin,
                         agent=agent,
                         staff_list=staff_list,
                         customers=customers)

@bp.route('/agents/<int:agent_id>/add_staff', methods=['GET', 'POST'])
@admin_session_required
@role_required('admin')
def add_staff_for_agent(agent_id):
    """管理员为代理添加员工"""
    # 获取当前管理员信息
    admin = User.query.get(session['admin_id'])
    
    agent = User.query.get_or_404(agent_id)
    
    # 确保目标用户是代理
    if not agent.has_role('agent'):
        abort(404)
    
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')
        email = request.form.get('email')
        
        # 检查用户名是否已存在
        if User.query.filter_by(username=username).first():
            flash('用户名已存在', 'error')
            return redirect(url_for('admin.add_staff_for_agent', agent_id=agent.id))
            
        # 创建新员工账户
        staff = User(
            username=username,
            email=email,
            referrer_id=agent.id,  # 设置推荐人为目标代理
            is_active=True
        )
        staff.set_password(password)  # 使用set_password方法设置密码
        
        # 设置员工角色
        staff_role = Role.query.filter_by(name='staff').first()
        if staff_role:
            staff.role = staff_role
        
        try:
            db.session.add(staff)
            db.session.commit()
            flash('员工添加成功', 'success')
            return redirect(url_for('admin.agent_detail', agent_id=agent.id))
        except Exception as e:
            db.session.rollback()
            flash('添加失败：' + str(e), 'error')
            return redirect(url_for('admin.add_staff_for_agent', agent_id=agent.id))
    
    return render_template('admin/add_staff_for_agent.html', admin=admin, agent=agent)

@bp.route('/hierarchy')
@admin_session_required
@role_required('admin')
def hierarchy():
    """层级管理页面"""
    # 获取当前管理员
    admin = User.query.get(session['admin_id'])
    
    return render_template('admin/hierarchy.html',
                         admin=admin)  # 添加 admin 变量

@bp.route('/api/hierarchy')
@admin_session_required
@role_required('admin')
def get_hierarchy():
    """获取用户层级数据的API"""
    def build_tree(users):
        # 创建一个字典来存储每个用户的节点
        nodes = {}
        root_nodes = []

        # 首先创建所有用户的节点
        for user in users:
            role = user.role.name if user.role else 'user'
            node = {
                'id': user.id,
                'username': user.username,
                'role': role,
                'email': user.email,
                'is_active': user.is_active,
                'created_at': user.created_at.strftime('%Y-%m-%d %H:%M:%S'),
                'children': []
            }
            nodes[user.id] = node

        # 构建层级关系
        for user in users:
            node = nodes[user.id]
            role = user.role.name if user.role else 'user'

            if role == 'admin':
                # 管理员节点作为根节点
                root_nodes.append(node)
            elif user.referrer_id and user.referrer_id in nodes:
                # 将节点添加到其推荐人的children列表中
                parent_node = nodes[user.referrer_id]
                parent_node['children'].append(node)
            else:
                # 如果没有推荐人，也作为根节点（这种情况不应该发生）
                root_nodes.append(node)

        # 返回所有根节点
        return root_nodes

    try:
        # 获取所有用户，包括他们的角色和推荐关系
        users = User.query.join(Role, isouter=True).all()
        
        # 构建层级树
        hierarchy = build_tree(users)
        
        # 如果有多个管理员，创建一个虚拟根节点
        if len(hierarchy) > 1:
            root = {
                'id': 0,
                'username': '系统',
                'role': 'system',
                'email': '',
                'is_active': True,
                'created_at': '',
                'children': hierarchy
            }
            return jsonify(root)
        elif len(hierarchy) == 1:
            return jsonify(hierarchy[0])
        else:
            return jsonify({})
            
    except Exception as e:
        print(f"Error in get_hierarchy: {str(e)}")  # 添加错误日志
        return jsonify({'error': str(e)}), 500

def get_projects_data():
    """获取项目数据"""
    projects = Project.query.all()
    
    data = []
    for project in projects:
        # 计算项目的总投资额
        total_investment = db.session.query(func.sum(Investment.amount))\
            .filter(Investment.project_id == project.id).scalar() or 0
            
        # 计算项目的总收益
        total_profit = db.session.query(func.sum(DailyProfit.amount))\
            .filter(DailyProfit.project_id == project.id).scalar() or 0
            
        data.append({
            '项目名称': project.name,
            '目标金额': project.target_amount,
            '份额单价': project.share_price,
            '总份额': project.total_shares,
            '剩余份额': project.available_shares,
            '日收益率': f"{project.daily_roi * 100}%",
            '结束日期': project.end_date.strftime('%Y-%m-%d'),
            '创建时间': project.created_at.strftime('%Y-%m-%d %H:%M:%S'),
            '当前状态': '进行中' if project.status == 'active' else '已结束',
            '总投资额': total_investment,
            '总收益': total_profit
        })
    
    return data

def get_recharges_data():
    """获取充值数据"""
    recharges = Recharge.query.join(User).all()
    
    data = []
    for recharge in recharges:
        data.append({
            '用户名': recharge.user.username,
            '充值金额': recharge.amount,
            '支付方式': recharge.payment_method,
            '充值状态': {
                'pending': '待处理',
                'completed': '已完成',
                'failed': '已拒绝'
            }.get(recharge.status, recharge.status),
            '创建时间': recharge.created_at.strftime('%Y-%m-%d %H:%M:%S'),
            '完成时间': recharge.completed_at.strftime('%Y-%m-%d %H:%M:%S') if recharge.completed_at else '',
            '交易号': recharge.transaction_id or '',
            '备注': recharge.remarks or ''
        })
    
    return data

def get_withdrawals_data():
    """获取提现数据"""
    withdrawals = Withdrawal.query.join(User).all()
    
    data = []
    for withdrawal in withdrawals:
        data.append({
            '用户名': withdrawal.user.username,
            '提现金额': withdrawal.amount,
            '手续费': withdrawal.fee,
            '实际到账': withdrawal.amount - withdrawal.fee,
            '提现状态': {
                'pending': '待处理',
                'approved': '已通过',
                'rejected': '已拒绝'
            }.get(withdrawal.status, withdrawal.status),
            '创建时间': withdrawal.created_at.strftime('%Y-%m-%d %H:%M:%S'),
            '处理时间': withdrawal.processed_at.strftime('%Y-%m-%d %H:%M:%S') if withdrawal.processed_at else '',
            '处理人': User.query.get(withdrawal.processed_by).username if withdrawal.processed_by else '',
            '银行卡号': withdrawal.bank_card_number,
            '开户行': withdrawal.bank_name,
            '开户人': withdrawal.account_name
        })
    
    return data

@bp.route('/export/<string:type>')
@admin_session_required
@role_required('admin', 'agent')
def export_data(type):
    """导出数据
    
    Args:
        type: 导出数据类型 (users/staff/agents/projects/recharges/withdrawals)
    """
    format = request.args.get('format', 'csv')  # 默认导出为CSV
    admin = User.query.get(session['admin_id'])
    
    try:
        # 根据不同角色和类型获取数据
        if admin.has_role('admin'):
            if type == 'users':
                data = get_users_data()
            elif type == 'staff':
                data = get_staff_data()
            elif type == 'agents':
                data = get_agents_data()
            elif type == 'projects':
                data = get_projects_data()
            elif type == 'recharges':
                data = get_recharges_data()
            elif type == 'withdrawals':
                data = get_withdrawals_data()
            else:
                abort(404)
        elif admin.has_role('agent'):
            if type == 'staff':
                data = get_staff_data(agent_id=admin.id)
            elif type == 'users':
                data = get_users_data(agent_id=admin.id)
            else:
                abort(403)
        else:
            abort(403)
        
        # 转换为DataFrame
        df = pd.DataFrame(data)
        
        # 准备输出
        output = io.BytesIO()
        
        # 根据格式导出
        if format == 'csv':
            df.to_csv(output, index=False, encoding='utf-8-sig')
            mimetype = 'text/csv'
            filename = f'{type}_{datetime.now().strftime("%Y%m%d_%H%M%S")}.csv'
        else:  # excel
            df.to_excel(output, index=False)
            mimetype = 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
            filename = f'{type}_{datetime.now().strftime("%Y%m%d_%H%M%S")}.xlsx'
        
        output.seek(0)
        return send_file(
            output,
            mimetype=mimetype,
            as_attachment=True,
            download_name=filename
        )
        
    except Exception as e:
        flash(f'导出失败：{str(e)}', 'error')
        return redirect(request.referrer or url_for('admin.dashboard'))

def get_users_data(agent_id=None):
    """获取用户数据"""
    query = User.query.options(joinedload(User.role))
    
    if agent_id:
        # 代理只能看到自己的下级用户
        staff_ids = [u.id for u in User.query.filter_by(referrer_id=agent_id).all()]
        query = query.filter(
            (User.referrer_id == agent_id) |
            (User.referrer_id.in_(staff_ids))
        )
    
    users = query.all()
    
    data = []
    for user in users:
        # 计算用户的投资总额和收益总额
        total_investment = db.session.query(func.sum(Investment.amount))\
            .filter(Investment.user_id == user.id).scalar() or 0
        total_profit = db.session.query(func.sum(DailyProfit.amount))\
            .filter(DailyProfit.user_id == user.id).scalar() or 0
            
        data.append({
            '用户名': user.username,
            '邮箱': user.email,
            '角色': user.role.name if user.role else '普通用户',
            '状态': '启用' if user.is_active else '禁用',
            '注册时间': user.created_at.strftime('%Y-%m-%d %H:%M:%S'),
            '推荐人': User.query.get(user.referrer_id).username if user.referrer_id else '无',
            '账户余额': user.balance,
            '投资总额': total_investment,
            '收益总额': total_profit
        })
    
    return data

def get_staff_data(agent_id=None):
    """获取员工数据"""
    query = User.query.join(User.role).filter(Role.name == 'staff')
    
    if agent_id:
        query = query.filter(User.referrer_id == agent_id)
    
    staff = query.all()
    
    data = []
    for s in staff:
        # 计算员工的客户数和业绩
        customer_count = User.query.filter_by(referrer_id=s.id).count()
        customer_investment = db.session.query(func.sum(Investment.amount))\
            .join(User)\
            .filter(User.referrer_id == s.id)\
            .scalar() or 0
            
        data.append({
            '员工账号': s.username,
            '邮箱': s.email,
            '状态': '启用' if s.is_active else '禁用',
            '入职时间': s.created_at.strftime('%Y-%m-%d %H:%M:%S'),
            '所属代理': User.query.get(s.referrer_id).username if s.referrer_id else '无',
            '客户数量': customer_count,
            '客户投资总额': customer_investment
        })
    
    return data

def get_agents_data():
    """获取代理数据"""
    agents = User.query.join(User.role).filter(Role.name == 'agent').all()
    
    data = []
    for agent in agents:
        # 获取代理的员工数量
        staff_count = User.query.join(User.role).filter(
            User.referrer_id == agent.id,
            Role.name == 'staff'
        ).count()
            
        # 获取代理的客户数量（包括直接客户和员工的客户）
        staff_ids = [u.id for u in User.query.filter_by(referrer_id=agent.id).all()]
        customer_count = User.query.filter(
            (User.referrer_id == agent.id) |
            (User.referrer_id.in_(staff_ids))
        ).count()
        
        # 计算代理区域的总投资额
        total_investment = db.session.query(func.sum(Investment.amount))\
            .join(User)\
            .filter(
                (User.referrer_id == agent.id) |
                (User.referrer_id.in_(staff_ids))
            ).scalar() or 0
            
        data.append({
            '代理账号': agent.username,
            '邮箱': agent.email,
            '状态': '启用' if agent.is_active else '禁用',
            '注册时间': agent.created_at.strftime('%Y-%m-%d %H:%M:%S'),
            '员工数量': staff_count,
            '客户总数': customer_count,
            '区域投资总额': total_investment
        })
    
    return data

@bp.route('/assign_customers')
@admin_session_required
@role_required('agent')
def assign_customers():
    """客户分配页面 - 代理专用"""
    # 获取当前管理员信息
    admin = User.query.get(session['admin_id'])
    
    page = request.args.get('page', 1, type=int)
    per_page = 10
    username = request.args.get('username', '').strip()
    
    # 获取当前代理下的所有员工
    staff_list = User.query.join(User.role).filter(
        User.referrer_id == admin.id,
        Role.name == 'staff'
    ).all()
    
    # 构建查询 - 获取未分配推荐人的普通用户
    query = User.query.join(User.role).filter(
        User.referrer_id == None,  # 未分配推荐人的用户
        Role.name == 'user'  # 只查询普通用户
    )
    
    # 如果有用户名筛选条件，添加过滤
    if username:
        query = query.filter(User.username.ilike(f'%{username}%'))
    
    # 获取分页数据
    users = query.order_by(User.created_at.desc()).paginate(
        page=page, per_page=per_page, error_out=False)
    
    return render_template('admin/assign_customers.html',
                         admin=admin,
                         users=users,
                         staff_list=staff_list,
                         username=username)

@bp.route('/assign_customer/<int:user_id>', methods=['POST'])
@admin_session_required
@role_required('agent')
def assign_customer(user_id):
    """分配客户给员工"""
    try:
        admin = User.query.get(session['admin_id'])
        user = User.query.get_or_404(user_id)
        staff_id = request.form.get('staff_id', type=int)
        
        # 验证员工是否属于当前代理
        staff = User.query.join(User.role).filter(
            User.id == staff_id,
            User.referrer_id == admin.id,
            Role.name == 'staff'
        ).first()
        
        if not staff:
            flash('无效的员工选择', 'error')
            return redirect(url_for('admin.assign_customers'))
        
        # 验证用户是否可以被分配
        if user.referrer_id is not None:
            flash('该用户已有推荐人', 'error')
            return redirect(url_for('admin.assign_customers'))
        
        # 分配客户给员工
        user.referrer_id = staff_id
        db.session.commit()
        
        flash(f'已成功将用户 {user.username} 分配给员工 {staff.username}', 'success')
        
    except Exception as e:
        db.session.rollback()
        flash(f'分配失败：{str(e)}', 'error')
    
    return redirect(url_for('admin.assign_customers'))

@bp.route('/ai_models')
@admin_session_required
@role_required('admin')
def ai_models():
    """AI模型管理页面"""
    # 获取当前管理员
    admin = User.query.get(session['admin_id'])
    
    page = request.args.get('page', 1, type=int)
    per_page = 10
    
    # 获取模型列表
    models = ChatModels.query.order_by(ChatModels.id.desc()).paginate(
        page=page, per_page=per_page, error_out=False)
    
    return render_template('admin/ai_models.html', 
                         admin=admin,
                         models=models)

@bp.route('/ai_models/add', methods=['GET', 'POST'])
@admin_session_required
@role_required('admin')
def add_ai_model():
    """添加新的AI模型"""
    admin = User.query.get(session['admin_id'])
    form = AIModelForm()
    
    if form.validate_on_submit():
        try:
            # 创建新模型
            model = ChatModels(
                model_name=form.model_name.data,
                base_url=form.base_url.data,
                api_key=form.api_key.data,
                ai_model=form.ai_model.data
            )
            
            db.session.add(model)
            db.session.commit()
            flash('AI模型添加成功', 'success')
            return redirect(url_for('admin.ai_models'))
            
        except Exception as e:
            db.session.rollback()
            flash(f'添加失败：{str(e)}', 'error')
            return redirect(url_for('admin.add_ai_model'))
    
    return render_template('admin/add_ai_model.html', admin=admin, form=form)

@bp.route('/ai_models/<int:model_id>/edit', methods=['GET', 'POST'])
@admin_session_required
@role_required('admin')
def edit_ai_model(model_id):
    """编辑AI模型"""
    admin = User.query.get(session['admin_id'])
    model = ChatModels.query.get_or_404(model_id)
    form = AIModelForm(obj=model)
    
    if form.validate_on_submit():
        try:
            form.populate_obj(model)
            db.session.commit()
            flash('AI模型更新成功', 'success')
            return redirect(url_for('admin.ai_models'))
            
        except Exception as e:
            db.session.rollback()
            flash(f'更新失败：{str(e)}', 'error')
            return redirect(url_for('admin.edit_ai_model', model_id=model_id))
    
    return render_template('admin/edit_ai_model.html', admin=admin, model=model, form=form)

@bp.route('/ai_models/<int:model_id>/delete', methods=['POST'])
@admin_session_required
@role_required('admin')
def delete_ai_model(model_id):
    """删除AI模型"""
    try:
        model = ChatModels.query.get_or_404(model_id)
        db.session.delete(model)
        db.session.commit()
        flash('AI模型已删除', 'success')
    except Exception as e:
        db.session.rollback()
        flash(f'删除失败：{str(e)}', 'error')
    
    return redirect(url_for('admin.ai_models'))

@bp.route('/ai_models/<int:model_id>/toggle', methods=['GET'])
@admin_session_required
@role_required('admin')
def toggle_ai_model(model_id):
    """切换AI模型状态"""
    try:
        model = ChatModels.query.get_or_404(model_id)
        model.is_active = not model.is_active
        db.session.commit()
        status = "启用" if model.is_active else "禁用"
        flash(f'AI模型已{status}', 'success')
    except Exception as e:
        db.session.rollback()
        flash(f'操作失败：{str(e)}', 'error')
    
    return redirect(url_for('admin.ai_models'))

# ... 其他管理路由 ...