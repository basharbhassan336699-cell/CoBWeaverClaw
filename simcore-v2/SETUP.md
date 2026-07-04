# SimCore — تعليمات التشغيل

## المتطلبات الأساسية (إلزامية)
- Python 3.11+
- Node.js 18+
- مفتاح LLM API (Anthropic / OpenAI / OpenRouter / أي مزود)

## خطوات التشغيل

### 1. إعداد البيئة
```bash
cp .env.example .env
# افتح .env وأضف:
# LLM_API_KEY=مفتاحك
# LLM_BASE_URL=https://api.openai.com/v1   (أو مزودك)
# LLM_MODEL_NAME=gpt-4o-mini
```

### 2. تثبيت Backend
```bash
cd backend
pip install -r requirements.txt
```

### 3. تشغيل Backend
```bash
python run.py
# يعمل على http://localhost:5000
```

### 4. تثبيت وتشغيل Frontend
```bash
cd frontend
npm install
npm run dev
# يعمل على http://localhost:5173
```

---

## SimCore — قسم الوكلاء الذكيين

افتح المتصفح على `/simcore`

### الاستخدام:
1. اختر التوجه (تداول / طب / هندسة / ...)
2. أضف مصادر — أي رابط موقع أو API
3. اختبر الاتصال — النظام يكتشف تلقائياً إذا احتاج مفتاح أو ID
4. أضف المفاتيح لكل وكيل أو اتركها ترث المفتاح العام
5. شغّل التحليل — monitor → tracker → OracleAgent

### الوكلاء:
- **MonitorAgent** — يراقب المنصات والـ APIs المرتبطة بمفتاح
- **TrackerAgent** — يتتبع مواقع الويب ويستخرج محتوى
- **OracleAgent** — يجمع النتائج ويصدر قراراً نهائياً

---

## المحاكاة الأصلية (اختيارية)

تحتاج إضافياً:
```
ZEP_API_KEY=مفتاحك من app.getzep.com  (مجاني)
```

المحاكاة الاجتماعية (camel-oasis) تعمل تلقائياً مع requirements.txt
