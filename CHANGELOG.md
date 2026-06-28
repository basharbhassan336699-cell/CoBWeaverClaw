# Changelog

## [Unreleased] — In Development

### Added (Master Build Order)
- Three-layer memory: Working / Episodic / Core Knowledge with auto-summarization + self-learning
- Identity-driven system prompt built from config.agent + mission anchor (anti-drift)
- Role-based key routing: task type → provider (chat/analysis/summary/search/code)
- Full 5-tab gateway dashboard (Chat, Identity, Settings, Channels, Skills), RTL, no CDN
- Gateway API: /api/chat, /api/config (GET/POST), /api/memory/stats, /api/memory/clear, /api/skills, /api/channels
- Full Telegram bot (/start /help /memory /clear) + `python main.py telegram`
- Doctor now checks the configured provider (not hardcoded Anthropic)
- Setup wizard: language-first screen + owner name (Bashar Hassan)

### Fixed
- Gateway platform reporting + no-token default for localhost
- `main.py status` crash from `core/` shadowing stdlib `platform`
- All config/keys saved only to ~/.cobweaverclaw (never the project folder)

### Added
- Core agent architecture (core/agent.py)
- Triple memory system (SQLite + LightRAG + Compressor)
- Multi-model engine (Claude / Groq / Ollama / GPT / Gemini)
- Skill Factory + SkillClaw evolver
- Swarm Trading Engine (MiroFish-inspired)
- Built-in browser (manual + auto)
- 11 command categories (scan, doctor, fix, monitor...)
- Security-first Sandbox architecture
- JWT token system (Master / Device / Session)
- Multi-platform support (Android, iOS, Linux, Windows, macOS, Raspberry Pi)
- i18n: Arabic, English, Chinese, French, German, Japanese, Spanish
- Telegram + CLI + Web Dashboard interfaces
- One-line installer for all platforms
- Migration tool from OpenClaw and Hermes
