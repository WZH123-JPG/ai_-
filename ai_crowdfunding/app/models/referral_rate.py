from app import db
from datetime import datetime

class ReferralRate(db.Model):
    """推荐奖励比例配置模型"""
    __tablename__ = 'referral_rates'
    __table_args__ = {'extend_existing': True}
    
    id = db.Column(db.Integer, primary_key=True)
    role = db.Column(db.String(50), nullable=False)  # 角色：agent, staff
    level = db.Column(db.Integer, nullable=False)  # 层级：1, 2, 3
    rate = db.Column(db.Float, nullable=False)  # 奖励比例
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    def __repr__(self):
        return f'<ReferralRate {self.role} Level {self.level} Rate {self.rate}%>'

    @staticmethod
    def get_rate(level):
        """获取指定级别的分销比例"""
        rate = ReferralRate.query.filter_by(level=level).first()
        return rate.rate if rate else (0.1 if level == 1 else 0.05)  # 默认一级10%，二级5% 