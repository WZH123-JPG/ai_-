from app import create_app, db
from app.models import User, Project, Investment
from datetime import datetime, timedelta

def add_test_data():
    app = create_app()
    with app.app_context():
        # 添加测试用户
        test_user = User(
            username='testuser2',
            email='test2@example.com',
            is_active=True,
            is_admin=False,
            balance=0,
            referral_code='TEST456'
        )
        test_user.set_password('123456')
        db.session.add(test_user)
        
        # 添加测试项目
        test_project = Project(
            name='测试项目',
            description='这是一个测试项目',
            target_amount=50000,
            current_amount=0,
            share_price=100,
            total_shares=500,
            remaining_shares=500,
            daily_roi=0.01,
            start_date=datetime.now(),
            end_date=datetime.now() + timedelta(days=30),
            status='funding'
        )
        db.session.add(test_project)
        
        # 提交更改以获取 ID
        db.session.commit()
        
        # 添加测试投资
        test_investment = Investment(
            user_id=test_user.id,
            project_id=test_project.id,
            amount=1000,
            shares=10,
            created_at=datetime.now(),
            profit=100
        )
        db.session.add(test_investment)
        
        # 最终提交
        db.session.commit()
        print("测试数据添加成功！")

if __name__ == '__main__':
    add_test_data()