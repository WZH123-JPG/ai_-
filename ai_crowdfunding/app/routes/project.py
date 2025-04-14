from flask import Blueprint, render_template, redirect, url_for, flash, request
from flask_login import login_required, current_user
from .. import db
from ..models import Project, Investment, User
from datetime import datetime

bp = Blueprint('project', __name__, url_prefix='/projects')

@bp.route('/')
def project_list():
    """项目列表页面"""
    # 获取筛选参数
    status = request.args.get('status', 'active')
    sort = request.args.get('sort', 'latest')
    
    # 构建查询
    query = Project.query
    
    # 应用状态筛选
    if status != 'all':
        query = query.filter_by(status=status)
    
    # 应用排序
    if sort == 'latest':
        query = query.order_by(Project.created_at.desc())
    elif sort == 'roi':
        query = query.order_by(Project.daily_roi.desc())
    elif sort == 'amount':
        query = query.order_by(Project.target_amount.desc())
    
    # 获取项目列表
    projects = query.all()
    
    return render_template('project/project_list.html',
                         projects=projects,
                         current_status=status,
                         current_sort=sort)

@bp.route('/project/<int:id>')
def project_detail(id):
    project = Project.query.get_or_404(id)
    source = request.args.get('source', 'index')  # 默认来源为首页
    return render_template('project/detail.html', project=project, source=source)

@bp.route('/project/<int:id>/invest', methods=['GET', 'POST'])
@login_required
def invest(id):
    project = Project.query.get_or_404(id)
    
    if request.method == 'POST':
        try:
            shares = int(request.form['shares'])
            amount = shares * project.share_price
            
            if shares <= 0:
                flash('份额必须大于0', 'error')
                return redirect(url_for('project.invest', id=id))
                
            if shares > project.remaining_shares:
                flash('超出可用份额', 'error')
                return redirect(url_for('project.invest', id=id))
            
            # 重新从数据库加载用户对象
            user = User.query.get(current_user.id)
            if amount > user.balance:
                flash('余额不足', 'error')
                return redirect(url_for('project.invest', id=id))
            
            # 开始数据库事务
            try:
                # 创建投资记录
                investment = Investment(
                    user_id=user.id,
                    project_id=project.id,
                    shares=shares,
                    amount=amount,
                    status='active'
                )
                
                # 更新项目状态
                project.remaining_shares -= shares
                project.current_amount += amount
                
                # 更新用户余额
                user.balance -= amount
                
                # 添加所有更改到会话
                db.session.add(investment)
                
                # 提交事务
                db.session.commit()
                
                flash('投资成功！', 'success')
                return redirect(url_for('project.project_detail', id=id))
                
            except Exception as e:
                # 如果出现错误，回滚事务
                db.session.rollback()
                flash('投资失败，请稍后重试', 'error')
                return redirect(url_for('project.invest', id=id))
                
        except ValueError:
            flash('请输入有效的份额数量', 'error')
            return redirect(url_for('project.invest', id=id))
            
    return render_template('project/invest.html', project=project)