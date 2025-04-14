from app.models import ChatModels
from flask import Blueprint, render_template, redirect, url_for, flash, request, jsonify, current_app
from flask_login import login_required, current_user
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

logger = logging.getLogger(__name__)


def call_model_api(user_message, model_id=None):
    # 使用模型配置调用API
    print(user_message)
    client = OpenAI(api_key="sk-6442233247e14d5baad88a7b34afae35", base_url="https://api.deepseek.com")
    response = client.chat.completions.create(
        model="deepseek-chat",
        messages=[
            {"role": "system",
             "content": "你是一个专业的AI助手，请用专业、友好的语气回答用户的问题，避免使用表情符号。"},
            {"role": "user", "content": user_message},
        ],
        stream=False
    )

    content = response.choices[0].message.content
    # 移除表情符号
    content = re.sub(r'[\U0001F600-\U0001F64F\U0001F300-\U0001F5FF\U0001F680-\U0001F6FF\U0001F1E0-\U0001F1FF]',
                     '', content)
    logger.info(f"AI回复: {content}")
    print(content)
    return content


if __name__ == '__main__':
    call_model_api("你好", model_id=1)
