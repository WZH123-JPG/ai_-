from datetime import datetime, timedelta
from sqlalchemy import func
from ..models import Investment, DailyProfit, User, ReferralBonus, ReferralRate
from .. import db

def calculate_daily_profits():
    """计算每日收益"""
    today = datetime.utcnow().date()
    
    # 获取所有活跃投资
    investments = Investment.query.filter_by(status='active').all()
    
    # 获取分销比例配置
    level1_rate = ReferralRate.get_rate(1)  # 一级分销比例
    level2_rate = ReferralRate.get_rate(2)  # 二级分销比例
    
    for investment in investments:
        # 计算投资收益
        daily_profit_amount = investment.amount * investment.project.daily_roi
        
        # 创建每日收益记录
        daily_profit = DailyProfit(
            user_id=investment.user_id,
            investment_id=investment.id,
            amount=daily_profit_amount,
            date=today
        )
        db.session.add(daily_profit)
        
        # 计算分销奖励
        investor = User.query.get(investment.user_id)
        
        # 如果投资人有推荐人（一级分销）
        if investor.referred_by:
            level1_referrer = User.query.get(investor.referred_by)
            level1_bonus_amount = daily_profit_amount * level1_rate
            
            # 创建一级分销奖励记录
            level1_bonus = ReferralBonus(
                referrer_id=level1_referrer.id,
                referred_id=investor.id,
                amount=level1_bonus_amount,
                status='completed'
            )
            db.session.add(level1_bonus)
            
            # 如果一级推荐人也有推荐人（二级分销）
            if level1_referrer.referred_by:
                level2_referrer = User.query.get(level1_referrer.referred_by)
                level2_bonus_amount = daily_profit_amount * level2_rate
                
                # 创建二级分销奖励记录
                level2_bonus = ReferralBonus(
                    referrer_id=level2_referrer.id,
                    referred_id=investor.id,
                    amount=level2_bonus_amount,
                    status='completed'
                )
                db.session.add(level2_bonus)
    
    try:
        db.session.commit()
    except Exception as e:
        print(f"Error calculating daily profits: {str(e)}")
        db.session.rollback() 