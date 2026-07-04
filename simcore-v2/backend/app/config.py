"""
配置管理
统一从项目根目录的 .env 文件加载配置
"""

import os
from dotenv import load_dotenv

# 加载项目根目录的 .env 文件
# 路径: SimCore/.env (相对于 backend/app/config.py)
project_root_env = os.path.join(os.path.dirname(__file__), '../../.env')

if os.path.exists(project_root_env):
    load_dotenv(project_root_env, override=True)
else:
    # 如果根目录没有 .env，尝试加载环境变量（用于生产环境）
    load_dotenv(override=True)

# ── تكامل CoBWeaverClaw: مفاتيح الوكيل الموحّدة ──────────────────
# يحمّل ~/.cobweaverclaw/.env كاحتياط (بلا override — ملف SimCore المحلي أولاً)
# فتعمل مفاتيح وكيلك هنا مباشرة بلا إعداد مكرر.
_agent_env = os.path.join(os.path.expanduser("~"), ".cobweaverclaw", ".env")
if os.path.exists(_agent_env):
    load_dotenv(_agent_env, override=False)


def _agent_llm_fallback():
    """يرث LLM من مزوّدات CoBWeaverClaw عند غياب LLM_API_KEY.

    يفحص مفاتيح المزوّدات بالترتيب ويعيد (key, base_url, model)
    بصيغة OpenAI SDK، أو (None, None, None) إن لم يوجد مفتاح.
    """
    providers = [
        ("OPENAI_API_KEY",     "https://api.openai.com/v1",      "gpt-4o-mini"),
        ("GROQ_API_KEY",       "https://api.groq.com/openai/v1", "llama-3.3-70b-versatile"),
        ("OPENROUTER_API_KEY", "https://openrouter.ai/api/v1",   "openai/gpt-4o-mini"),
        ("DEEPSEEK_API_KEY",   "https://api.deepseek.com",       "deepseek-chat"),
        ("MISTRAL_API_KEY",    "https://api.mistral.ai/v1",      "mistral-small-latest"),
        ("XAI_API_KEY",        "https://api.x.ai/v1",            "grok-2-latest"),
        ("MOONSHOT_API_KEY",   "https://api.moonshot.ai/v1",     "kimi-k2-0711-preview"),
        ("ZAI_API_KEY",        "https://api.z.ai/api/paas/v4",   "glm-4.6"),
    ]
    for env_key, base_url, model in providers:
        key = os.environ.get(env_key)
        if key:
            return key, base_url, model
    return None, None, None


_FB_KEY, _FB_URL, _FB_MODEL = (None, None, None)
if not os.environ.get('LLM_API_KEY'):
    _FB_KEY, _FB_URL, _FB_MODEL = _agent_llm_fallback()


class Config:
    """Flask配置类"""
    
    # Flask配置
    SECRET_KEY = os.environ.get('SECRET_KEY', 'simcore-secret-key')
    DEBUG = os.environ.get('FLASK_DEBUG', 'True').lower() == 'true'
    
    # JSON配置 - 禁用ASCII转义，让中文直接显示（而不是 \uXXXX 格式）
    JSON_AS_ASCII = False
    
    # LLM配置（统一使用OpenAI格式）— يرث من مزوّدات CoBWeaverClaw عند الغياب
    LLM_API_KEY = os.environ.get('LLM_API_KEY') or _FB_KEY
    LLM_BASE_URL = os.environ.get('LLM_BASE_URL') or _FB_URL or 'https://api.openai.com/v1'
    LLM_MODEL_NAME = os.environ.get('LLM_MODEL_NAME') or _FB_MODEL or 'gpt-4o-mini'
    
    # Zep配置
    ZEP_API_KEY = os.environ.get('ZEP_API_KEY')
    
    # 文件上传配置
    MAX_CONTENT_LENGTH = 50 * 1024 * 1024  # 50MB
    UPLOAD_FOLDER = os.path.join(os.path.dirname(__file__), '../uploads')
    ALLOWED_EXTENSIONS = {'pdf', 'md', 'txt', 'markdown'}
    
    # 文本处理配置
    DEFAULT_CHUNK_SIZE = 500  # 默认切块大小
    DEFAULT_CHUNK_OVERLAP = 50  # 默认重叠大小
    
    # OASIS模拟配置
    OASIS_DEFAULT_MAX_ROUNDS = int(os.environ.get('OASIS_DEFAULT_MAX_ROUNDS', '10'))
    OASIS_SIMULATION_DATA_DIR = os.path.join(os.path.dirname(__file__), '../uploads/simulations')
    
    # OASIS平台可用动作配置
    OASIS_TWITTER_ACTIONS = [
        'CREATE_POST', 'LIKE_POST', 'REPOST', 'FOLLOW', 'DO_NOTHING', 'QUOTE_POST'
    ]
    OASIS_REDDIT_ACTIONS = [
        'LIKE_POST', 'DISLIKE_POST', 'CREATE_POST', 'CREATE_COMMENT',
        'LIKE_COMMENT', 'DISLIKE_COMMENT', 'SEARCH_POSTS', 'SEARCH_USER',
        'TREND', 'REFRESH', 'DO_NOTHING', 'FOLLOW', 'MUTE'
    ]
    
    # Report Agent配置
    REPORT_AGENT_MAX_TOOL_CALLS = int(os.environ.get('REPORT_AGENT_MAX_TOOL_CALLS', '5'))
    REPORT_AGENT_MAX_REFLECTION_ROUNDS = int(os.environ.get('REPORT_AGENT_MAX_REFLECTION_ROUNDS', '2'))
    REPORT_AGENT_TEMPERATURE = float(os.environ.get('REPORT_AGENT_TEMPERATURE', '0.5'))
    

    # SimCore — إعدادات الوكلاء والمصادر
    # مفاتيح الوكلاء — تُقرأ من .env أو تُمرَّر مباشرة في كل طلب
    SIMCORE_MONITOR_KEY  = os.environ.get('SIMCORE_MONITOR_KEY',  None)
    SIMCORE_TRACKER_KEY  = os.environ.get('SIMCORE_TRACKER_KEY',  None)
    SIMCORE_ORACLE_KEY   = os.environ.get('SIMCORE_ORACLE_KEY',   None)
    SIMCORE_MONITOR_URL  = os.environ.get('SIMCORE_MONITOR_URL',  None)
    SIMCORE_TRACKER_URL  = os.environ.get('SIMCORE_TRACKER_URL',  None)
    SIMCORE_ORACLE_URL   = os.environ.get('SIMCORE_ORACLE_URL',   None)
    SIMCORE_MONITOR_MODEL = os.environ.get('SIMCORE_MONITOR_MODEL', None)
    SIMCORE_TRACKER_MODEL = os.environ.get('SIMCORE_TRACKER_MODEL', None)
    SIMCORE_ORACLE_MODEL  = os.environ.get('SIMCORE_ORACLE_MODEL',  None)

    # التوجهات المتاحة
    SIMCORE_DOMAINS = [
        'general', 'trading', 'medicine', 'engineering',
        'law', 'marketing', 'security', 'education', 'politics', 'other'
    ]

    @classmethod
    def validate(cls) -> list[str]:
        """验证必要配置"""
        errors: list[str] = []
        if not cls.LLM_API_KEY:
            errors.append("LLM_API_KEY 未配置")
        if not cls.ZEP_API_KEY:
            import logging
            logging.getLogger("simcore").warning("ZEP_API_KEY غير مضبوط — ميزات الذاكرة المتقدمة معطلة")
        return errors

