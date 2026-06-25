# 🕷️ CoBWeaverClaw — دليل الاستخدام الكامل

## فهرس المحتويات
1. متطلبات التشغيل
2. التثبيت
3. الإعداد الأولي
4. تشغيل الوكيل
5. الأوامر الكاملة (11 فئة)
6. لوحة التحكم
7. ربط النماذج
8. نظام التوكينات
9. المتصفح الداخلي
10. التعلم الذاتي
11. التداول (Swarm Engine)
12. استكشاف الأخطاء
13. الهجرة من OpenClaw / Hermes

---

## 1. متطلبات التشغيل

| المنصة | الحد الأدنى |
|--------|-------------|
| Android/Termux | Python 3.10+, 2GB RAM |
| iPhone/iSH | Python 3.10+, 2GB RAM |
| Linux/VPS | Python 3.10+, 1GB RAM |
| Windows | Python 3.10+, Windows 10+ |
| macOS | Python 3.10+, macOS 12+ |
| Raspberry Pi | Python 3.10+, Pi 4 / 2GB |

---

## 2. التثبيت

### سطر واحد — كل المنصات

```bash
# Linux / macOS / Android Termux / iPhone iSH / Raspberry Pi
curl -sSL https://get.cobweaverclaw.ai | bash

# Windows (PowerShell)
irm https://get.cobweaverclaw.ai/win | iex
```

### تثبيت يدوي

```bash
# 1. استنساخ المشروع
git clone https://github.com/basharbhassan336699-cell/CoBWeaverClaw
cd CoBWeaverClaw

# 2. تثبيت المكتبات
pip install -r requirements.txt

# 3. إعداد مفتاح Claude API
export ANTHROPIC_API_KEY="your_key_here"

# 4. تشغيل الوكيل
python main.py
```

### Android/Termux تحديداً

```bash
pkg update && pkg upgrade -y
pkg install python git -y
pip install pyyaml aiohttp
git clone https://github.com/basharbhassan336699-cell/CoBWeaverClaw
cd CoBWeaverClaw
export ANTHROPIC_API_KEY="your_key"
python main.py
```

---

## 3. الإعداد الأولي

افتح `config.yaml` وعدّل:

```yaml
agent:
  language: ar           # ar أو en أو auto
  specialization: general  # general / trading / medicine ...

brain:
  primary: claude-sonnet-4-6   # للتحليل العميق
  fast: groq/llama-3.3-70b     # للردود السريعة
  local: ollama/mistral         # بدون إنترنت

interfaces:
  telegram:
    enabled: true
    token: "BOT_TOKEN_FROM_BOTFATHER"
```

---

## 4. تشغيل الوكيل

```bash
# CLI تفاعلي
python main.py

# تشخيص سريع
python main.py doctor

# إصلاح تلقائي
python main.py doctor --fix

# إصلاح كامل
python main.py doctor --fix --full

# حالة الوكيل
python main.py status

# بوت Telegram
python main.py telegram

# لوحة التحكم الويب
python main.py dashboard
# ثم افتح: http://localhost:8080
```

---

## 5. الأوامر الكاملة

### فئة 1 — الاكتشاف

```bash
agent scan              # اكتشاف الجهاز والبيئة
agent scan --deep       # فحص شامل
agent scan --models     # النماذج المحلية المتاحة
agent scan --ports      # فحص المنافذ
agent scan --net        # اختبار الاتصال بكل API
```

### فئة 2 — التشخيص

```bash
agent doctor                  # تشخيص بدون تغيير
agent doctor --fix            # تشخيص + إصلاح تلقائي
agent doctor --fix --full     # دورة إصلاح كاملة (30-60 ثانية)
agent doctor --fix --dry-run  # يُظهر ما سيُصلح بدون تنفيذ
agent doctor --memory         # فحص الذاكرة فقط
agent doctor --skills         # فحص Skills فقط
agent doctor --models         # فحص النماذج ومفاتيح API
agent doctor --security       # فحص أمني شامل
agent doctor --report         # تصدير تقرير JSON
```

### فئة 3 — الإصلاح

```bash
agent fix                # إصلاح كل المشاكل المكتشفة
agent fix --config       # إعادة بناء الإعدادات
agent fix --memory       # إصلاح قاعدة الذاكرة
agent fix --permissions  # إصلاح صلاحيات الملفات
agent fix --gateway      # إعادة تشغيل البوابة
agent fix --skills       # إعادة تفعيل Skills المعطّلة
agent fix --reset-model X  # إعادة إعداد نموذج محدد
```

### فئة 4 — المراقبة

