from datetime import datetime
from app import db

class Project(db.Model):
    """项目模型"""
    __tablename__ = 'projects'
    __table_args__ = {'extend_existing': True}
    
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    description = db.Column(db.Text)
    image_path = db.Column(db.String(255), default='default_project.jpg')
    target_amount = db.Column(db.Float, nullable=False)  # 目标金额
    current_amount = db.Column(db.Float, default=0.0)
    share_price = db.Column(db.Float, nullable=False)  # 每份金额
    total_shares = db.Column(db.Integer, nullable=False)  # 总份数
    available_shares = db.Column(db.Integer)  # 剩余份数
    daily_roi = db.Column(db.Float, nullable=False)  # 日收益率(%)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    end_date = db.Column(db.DateTime)  # 结束日期
    status = db.Column(db.String(20), default='active')  # active, completed, cancelled
    
    # 关系
    investments = db.relationship('Investment', backref='project', lazy='dynamic')
    daily_profits = db.relationship('DailyProfit', backref='project', lazy='dynamic')
    
    def __repr__(self):
        return f'<Project {self.name}>'
    
    @property
    def remaining_shares(self):
        """获取剩余股份数（available_shares 的别名）"""
        return self.available_shares
    
    @remaining_shares.setter
    def remaining_shares(self, value):
        """设置剩余股份数（available_shares 的别名）"""
        self.available_shares = value
    
    @property
    def progress(self):
        """筹资进度(%)"""
        if self.target_amount == 0:
            return 0
        return (self.current_amount / self.target_amount) * 100
    
    @property
    def is_completed(self):
        """项目是否已完成"""
        return self.current_amount >= self.target_amount
    
    @property
    def is_expired(self):
        """项目是否已过期"""
        return self.end_date and datetime.utcnow() > self.end_date
    
    def calculate_shares(self, investment_amount):
        """计算投资可以获得的股份数"""
        if self.share_price == 0:
            return 0
        return int(investment_amount / self.share_price)