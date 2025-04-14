from app import create_app, db
from app.models import User, Role
import pymysql
from config import Config
import re

def init_database():
    """初始化数据库"""
    # 解析数据库URL
    pattern = r'mysql\+pymysql://([^:]+):([^@]+)@([^/]+)/([^?]+)'
    match = re.match(pattern, Config.SQLALCHEMY_DATABASE_URI)
    if not match:
        print("无法解析数据库URL")
        return
    
    user, password, host, dbname = match.groups()
    
    # 连接MySQL服务器（不指定数据库）
    conn = pymysql.connect(
        host=host,
        user=user,
        password=password
    )
    
    try:
        with conn.cursor() as cursor:
            # 删除数据库（如果存在）
            cursor.execute(f"DROP DATABASE IF EXISTS {dbname}")
            # 创建新数据库
            cursor.execute(f"CREATE DATABASE {dbname} CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci")
            print(f"数据库 {dbname} 已重新创建")
    finally:
        conn.close()
    
    # 创建应用上下文
    app = create_app()
    with app.app_context():
        # 创建所有表
        db.create_all()
        print("数据库表创建成功")
        
        # 创建角色
        roles_info = {
            'admin': '系统管理员',
            'agent': '代理商',
            'staff': '员工',
            'user': '普通用户'
        }
        
        for role_name, description in roles_info.items():
            role = Role(name=role_name, description=description)
            db.session.add(role)
        
        db.session.commit()
        print("角色初始化成功")
        
        # 创建管理员账户
        admin_role = Role.query.filter_by(name='admin').first()
        admin = User(
            username='admin',
            email='admin@example.com',
            role=admin_role,
            is_active=True,
            is_admin=True
        )
        admin.password = 'admin123'
        db.session.add(admin)
        db.session.commit()
        print("管理员账户创建成功")
        
        # 创建代理账户
        agent_role = Role.query.filter_by(name='agent').first()
        agent = User(
            username='agent',
            email='agent@example.com',
            role=agent_role,
            is_active=True
        )
        agent.password = 'agent123'
        db.session.add(agent)
        db.session.commit()
        print("代理账户创建成功")
        
        # 创建员工账户
        staff_role = Role.query.filter_by(name='staff').first()
        staff = User(
            username='staff',
            email='staff@example.com',
            role=staff_role,
            is_active=True,
            referrer=agent  # 设置代理为推荐人
        )
        staff.password = 'staff123'
        db.session.add(staff)
        db.session.commit()
        print("员工账户创建成功")
        
        # 创建测试用户账户
        user_role = Role.query.filter_by(name='user').first()
        test_user = User(
            username='test_user',
            email='user@example.com',
            role=user_role,
            is_active=True,
            referrer=staff  # 设置员工为推荐人
        )
        test_user.password = 'user123'
        db.session.add(test_user)
        db.session.commit()
        print("测试用户账户创建成功")

if __name__ == '__main__':
    init_database()