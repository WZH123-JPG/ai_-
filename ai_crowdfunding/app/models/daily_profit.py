from datetime import datetime
from app import db

class DailyProfit(db.Model):
    """每日收益记录模型"""
    __tablename__ = 'daily_profits'
    __table_args__ = {'extend_existing': True}
    
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'))
    project_id = db.Column(db.Integer, db.ForeignKey('projects.id'))
    investment_id = db.Column(db.Integer, db.ForeignKey('investments.id'))  # 添加投资记录外键
    amount = db.Column(db.Float, nullable=False)  # 收益金额
    date = db.Column(db.Date, nullable=False)  # 收益日期
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    def __repr__(self):
        return f'<DailyProfit {self.id} User {self.user_id} Project {self.project_id}>'

    @staticmethod
    def calculate_daily_profit(investment):
        """计算某个投资的每日收益"""
        return round(investment.amount * investment.project.daily_roi / 100, 2) 