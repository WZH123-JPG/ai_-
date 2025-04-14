from app import db
from datetime import datetime

class Withdrawal(db.Model):
    """提现记录模型"""
    __tablename__ = 'withdrawals'
    __table_args__ = {'extend_existing': True}
    
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'))
    amount = db.Column(db.Float, nullable=False)  # 提现金额
    fee = db.Column(db.Float, default=0.0)  # 手续费
    actual_amount = db.Column(db.Float, nullable=False)  # 实际到账金额
    bank_name = db.Column(db.String(100))  # 银行名称
    bank_card_number = db.Column(db.String(50))  # 银行卡号
    bank_account_name = db.Column(db.String(100))  # 开户名
    status = db.Column(db.String(20), default='pending')  # pending, approved, rejected
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    processed_at = db.Column(db.DateTime)  # 处理时间
    remarks = db.Column(db.String(200))  # 备注
    processed_by = db.Column(db.Integer, db.ForeignKey('users.id'))  # 处理人ID
    
    # 关联用户
    user = db.relationship('User', foreign_keys=[user_id], backref=db.backref('withdrawals', lazy='dynamic'))
    processor = db.relationship('User', foreign_keys=[processed_by])
    
    def __repr__(self):
        return f'<Withdrawal {self.id} User {self.user_id}>'

class WithdrawConfig(db.Model):
    """提现配置"""
    __tablename__ = 'withdraw_config'
    
    id = db.Column(db.Integer, primary_key=True)
    min_amount = db.Column(db.Float, nullable=False, default=100.0)  # 最低提现金额
    max_amount = db.Column(db.Float, nullable=False, default=50000.0)  # 最高提现金额
    fee_percentage = db.Column(db.Float, nullable=False, default=2.0)  # 手续费百分比
    daily_limit = db.Column(db.Integer, nullable=False, default=3)  # 每日提现次数限制
    start_time = db.Column(db.String(5), nullable=False, default='08:00')  # 开始时间
    end_time = db.Column(db.String(5), nullable=False, default='16:00')  # 结束时间
    allowed_days = db.Column(db.String(20), nullable=False, default='0,1,2,3,4')  # 允许提现的星期（0-6，逗号分隔）
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    @property
    def allowed_days_list(self):
        """获取允许提现的星期列表"""
        return [int(day) for day in self.allowed_days.split(',') if day]

    @property
    def allowed_days_display(self):
        """获取允许提现的星期显示文本"""
        days_map = {
            '0': '周日',
            '1': '周一',
            '2': '周二',
            '3': '周三',
            '4': '周四',
            '5': '周五',
            '6': '周六'
        }
        allowed = self.allowed_days.split(',')
        return '、'.join(days_map[day] for day in allowed)

    @staticmethod
    def get_config():
        """获取当前配置"""
        config = WithdrawConfig.query.order_by(WithdrawConfig.id.desc()).first()
        if not config:
            config = WithdrawConfig()
            db.session.add(config)
            db.session.commit()
        return config

    def is_withdrawal_allowed(self):
        """检查当前时间是否允许提现"""
        now = datetime.now()
        # 检查星期（将 weekday() 返回的 0-6（周一到周日）转换为 0-6（周日到周六））
        current_day = str((now.weekday() + 1) % 7)  # 转换星期并转为字符串
        if current_day not in self.allowed_days.split(','):
            return False
        
        # 检查时间
        current_time = now.strftime('%H:%M')
        return self.start_time <= current_time <= self.end_time