from datetime import datetime
from app import db

class Investment(db.Model):
    """投资记录模型"""
    __tablename__ = 'investments'
    __table_args__ = {'extend_existing': True}
    
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'))
    project_id = db.Column(db.Integer, db.ForeignKey('projects.id'))
    amount = db.Column(db.Float, nullable=False)  # 投资金额
    shares = db.Column(db.Integer, nullable=False)  # 购买份数
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    status = db.Column(db.String(20), default='active')  # active, completed, cancelled
    
    # 添加关系，修改为正确的外键关联
    daily_profits = db.relationship('DailyProfit', 
                                  backref=db.backref('investment', lazy='joined'),
                                  foreign_keys='DailyProfit.investment_id',
                                  lazy='dynamic')
    
    @property
    def daily_profit(self):
        """计算每日收益"""
        if not self.project:
            return 0
        return self.amount * (self.project.daily_roi / 100)

    def __repr__(self):
        return f'<Investment {self.id} by User {self.user_id}>'