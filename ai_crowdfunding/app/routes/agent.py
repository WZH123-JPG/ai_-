from flask import Blueprint, render_template, redirect, url_for, flash, request, jsonify, current_app
from flask_login import login_required, current_user
from ..extensions import db, csrf
from ..models import User, Withdrawal, ReferralBonus, Investment, Recharge, WithdrawConfig, ReferralRate, DailyProfit, ChatSession, ChatMessage, ChatModels
from datetime import datetime, timedelta
from sqlalchemy import func
import random
import string
import os
from werkzeug.utils import secure_filename
import re
from openai import OpenAI
import traceback
import logging
from ..tools.model_api import call_model_api

bp = Blueprint('agent', __name__, url_prefix='/agent')

# 设置日志记录
logger = logging.getLogger(__name__)

# def call_model_api(user_message, model_id=None):
#     # 获取选择的模型配置
#     try:
#         if model_id:
#             model = ChatModels.query.get(model_id)
#         else:
#             # 如果没有指定模型ID，使用第一个可用的模型
#             model = ChatModels.query.filter_by(is_active=True).first()
#
#         if not model:
#             raise Exception("没有可用的AI模型")
#
#         # 使用模型配置调用API
#         try:
#             print(user_message)
#             client = OpenAI(api_key=f"{model.api_key}", base_url=f"{model.base_url}")
#             response = client.chat.completions.create(
#                 model=f"{model.ai_model}",
#                 messages=[
#                     {"role": "system", "content": "你是一个专业的AI助手，请用专业、友好的语气回答用户的问题，避免使用表情符号。"},
#                     {"role": "user", "content": user_message},
#                 ],
#                 stream=False
#             )
#
#             content = response.choices[0].message.content
#             # 移除表情符号
#             content = re.sub(r'[\U0001F600-\U0001F64F\U0001F300-\U0001F5FF\U0001F680-\U0001F6FF\U0001F1E0-\U0001F1FF]', '', content)
#             logger.info(f"AI回复: {content}")
#             return content
#         except Exception as api_error:
#             error_message = str(api_error).lower()
#             if "authentication" in error_message or "api key" in error_message:
#                 raise Exception(f"模型 {model.model_name} 的API密钥无效，请联系管理员更新API密钥")
#             elif "quota" in error_message or "credit" in error_message:
#                 raise Exception(f"模型 {model.model_name} 的API额度不足")
#             elif "model" in error_message and "not found" in error_message:
#                 raise Exception(f"模型 {model.model_name} 的模型类型 {model.ai_model} 不存在，请检查配置")
#             elif "rate limit" in error_message:
#                 raise Exception(f"模型 {model.model_name} 的请求频率过高，请稍后再试")
#             else:
#                 raise Exception(f"调用模型 {model.model_name} 时出错: {str(api_error)}")
#     except Exception as e:
#         logger.error(f"调用模型API出错: {str(e)}\n{traceback.format_exc()}")
#         raise

# 获取用户的所有聊天会话
@bp.route('/sessions')
@login_required
def get_sessions():
    try:
        sessions = ChatSession.query.filter_by(user_id=current_user.id).order_by(ChatSession.updated_at.desc()).all()
        return jsonify([{
            'id': session.id,
            'title': session.title or '新会话',
            'created_at': session.created_at.strftime('%Y-%m-%d %H:%M:%S')
        } for session in sessions])
    except Exception as e:
        logger.error(f"获取会话列表失败: {str(e)}\n{traceback.format_exc()}")
        return jsonify({"error": "获取会话列表失败"}), 500

# 删除会话
@bp.route('/sessions/<int:session_id>', methods=['DELETE'])
@login_required
def delete_session(session_id):
    try:
        # 验证会话归属
        session = ChatSession.query.filter_by(id=session_id, user_id=current_user.id).first_or_404()
        
        # 删除会话相关的所有消息
        ChatMessage.query.filter_by(session_id=session_id).delete()
        
        # 删除会话
        db.session.delete(session)
        db.session.commit()
        
        logger.info(f"会话删除成功，ID: {session_id}")
        return jsonify({"message": "会话删除成功"})
        
    except Exception as e:
        db.session.rollback()
        error_msg = f"删除会话失败: {str(e)}\n{traceback.format_exc()}"
        logger.error(error_msg)
        return jsonify({"error": "删除会话失败"}), 500

