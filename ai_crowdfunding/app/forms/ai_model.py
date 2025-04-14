from flask_wtf import FlaskForm
from wtforms import StringField
from wtforms.validators import DataRequired, URL, Length

class AIModelForm(FlaskForm):
    model_name = StringField('模型名称', validators=[
        DataRequired(message='请输入模型名称'),
        Length(max=100, message='模型名称不能超过100个字符')
    ])
    base_url = StringField('基础URL', validators=[
        DataRequired(message='请输入基础URL'),
        URL(message='请输入有效的URL地址')
    ])
    api_key = StringField('API密钥', validators=[
        DataRequired(message='请输入API密钥'),
        Length(min=8, message='API密钥长度至少为8个字符')
    ])
    ai_model = StringField('模型类型', validators=[
        DataRequired(message='请输入模型类型'),
        Length(max=100, message='模型类型不能超过100个字符')
    ])