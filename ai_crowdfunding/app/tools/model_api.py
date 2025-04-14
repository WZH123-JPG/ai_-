from ..models import ChatModels
from openai import OpenAI
import logging
import re
import traceback


# 设置日志记录
logger = logging.getLogger(__name__)


def call_model_api(user_message, model_id=None):
    # 获取选择的模型配置
    try:
        if model_id:
            model = ChatModels.query.get(model_id)
        else:
            # 如果没有指定模型ID，使用第一个可用的模型
            model = ChatModels.query.filter_by(is_active=True).first()

        if not model:
            raise Exception("没有可用的AI模型")

        # 使用模型配置调用API
        try:
            print(user_message)
            client = OpenAI(api_key=f"{model.api_key}", base_url=f"{model.base_url}")
            response = client.chat.completions.create(
                model=f"{model.ai_model}",
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
            return content
        except Exception as api_error:
            error_message = str(api_error).lower()
            if "authentication" in error_message or "api key" in error_message:
                raise Exception(f"模型 {model.model_name} 的API密钥无效，请联系管理员更新API密钥")
            elif "quota" in error_message or "credit" in error_message:
                raise Exception(f"模型 {model.model_name} 的API额度不足")
            elif "model" in error_message and "not found" in error_message:
                raise Exception(f"模型 {model.model_name} 的模型类型 {model.ai_model} 不存在，请检查配置")
            elif "rate limit" in error_message:
                raise Exception(f"模型 {model.model_name} 的请求频率过高，请稍后再试")
            else:
                raise Exception(f"调用模型 {model.model_name} 时出错: {str(api_error)}")
    except Exception as e:
        logger.error(f"调用模型API出错: {str(e)}\n{traceback.format_exc()}")
        raise