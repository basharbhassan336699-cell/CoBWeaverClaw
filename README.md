# CoBWeaverClaw

<div align="center">

<img src="assets/icon.svg" width="120" height="120" alt="CoBWeaverClaw Icon"
     style="border-radius:24px; margin-bottom:16px"/>

**وكيل ذكاء اصطناعي مفتوح المصدر | Open-Source AI Agent**

*The agent that weaves intelligence into every thread.*
*الوكيل الذي ينسج الذكاء في كل خيط.*

![License](https://img.shields.io/badge/license-MIT-blue)
![Platform](https://img.shields.io/badge/platform-Android%20%7C%20iOS%20%7C%20Linux%20%7C%20Windows%20%7C%20macOS-green)
![Language](https://img.shields.io/badge/language-Python%203.11+-yellow)
![Status](https://img.shields.io/badge/status-In%20Development-orange)

</div>

---

## ما هو CoBWeaverClaw؟

CoBWeaverClaw هو وكيل ذكاء اصطناعي مفتوح المصدر، منافس مباشر لـ **OpenClaw** و**Hermes Agent**، مبني بفلسفة واحدة:

> **وكيل تملكه أنت بالكامل — يعمل على جهازك، يتعلم منك، يتطور بذاته.**
> *Your agent. Your rules. Your machine. No cloud lock-in. No limits.*

---

## المقارنة مع المنافسين

| الميزة | OpenClaw | Hermes | **CoBWeaverClaw** |
|--------|----------|--------|-------------------|
| Android رسمي | ❌ | ❌ | ✅ |
| iOS رسمي | ❌ | ❌ | ✅ أول وكيل |
| Windows بدون WSL | ✅ | ❌ | ✅ |
| ذاكرة لا نهائية | ❌ | ❌ (15 فقط) | ✅ LightRAG |
| أمان مدمج | ❌ (9 CVEs) | ❌ (4 Critical) | ✅ Sandbox |
| تعلم ذاتي من الويب | ❌ | ❌ | ✅ |
| Swarm Trading Engine | ❌ | ❌ | ✅ حصري |
| متصفح داخلي | ❌ | ❌ | ✅ |
| نموذج خاص | ❌ | جزئي | ✅ Qwen Fine-tuned |

---

## التثبيت

```bash
# Linux / macOS / Android Termux / Raspberry Pi / iPhone iSH
curl -sSL https://get.cobweaverclaw.ai | bash

# Windows (PowerShell)
irm https://get.cobweaverclaw.ai/win | iex
```

---

## الميزات الرئيسية

- 🧠 **ذاكرة ثلاثية**: SQLite + LightRAG + ضغط تلقائي
- 🤖 **محرك نماذج ذكي**: Claude / Groq / GPT / Gemini / Ollama
- 🌐 **متصفح داخلي**: يدوي وتلقائي
- 📈 **Swarm Trading Engine**: محاكاة آلاف المتداولين
- 🔒 **Sandbox مدمج**: أمان من اليوم الأول
- 🎓 **Skill Factory**: يبني مهارات جديدة تلقائياً
- 🌍 **7 لغات**: العربية، الإنجليزية، الصينية، الفرنسية، الألمانية، اليابانية، الإسبانية

---

## البنية التقنية

```
CoBWeaverClaw/
├── core/          ← القلب الرئيسي
├── memory/        ← الذاكرة الثلاثية
├── brain/         ← محرك النماذج
├── skills/        ← Skill Factory + Evolver
├── swarm/         ← MiroFish Trading Engine
├── browser/       ← المتصفح الداخلي
├── interfaces/    ← Telegram + CLI + Dashboard
├── auth/          ← JWT + Trust Levels
├── commands/      ← 11 فئة أوامر
└── i18n/          ← 7 لغات
```

---

## أوامر سريعة

```bash
agent scan          # اكتشاف الجهاز
agent doctor --fix  # تشخيص وإصلاح تلقائي
agent status --live # مراقبة حية
agent learn now     # تعلم ذاتي فوري
agent migrate --from openclaw  # هجرة من OpenClaw
```

---

## خارطة الطريق

| المرحلة | التوقيت | المخرجات |
|---------|---------|----------|
| 1 — القلب | أسبوع 1-2 | Core + Memory + Telegram |
| 2 — النماذج | أسبوع 3-4 | Model Engine + Specialization |
| 3 — Skills | شهر 2 | Factory + Evolver + Sandbox |
| 4 — Swarm | شهر 2 | Trading Engine + Browser |
| 5 — Dashboard | شهر 3 | Web UI + Installer |
| 6 — النموذج | شهر 4-6 | Qwen Fine-tune + HuggingFace |

---

## المساهمة

نرحب بمساهمات المجتمع! اقرأ [CONTRIBUTING.md](CONTRIBUTING.md) للبدء.

---

## الترخيص

MIT License — مجاني بالكامل للاستخدام الشخصي والتجاري.

---

<div align="center">
<b>CoBWeaverClaw</b> — Built with ❤️ for the AI community
</div>
