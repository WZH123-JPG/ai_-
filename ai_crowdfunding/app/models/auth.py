from datetime import datetime
from app.extensions import db

# 角色-权限关联表
role_permissions = db.Table('role_permissions',
    db.Column('role_id', db.Integer, db.ForeignKey('roles.id'), primary_key=True),
    db.Column('permission_id', db.Integer, db.ForeignKey('permissions.id'), primary_key=True),
    db.Column('created_at', db.DateTime, default=datetime.utcnow)
)

class Role(db.Model):
    """角色模型"""
    __tablename__ = 'roles'
    
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(50), unique=True, nullable=False)  # admin, agent, staff
    description = db.Column(db.String(200))
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # 关联权限
    permissions = db.relationship('Permission', secondary=role_permissions,
                                backref=db.backref('roles', lazy='dynamic'))
    
    @staticmethod
    def init_roles():
        """初始化角色"""
        roles = {
            'admin': '超级管理员',
            'agent': '代理',
            'staff': '普通员工'
        }
        
        for name, description in roles.items():
            role = Role.query.filter_by(name=name).first()
            if not role:
                role = Role(name=name, description=description)
                db.session.add(role)
        
        db.session.commit()

class Permission(db.Model):
    """权限模型"""
    __tablename__ = 'permissions'
    
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(50), unique=True, nullable=False)
    code = db.Column(db.String(50), unique=True, nullable=False)
    description = db.Column(db.String(200))
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    @staticmethod
    def init_permissions():
        """初始化权限"""
        permissions = {
            'user_manage': ('用户管理', '管理所有用户信息'),
            'staff_manage': ('员工管理', '管理员工信息'),
            'agent_manage': ('代理管理', '管理代理信息'),
            'fund_manage': ('资金管理', '管理平台资金'),
            'data_export': ('数据导出', '导出平台数据'),
            'customer_assign': ('客户分配', '分配客户给员工'),
            'customer_view': ('查看客户', '查看客户信息'),
            'customer_manage': ('管理客户', '管理客户状态'),
            'system_config': ('系统配置', '管理系统配置'),
            'report_view': ('查看报表', '查看统计报表')
        }
        
        for code, (name, description) in permissions.items():
            permission = Permission.query.filter_by(code=code).first()
            if not permission:
                permission = Permission(name=name, code=code, description=description)
                db.session.add(permission)
        
        db.session.commit()

    @staticmethod
    def init_role_permissions():
        """初始化角色权限"""
        # 获取所有权限
        all_permissions = Permission.query.all()
        staff_permissions = Permission.query.filter(
            Permission.code.in_(['customer_view', 'customer_manage'])
        ).all()
        agent_permissions = Permission.query.filter(
            Permission.code.in_([
                'staff_manage', 'customer_assign', 'customer_view',
                'customer_manage', 'data_export', 'report_view'
            ])
        ).all()
        
        # 获取角色
        admin_role = Role.query.filter_by(name='admin').first()
        agent_role = Role.query.filter_by(name='agent').first()
        staff_role = Role.query.filter_by(name='staff').first()
        
        # 分配权限
        if admin_role:
            admin_role.permissions = all_permissions
        if agent_role:
            agent_role.permissions = agent_permissions
        if staff_role:
            staff_role.permissions = staff_permissions
        
        db.session.commit() 