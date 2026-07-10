"""
SimCore — إعدادات النظام
قسم مستقل داخل CoBWeaverClaw (محرك مراقبة/تتبع/قرار متعدد الوكلاء)
"""
import os
from dataclasses import dataclass, field
from typing import Optional

# التخصصات المتاحة
DOMAINS = [
    "general",      # عام — شامل لكل شيء
    "trading",      # تداول
    "medicine",     # طب
    "engineering",  # هندسة
    "law",          # قانون
    "marketing",    # تسويق
    "security",     # أمن معلومات
    "education",    # تعليم
    "politics",     # سياسة
    "other",        # أخرى — يكتبها المستخدم
]

# مستويات نشاط الوكيل
AGENT_ACTIVITY = {
    "background": "خلفي مستمر — نموذج رخيص",
    "deep":       "تحليل عميق عند الطلب — نموذج أقوى",
}

@dataclass
class SourceConfig:
    """إعدادات مصدر بيانات واحد"""
    url:         str
    name:        str
    api_key:     Optional[str] = None
    account_id:  Optional[str] = None
    connected:   bool          = False
    source_type: str           = "web"   # web | api | social

@dataclass
class AgentConfig:
    """إعدادات وكيل واحد"""
    agent_id:    str
    role:        str            # monitor | tracker | analyst | oracle
    domain:      str            = "general"
    model_key:   Optional[str] = None   # None = يرث من النظام
    model_url:   Optional[str] = None
    model_name:  Optional[str] = None
    activity:    str            = "background"
    sources:     list           = field(default_factory=list)

@dataclass
class SimCoreConfig:
    """الإعدادات الكاملة لـ SimCore"""
    domain:       str          = "general"
    domain_custom: str         = ""       # إذا domain == "other"
    mode:         str          = "general" # general | specialized
    global_model_key:  Optional[str] = None
    global_model_url:  Optional[str] = None
    global_model_name: Optional[str] = None
    sources:      list         = field(default_factory=list)
    platforms:    list         = field(default_factory=list)  # منصات api/social/exchange
    agents:       list         = field(default_factory=list)
    executor_enabled: bool     = False   # ExecutorAgent مُعطَّل افتراضياً
    deep_research:    bool      = False   # تشغيل ResearchAgent ضمن الدورة
    research_query:   str       = ""      # موضوع البحث المعمّق (اختياري)
