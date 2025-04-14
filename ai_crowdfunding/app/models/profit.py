from datetime import datetime
from app import db

class DailyProfit(db.Model):
    """每日收益记录"""
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    investment_id = db.Column(db.Integer, db.ForeignKey('investment.id'), nullable=False)
    project_id = db.Column(db.Integer, db.ForeignKey('project.id'), nullable=False)
    amount = db.Column(db.Float, nullable=False)  # 当日收益金额
    date = db.Column(db.Date, nullable=False)  # 收益日期
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    # 关联关系
    user = db.relationship('User', backref=db.backref('daily_profits', lazy='dynamic'))
    investment = db.relationship('Investment', backref=db.backref('daily_profits', lazy='dynamic'))
    project = db.relationship('Project', backref=db.backref('daily_profits', lazy='dynamic'))

    @staticmethod
    def calculate_daily_profit(investment):
        """计算某个投资的每日收益"""
        return round(investment.amount * investment.project.daily_roi, 2)