# 获取特定会话的消息记录
@bp.route('/messages/<int:session_id>')
@login_required
def get_messages(session_id):
    try:
        session = ChatSession.query.filter_by(id=session_id, user_id=current_user.id).first_or_404()
        messages = ChatMessage.query.filter_by(session_id=session_id).order_by(ChatMessage.created_at).all()
        return jsonify([{
            'content': msg.content,
            'is_user': msg.is_user,
            'created_at': msg.created_at.strftime('%Y-%m-%d %H:%M:%S')
        } for msg in messages])
    except Exception as e:
        logger.error(f"获取消息记录失败: {str(e)}\n{traceback.format_exc()}")
        return jsonify({"error": "获取消息记录失败"}), 500

# 创建新会话
@bp.route('/sessions/new', methods=['POST'])
@login_required
def create_session():
    try:
        logger.info(f"用户 {current_user.id} 正在创建新会话")
        session = ChatSession(user_id=current_user.id)
        db.session.add(session)
        db.session.commit()
        logger.info(f"新会话创建成功，ID: {session.id}")
        return jsonify({
            'id': session.id,
            'created_at': session.created_at.strftime('%Y-%m-%d %H:%M:%S')
        })
    except Exception as e:
        db.session.rollback()
        error_msg = f"创建会话失败: {str(e)}\n{traceback.format_exc()}"
        logger.error(error_msg)
        return jsonify({"error": str(e)}), 500

# 路由：提供前端页面
@bp.route('/talk')
@login_required
def talk():
    # 获取所有可用的模型
    models = ChatModels.query.filter_by(is_active=True).all()
    return render_template('agent/talk.html', models=models)

# 路由：接收用户消息并返回模型回复
@bp.route('/chat', methods=['POST'])
@login_required
def chat():
    try:
        data = request.json
        user_message = data.get('message', '').strip()
        session_id = data.get('session_id')
        model_id = data.get('model_id', None)  # 获取选择的模型ID
        
        logger.info(f"收到用户 {current_user.id} 的消息，会话ID: {session_id}")

        if not user_message:
            return jsonify({"error": "消息不能为空"}), 400
        
        if not session_id:
            return jsonify({"error": "会话ID不能为空"}), 400

        # 验证会话归属
        session = ChatSession.query.filter_by(id=session_id, user_id=current_user.id).first()
        if not session:
            logger.warning(f"无效的会话ID: {session_id}")
            return jsonify({"error": "无效的会话ID"}), 404

        # 保存用户消息
        user_chat_message = ChatMessage(
            session_id=session_id,
            content=user_message,
            is_user=True
        )
        db.session.add(user_chat_message)

        # 如果是会话的第一条消息，设置会话标题
        if not session.title:
            session.title = user_message[:20] + ('...' if len(user_message) > 20 else '')

        try:
            # 调用模型接口获取回复
            model_response = call_model_api(user_message, model_id)
            
            # 保存AI回复
            ai_chat_message = ChatMessage(
                session_id=session_id,
                content=model_response,
                is_user=False
            )
            db.session.add(ai_chat_message)
            
            # 更新会话时间
            session.updated_at = datetime.utcnow()
            db.session.commit()
            
            logger.info(f"消息处理成功，会话ID: {session_id}")
            return jsonify({"response": model_response})
            
        except Exception as e:
            db.session.rollback()
            error_msg = f"AI回复失败: {str(e)}\n{traceback.format_exc()}"
            logger.error(error_msg)
            return jsonify({"error": f"AI回复失败: {str(e)}"}), 500
            
    except Exception as e:
        error_msg = f"请求处理失败: {str(e)}\n{traceback.format_exc()}"
        logger.error(error_msg)
        return jsonify({"error": f"请求处理失败: {str(e)}"}), 500