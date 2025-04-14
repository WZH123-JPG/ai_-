from app import create_app
from app.models import Project
from datetime import datetime

def check_projects():
    app = create_app()
    with app.app_context():
        projects = Project.query.all()
        print("\n当前项目状态：")
        print("-" * 50)
        for project in projects:
            print(f"项目名称：{project.name}")
            print(f"目标金额：{project.target_amount}")
            print(f"当前金额：{project.current_amount}")
            print(f"开始时间：{project.start_date}")
            print(f"结束时间：{project.end_date}")
            print(f"状态：{project.status}")
            print("-" * 50)

if __name__ == '__main__':
    check_projects() 