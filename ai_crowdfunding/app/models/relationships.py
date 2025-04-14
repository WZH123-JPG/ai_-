"""
这个模块用于定义所有模型之间的关系，避免循环导入问题。
在所有模型类都定义完成后，调用 setup_relationships() 函数来建立关系。
"""
from app.extensions import db

def setup_relationships():
    """设置所有模型之间的关系"""
    # 导入所有需要的模型
    from .user import User
    from .investment import Investment
    from .withdrawal import Withdrawal
    from .daily_profit import DailyProfit
    from .referral_bonus import ReferralBonus
    
    # 所有关系已经在各自的模型中定义，这里不需要重复定义
    pass 