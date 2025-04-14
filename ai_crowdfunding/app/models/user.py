from datetime import datetime
from flask_login import UserMixin, AnonymousUserMixin
from werkzeug.security import generate_password_hash, check_password_hash
from app import db
from .role import Role
import hashlib

class User(UserMixin, db.Model):
    """用户模型"""
    __tablename__ = 'users'
    __table_args__ = {'extend_existing': True}
    
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(64), unique=True, index=True)
    email = db.Column(db.String(120), unique=True, index=True)
    password_hash = db.Column(db.String(128))
    avatar_path = db.Column(db.String(256), default='default_avatar.jpg')
    role_id = db.Column(db.Integer, db.ForeignKey('roles.id'))
    referrer_id = db.Column(db.Integer, db.ForeignKey('users.id'))
    balance = db.Column(db.Float, default=0.0)  # 账户余额
    is_active = db.Column(db.Boolean, default=True)
    is_admin = db.Column(db.Boolean, default=False)
    referral_code = db.Column(db.String(10), unique=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    # 基本关系
    role = db.relationship('Role', backref='users')
    referrer = db.relationship('User', remote_side=[id], backref='referrals')
    investments = db.relationship('Investment', backref='user', lazy='dynamic')
    recharges = db.relationship('Recharge', backref='user', lazy='dynamic')
    daily_profits = db.relationship('DailyProfit', backref='user', lazy='dynamic')
    
    def __init__(self, **kwargs):
        super(User, self).__init__(**kwargs)
        if self.role is None:
            # 设置默认角色为普通用户
            default_role = Role.query.filter_by(name='user').first()
            if default_role:
                self.role = default_role
                
    @property
    def password(self):
        raise AttributeError('password is not a readable attribute')

    @password.setter
    def password(self, password):
        self.password_hash = generate_password_hash(password)

    def verify_password(self, password):
        return check_password_hash(self.password_hash, password)
        
    def has_role(self, role_name):
        """检查用户是否具有指定角色"""
        return self.role and self.role.name == role_name
        
    def has_permission(self, perm):
        """检查用户是否具有指定权限"""
        return self.role and self.role.has_permission(perm)
        
    def can_access_backend(self):
        """检查用户是否可以访问后台"""
        return self.has_role('admin') or self.has_role('agent') or self.has_role('staff')
        
    def can_manage_user(self, target_user):
        """检查是否可以管理目标用户"""
        if self.has_role('admin'):
            return True
            
        if self.has_role('agent'):
            # 代理可以管理自己发展的员工和客户
            return (target_user.referrer == self or 
                   any(staff.id == target_user.referrer_id for staff in self.referrals))
            
        if self.has_role('staff'):
            # 员工只能管理自己发展的客户
            return target_user.referrer == self
            
        return False
        
    def get_subordinates(self, include_indirect=False):
        """获取下属用户"""
        if self.has_role('admin'):
            # 管理员可以看到所有用户
            return User.query.filter(User.id != self.id).all()
            
        if self.has_role('agent'):
            # 代理可以看到直接下属（员工）和间接下属（客户）
            direct_subordinates = self.referrals.all()
            if include_indirect:
                indirect_subordinates = []
                for staff in direct_subordinates:
                    indirect_subordinates.extend(staff.referrals.all())
                return direct_subordinates + indirect_subordinates
            return direct_subordinates
            
        if self.has_role('staff'):
            # 员工只能看到直接发展的客户
            return self.referrals.all()
            
        return []
        
    def generate_referral_code(self):
        """生成唯一的推荐码"""
        if not self.referral_code:
            # 使用用户ID和时间戳生成唯一的推荐码
            timestamp = datetime.utcnow().strftime('%Y%m%d%H%M%S')
            code_base = f"{self.id}{timestamp}"
            self.referral_code = hashlib.md5(code_base.encode()).hexdigest()[:8].upper()

    def __repr__(self):
        return f'<User {self.username}>'

class AnonymousUser(AnonymousUserMixin):
    """匿名用户类"""
    def has_role(self, role_name):
        return False
        
    def has_permission(self, perm):
        return False
        
    def can_access_backend(self):
        return False
    
    def can_manage_user(self, target_user):
        return False
    
    def get_subordinates(self, include_indirect=False):
        return []