```bash
agent status             # الحالة المختصرة
agent status --all       # كل شيء بالتفصيل
agent status --live      # مراقبة حية كل 5 ثوانٍ
agent logs               # آخر 50 سطر
agent logs --tail        # سجل مستمر
agent logs --errors      # الأخطاء فقط
agent logs --skill web   # سجل skill محددة
agent monitor            # TUI حي في الطرفية
```

### فئة 5 — الذاكرة

```bash
agent memory status          # حجم الاستخدام
agent memory search "نص"     # بحث في الذاكرة
agent memory clean           # حذف القديم غير المهم
agent memory export          # تصدير نسخة احتياطية
agent memory import file.db  # استيراد من نسخة
agent memory rebuild         # إعادة بناء Embeddings
```

### فئة 6 — النماذج

```bash
agent models list         # كل النماذج وحالتها
agent models test         # اختبار كل نموذج
agent models add          # إضافة نموذج جديد
agent models remove X     # حذف نموذج
agent models set-role X   # تخصيص دور لنموذج
agent models benchmark    # مقارنة أداء النماذج
agent models auth X       # تحديث مفتاح API
```

### فئة 7 — المهارات

```bash
agent skills list         # كل Skills وحالتها
agent skills add X        # تثبيت skill
agent skills remove X     # حذف skill
agent skills enable X     # تفعيل
agent skills disable X    # تعطيل
agent skills test X       # اختبار skill محددة
agent skills build        # بناء skill من وصف نصي
agent skills score        # تقييم أداء كل skill
```

### فئة 8 — الاتصالات

```bash
agent channels list       # كل القنوات
agent channels add        # إضافة قناة
agent channels test X     # اختبار قناة
agent channels remove X   # حذف قناة
agent connect X           # ربط سريع
agent webhook add         # إضافة webhook
```

### فئة 9 — الأمان والتوكينات

```bash
agent auth status         # حالة كل المصادقات
agent auth refresh        # تجديد Tokens المنتهية
agent token create        # إنشاء توكين جديد
agent token revoke X      # إلغاء توكين
agent token list          # الأجهزة المرتبطة
agent security audit      # فحص أمني شامل
agent security harden     # تطبيق أفضل الإعدادات الأمنية
```

### فئة 10 — الجدولة

```bash
agent cron list           # المهام المجدولة
agent cron add            # إضافة مهمة
agent cron remove X       # حذف مهمة
agent cron run X          # تشغيل فوري
agent learn now           # تشغيل التعلم الذاتي فوراً
agent learn --from web    # تعلم من الويب
agent learn status        # آخر دورة تعلم
```

### فئة 11 — الصيانة

```bash
agent update              # تحديث للأحدث
agent backup              # نسخة احتياطية كاملة
agent restore file.bak    # استعادة من نسخة
agent migrate --from openclaw  # هجرة من OpenClaw
agent migrate --from hermes    # هجرة من Hermes
agent reset               # إعادة ضبط المصنع
agent reset --soft        # إعادة الإعدادات مع الحفاظ على الذاكرة
agent version             # النسخة الحالية
```

---

## 6. لوحة التحكم الويب

### التشغيل

```bash
# تثبيت FastAPI
pip install fastapi uvicorn

# تشغيل لوحة التحكم
uvicorn interfaces.dashboard.api:app --host 0.0.0.0 --port 8080

# افتح في المتصفح
http://localhost:8080
```

### صفحات لوحة التحكم

| الصفحة | الوظيفة |
|--------|---------|
| نظرة عامة | حالة الوكيل، إحصائيات الذاكرة والمهارات |
| الذاكرة | حجم الاستخدام، بحث في الذاكرة |
| النماذج | النماذج المتصلة، اختبار الأداء |
| المهارات | قائمة Skills، تفعيل/تعطيل |
| Doctor | تشخيص مرئي، إصلاح بزر واحد |
| السجلات | سجل المحادثات والنشاط |
| التوكينات | إنشاء وتحقق من Tokens |
| الإعدادات | معلومات النظام، التعلم الذاتي |

### تسجيل الدخول

- **Master Token**: أدخله مباشرة في حقل الدخول
- **تجربة**: اضغط "تجربة" لبيانات افتراضية بدون توكين

---

## 7. ربط النماذج

### Claude (Anthropic)

```bash
export ANTHROPIC_API_KEY="sk-ant-..."
```

أو في `config.yaml`:
```yaml
brain:
  primary: claude-sonnet-4-6
```

### Groq

```bash
export GROQ_API_KEY="gsk_..."
```

### Ollama (محلي — بدون إنترنت)

