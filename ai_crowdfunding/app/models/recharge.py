from app import db
from datetime import datetime

class Recharge(db.Model):
    """充值记录模型"""
    __tablename__ = 'recharges'
    __table_args__ = {'extend_existing': True}
    
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'))
    amount = db.Column(db.Float, nullable=False)  # 充值金额
    payment_method = db.Column(db.String(50))  # 支付方式
    payment_no = db.Column(db.String(100))  # 支付流水号
    status = db.Column(db.String(20), default='pending')  # pending, completed, failed
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    completed_at = db.Column(db.DateTime)  # 完成时间
    remarks = db.Column(db.String(255))  # 备注信息
    
    def __repr__(self):
        return f'<Recharge {self.id} User {self.user_id}>'

    def to_dict(self):
        return {
            'id': self.id,
            'amount': self.amount,
            'status': self.status,
            'created_at': self.created_at.strftime('%Y-%m-%d %H:%M:%S'),
            'completed_at': self.completed_at.strftime('%Y-%m-%d %H:%M:%S') if self.completed_at else None,
            'payment_method': self.payment_method,
            'payment_no': self.payment_no,
            'remarks': self.remarks
        } 