from flask import Blueprint, render_template
from flask_login import login_required, current_user
from ..models import Project, Investment, User, DailyProfit, ReferralBonus
from datetime import datetime, timedelta
from sqlalchemy import and_, func
from .. import db

bp = Blueprint('main', __name__)

@bp.route('/')
def index():
    """首页"""
    # 获取所有活跃项目，使用数据库级别的排序
    projects = Project.query.filter_by(status='active')\
        .order_by(((Project.total_shares - Project.available_shares) * 100 / Project.total_shares).desc())\
        .limit(2)\
        .all()
    
    # 统计数据
    total_users = User.query.count()
    total_projects = Project.query.count()
    total_investment = Investment.query.with_entities(func.sum(Investment.amount)).scalar() or 0
    total_investment = round(total_investment / 10000, 2)  # 转换为万元
    
    # 计算平均日收益率
    avg_roi = Project.query.with_entities(func.avg(Project.daily_roi)).scalar() or 0
    avg_roi = round(avg_roi * 100, 2)  # 转换为百分比
    
    # 如果用户已登录，计算收益
    yesterday_earnings = 0
    total_earnings = 0
    
    if current_user.is_authenticated:
        # 计算昨日收益
        yesterday = datetime.utcnow().date() - timedelta(days=1)
        # 昨日投资收益
        yesterday_investment_earnings = DailyProfit.query.filter_by(
            user_id=current_user.id,
            date=yesterday
        ).with_entities(func.sum(DailyProfit.amount)).scalar() or 0
        
        # 昨日推荐奖励
        yesterday_start = datetime.combine(yesterday, datetime.min.time())
        yesterday_end = datetime.combine(yesterday, datetime.max.time())
        yesterday_referral_earnings = db.session.query(func.sum(ReferralBonus.amount)).filter(
            ReferralBonus.referrer_id == current_user.id,
            ReferralBonus.created_at >= yesterday_start,
            ReferralBonus.created_at <= yesterday_end
        ).scalar() or 0
        
        yesterday_earnings = yesterday_investment_earnings + yesterday_referral_earnings
        
        # 计算累计收益
        # 投资收益
        total_investment_earnings = DailyProfit.query.filter_by(
            user_id=current_user.id
        ).with_entities(func.sum(DailyProfit.amount)).scalar() or 0
        
        # 推荐奖励
        total_referral_earnings = db.session.query(func.sum(ReferralBonus.amount)).filter(
            ReferralBonus.referrer_id == current_user.id
        ).scalar() or 0
        
        total_earnings = total_investment_earnings + total_referral_earnings
    
    return render_template('main/index.html',
                         projects=projects,
                         total_users=total_users,
                         total_projects=total_projects,
                         total_investment=total_investment,
                         avg_roi=avg_roi,
                         yesterday_earnings=yesterday_earnings,
                         total_earnings=total_earnings)

@bp.route('/dashboard')
@login_required
def dashboard():
    now = datetime.now()
    user_investments = Investment.query.filter_by(user_id=current_user.id).all()
    return render_template('main/dashboard.html', 
                         investments=user_investments,
                         now=now)

@bp.route('/projects')
def projects():
    """项目列表页面"""
    now = datetime.utcnow()
    # 获取所有项目，包括已结束的
    projects = Project.query.order_by(Project.created_at.desc()).all()
    return render_template('main/projects.html', projects=projects, now=now)