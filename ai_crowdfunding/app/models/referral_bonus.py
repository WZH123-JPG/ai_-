from datetime import datetime
from app import db

class ReferralBonus(db.Model):
    """推荐奖励记录模型"""
    __tablename__ = 'referral_bonuses'
    __table_args__ = {'extend_existing': True}
    
    id = db.Column(db.Integer, primary_key=True)
    referrer_id = db.Column(db.Integer, db.ForeignKey('users.id'))  # 推荐人ID
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'))  # 被推荐人ID
    investment_id = db.Column(db.Integer, db.ForeignKey('investments.id'))  # 投资记录ID
    amount = db.Column(db.Float, nullable=False)  # 奖励金额
    level = db.Column(db.Integer, nullable=False)  # 推荐层级（1级、2级、3级）
    rate = db.Column(db.Float, nullable=False)  # 奖励比例
    status = db.Column(db.String(20), default='pending')  # pending, paid
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    paid_at = db.Column(db.DateTime)  # 发放时间
    
    # 添加关系
    referrer = db.relationship(
        'User',
        primaryjoin='ReferralBonus.referrer_id == User.id',
        backref=db.backref('bonuses_given', lazy='dynamic')
    )
    user = db.relationship(
        'User',
        primaryjoin='ReferralBonus.user_id == User.id',
        backref=db.backref('bonuses_received', lazy='dynamic')
    )
    investment = db.relationship('Investment', backref=db.backref('referral_bonuses', lazy='dynamic'))

    def __repr__(self):
        return f'<ReferralBonus {self.id} Referrer {self.referrer_id} User {self.user_id}>'