```bash
# تثبيت Ollama
curl -sSL https://ollama.ai/install.sh | sh

# تحميل نموذج
ollama pull mistral

# الوكيل يكتشفه تلقائياً
```

### تخصيص أدوار النماذج

```yaml
brain:
  primary: claude-sonnet-4-6    # التحليل العميق والمعقد
  fast: groq/llama-3.3-70b      # الردود السريعة اليومية
  local: ollama/qwen2.5         # العمل بدون إنترنت
  coding: groq/llama-3.3-70b    # مهام البرمجة
  arabic: ollama/qwen2.5        # اللغة العربية تحديداً
```

---

## 8. نظام التوكينات

### إنشاء أول توكين

```python
from auth.tokens import TokenManager
tm = TokenManager()

# Master Token — احفظه في مكان آمن
master = tm.create_master_token("your_user_id")
print(master)

# Device Token للجهاز الحالي
device = tm.create_device_token(master, "my_android")
print(device)
```

### استعادة الحساب على جهاز جديد

1. أدخل Master Token في لوحة التحكم أو CLI
2. الوكيل يُنشئ Device Token جديد تلقائياً
3. كل بياناتك محفوظة

### أين تحفظ Master Token؟

✅ Password Manager (Bitwarden, 1Password)
✅ ملف مشفر على Google Drive
✅ ورقة مكتوبة في مكان آمن
❌ لا تحفظه في الهاتف فقط

---

## 9. المتصفح الداخلي

### الوضع اليدوي (Phase 2)

```bash
agent browser open https://example.com
agent browser search "أفضل GPU للتداول"
```

### الوضع التلقائي

```
أنت: ابحث عن آخر أخبار Bitcoin
الوكيل: يفتح المتصفح → يبحث → يقرأ → يلخص → يردّ
```

### المواقع المفضلة

```yaml
browser:
  favorites:
    - name: Binance
      url: https://www.binance.com
    - name: CoinGecko
      url: https://www.coingecko.com
```

---

## 10. التعلم الذاتي

### دورة التعلم التلقائية

```
كل يوم:
  → يقرأ مصادر المجال المحدد
  → يلخص ويخزن في الذاكرة

كل أسبوع (الأحد 2:00 صباحاً):
  → يراجع المهام السابقة
  → يكتب Skills جديدة من النجاحات
  → يحذف Skills ضعيفة الأداء
  → يُحدّث الأوزان الداخلية

عند كل خطأ:
  → يسجّل الدرس
  → يمنع تكرار نفس الخطأ
```

### تشغيل يدوي

```bash
agent learn now           # فوراً
agent learn --from web    # من الويب
agent learn status        # آخر نتائج
```

---

## 11. محرك التداول (Swarm Engine)

### الإعداد

```yaml
agent:
  specialization: trading

swarm:
  enabled: true
  agents_count: 50          # عدد المتداولين الرقميين
  simulation_timeout_seconds: 30
```

### دورة التحليل الكاملة

```
1. بيانات Binance + CoinGecko + DeFiLlama
2. GraphRAG يبني خريطة السوق
3. 50 متداول رقمي يتفاعلون
4. تحليل ICT + Wyckoff + CVD
5. قرار بمستوى ثقة %
6. زر موافقة في Telegram
7. تنفيذ على Binance
8. الوكيل يتعلم من النتيجة
```

---

## 12. استكشاف الأخطاء

### الوكيل لا يبدأ

```bash
python main.py doctor
# يشخص المشكلة ويقترح الحل

python main.py doctor --fix
# يصلح تلقائياً
```

### مفتاح API لا يعمل

```bash
agent models auth claude
# يطلب المفتاح ويختبره
```

### الذاكرة تالفة

```bash
agent fix --memory
# يُصلح أو يُعيد بناء قاعدة الذاكرة
```

### الوكيل بطيء

```bash
agent models benchmark
# يقارن النماذج ويوصي بالأسرع
```

---

## 13. الهجرة من المنافسين

### من OpenClaw

```bash
agent migrate --from openclaw
# يستورد: إعدادات + ذاكرة + Skills + مفاتيح API
```

### من Hermes

```bash
agent migrate --from hermes
# يستورد: SQLite + Skills + إعدادات Telegram
```

---

## الدعم والمجتمع

- **GitHub Issues**: https://github.com/basharbhassan336699-cell/CoBWeaverClaw/issues
- **البريد الأمني**: security@cobweaverclaw.ai
- **التوثيق**: https://github.com/basharbhassan336699-cell/CoBWeaverClaw/docs

---

*CoBWeaverClaw — The agent that weaves intelligence into every thread.*
