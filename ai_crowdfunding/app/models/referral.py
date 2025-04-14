from app import db

class ReferralConfig(db.Model):
    """推荐费率配置"""
    __tablename__ = 'referral_config'
    
    id = db.Column(db.Integer, primary_key=True)
    level1_rate = db.Column(db.Float, nullable=False, default=0)  # 一级推荐费率
    level2_rate = db.Column(db.Float, nullable=False, default=0)  # 二级推荐费率
    level3_rate = db.Column(db.Float, nullable=False, default=0)  # 三级推荐费率
    created_at = db.Column(db.DateTime, nullable=False, default=db.func.now())  # 创建时间
    updated_at = db.Column(db.DateTime, nullable=False, default=db.func.now(), onupdate=db.func.now())  # 更新时间

    @classmethod
    def get_config(cls):
        """获取推荐费率配置，如果不存在则创建默认配置"""
        config = cls.query.first()
        if not config:
            config = cls(
                level1_rate=5,  # 默认5%
                level2_rate=3,  # 默认3%
                level3_rate=2   # 默认2%
            )
            db.session.add(config)
            db.session.commit()
        return config

    def to_dict(self):
        """转换为字典格式"""
        return {
            'level1_rate': self.level1_rate,
            'level2_rate': self.level2_rate,
            'level3_rate': self.level3_rate,
            'created_at': self.created_at.strftime('%Y-%m-%d %H:%M:%S'),
            'updated_at': self.updated_at.strftime('%Y-%m-%d %H:%M:%S')
        } 