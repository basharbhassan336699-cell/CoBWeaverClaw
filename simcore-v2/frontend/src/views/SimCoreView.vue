<template>
  <div class="sc-wrap">
    <header class="sc-header">
      <div class="sc-brand" @click="$router.push('/')">SIMCORE</div>
      <span class="sc-domain-badge">{{ domainLabel }}</span>
    </header>

    <div class="sc-body">

      <!-- التوجه -->
      <div class="sc-panel">
        <div class="sc-panel-title">🎯 التوجه</div>
        <select v-model="domain" class="sc-sel">
          <option value="general">عام — شامل</option>
          <option value="trading">تداول</option>
          <option value="medicine">طب</option>
          <option value="engineering">هندسة</option>
          <option value="law">قانون</option>
          <option value="marketing">تسويق</option>
          <option value="security">أمن معلومات</option>
          <option value="education">تعليم</option>
          <option value="politics">سياسة</option>
          <option value="other">أخرى</option>
        </select>
        <input v-if="domain==='other'" v-model="domainCustom"
               class="sc-inp" placeholder="اكتب تخصصك"/>
      </div>

      <!-- ── المنصات ── -->
      <div class="sc-panel">
        <div class="sc-panel-title">🏦 المنصات</div>
        <p class="sc-hint">منصات التداول والشبكات الاجتماعية — تتصل عبر مفتاح API</p>

        <div class="sc-row">
          <input v-model="newPlatform.url" class="sc-inp sc-inp-url" dir="ltr"
                 placeholder="https://api.binance.com/api/v3/ticker/price"/>
          <button class="sc-btn-ghost" @click="probePlatform" :disabled="pprobing">
            {{ pprobing ? '...' : 'اختبر الاتصال' }}
          </button>
        </div>

        <div v-if="ppResult" class="sc-probe" :class="ppResult.reachable && !ppResult.auth_failed ? 'ok' : 'fail'">
          {{ ppResult.auth_ok ? '✅ متصل ومصادق' : ppResult.auth_failed ? '❌ مفتاح خاطئ' : ppResult.reachable ? '⚠️ يحتاج مفتاح' : '❌ ' + (ppResult.error||'فشل') }}
        </div>

        <input v-model="newPlatform.name" class="sc-inp" placeholder="اسم المنصة — مثال: Binance"/>

        <div class="sc-key-row">
          <label>مفتاح API</label>
          <input v-model="newPlatform.api_key" class="sc-inp" type="password" placeholder="API Key"/>
        </div>
        <div v-if="ppResult && ppResult.needs_secret" class="sc-key-row">
          <label>Secret</label>
          <input v-model="newPlatform.secret" class="sc-inp" type="password" placeholder="Secret Key (إذا طلبته المنصة)"/>
        </div>
        <div v-if="ppResult && ppResult.needs_id" class="sc-key-row">
          <label>Account ID</label>
          <input v-model="newPlatform.account_id" class="sc-inp" placeholder="Account ID (اختياري)"/>
        </div>

        <button class="sc-btn-add" @click="addPlatform">+ إضافة المنصة</button>

        <table v-if="platforms.length" class="sc-tbl">
          <thead><tr><th>الاسم</th><th>URL</th><th>النوع</th><th>الحالة</th><th></th></tr></thead>
          <tbody>
            <tr v-for="(p,i) in platforms" :key="i">
              <td>{{ p.name }}</td>
              <td class="mono">{{ p.url.slice(0,30) }}...</td>
              <td><span class="sc-type">{{ p.source_type }}</span></td>
              <td><span :class="p.auth_ok ? 'txt-green' : 'txt-amber'">{{ p.auth_ok ? '✅' : '⚠️' }}</span></td>
              <td><button class="sc-del" @click="platforms.splice(i,1)">✕</button></td>
            </tr>
          </tbody>
        </table>
        <div v-else class="sc-empty">لا منصات بعد</div>
      </div>

      <!-- ── المصادر ── -->
      <div class="sc-panel">
        <div class="sc-panel-title">🌐 المصادر</div>
        <p class="sc-hint">مواقع أخبار وويب — تُجلب مباشرة بدون مفتاح</p>

        <div class="sc-row">
          <input v-model="ns.url" class="sc-inp sc-inp-url" dir="ltr"
                 placeholder="https://coindesk.com أو أي موقع أخبار"/>
          <button class="sc-btn-ghost" @click="probe" :disabled="probing">
            {{ probing ? '...' : 'اختبر' }}
          </button>
        </div>

        <div v-if="pr" class="sc-probe" :class="pr.reachable ? 'ok' : 'fail'">
          {{ pr.reachable ? '✅ متصل' : '❌ ' + (pr.error||'فشل') }}
        </div>

        <div class="sc-row">
          <input v-model="ns.name" class="sc-inp" placeholder="اسم المصدر"/>
          <button class="sc-btn-add" style="width:auto;padding:8px 16px" @click="addSource">+</button>
        </div>

        <!-- نافذة إضافة مصدر إضافي -->
        <div v-if="showAddSource" class="sc-modal">
          <div class="sc-modal-body">
            <div class="sc-panel-title">+ مصدر جديد</div>
            <input v-model="extraSource.url"  class="sc-inp" dir="ltr" placeholder="URL"/>
            <input v-model="extraSource.name" class="sc-inp" placeholder="الاسم"/>
            <div class="sc-row">
              <button class="sc-btn-ghost" @click="showAddSource=false">إلغاء</button>
              <button class="sc-btn-primary" @click="confirmExtraSource">إضافة</button>
            </div>
          </div>
        </div>

        <div class="sc-row" style="margin-top:8px">
          <span class="sc-empty" style="flex:1">{{ sources.length }} مصدر مضاف</span>
          <button class="sc-btn-ghost" @click="showAddSource=true;extraSource={url:'',name:''}">+ مصدر آخر</button>
        </div>

        <table v-if="sources.length" class="sc-tbl">
          <thead><tr><th>الاسم</th><th>URL</th><th></th></tr></thead>
          <tbody>
            <tr v-for="(s,i) in sources" :key="i">
              <td>{{ s.name }}</td>
              <td class="mono">{{ s.url.slice(0,35) }}...</td>
              <td><button class="sc-del" @click="sources.splice(i,1)">✕</button></td>
            </tr>
          </tbody>
        </table>
      </div>

      <!-- المفاتيح -->
      <div class="sc-panel">
        <div class="sc-panel-title">🔑 المفاتيح</div>
        <p class="sc-hint">💡 الفارغ يرث: وكيل → مفتاح عام → نماذج CoBWeaverClaw</p>
        <div v-for="row in keyRows" :key="row.key" class="sc-key-row">
          <label>{{ row.label }}</label>
          <input v-model="keys[row.key]" class="sc-inp"
                 :type="row.pw?'password':'text'" :placeholder="row.ph" :dir="row.dir||'rtl'"/>
        </div>
      </div>

      <!-- تشغيل -->
      <button class="sc-btn-run" @click="run" :disabled="running">
        {{ running ? '⏳ جارٍ التحليل...' : '🔍 تشغيل التحليل' }}
      </button>

      <!-- النتائج -->
      <div v-if="result" class="sc-panel sc-results">
        <div class="sc-panel-title">📊 قرار OracleAgent</div>

        <div class="sc-decision" :class="result.decision.decision">
          <div class="dec-val">{{ (result.decision.decision||'').toUpperCase() }}</div>
          <div class="dec-conf">ثقة: {{ Math.round((result.decision.confidence||0)*100) }}%</div>
          <div class="dec-reason">{{ result.decision.reasoning }}</div>
          <div class="dec-action">▶ {{ result.decision.action }}</div>
          <ul v-if="result.decision.risks?.length" class="dec-risks">
            <li v-for="r in result.decision.risks" :key="r">⚠️ {{ r }}</li>
          </ul>
        </div>

        <div v-if="result.monitor_results?.length">
          <div class="sc-sub-title">📡 إشارات المراقبة</div>
          <div v-for="(m,i) in result.monitor_results" :key="i"
               class="sc-signal" :class="m.severity">
            <span class="sig-type">{{ m.signal_type }}</span>
            <span class="sig-sev">{{ m.severity }}</span>
            <p>{{ m.summary }}</p>
          </div>
        </div>

        <div v-if="result.tracker_results?.length">
          <div class="sc-sub-title">🌐 نتائج التتبع</div>
          <div v-for="(t,i) in result.tracker_results" :key="i" class="sc-track">
            <div class="track-src">{{ t.source }}</div>
            <p>{{ t.summary }}</p>
          </div>
        </div>

        <div class="sc-feedback">
          <div class="sc-sub-title">📝 ما حدث فعلاً؟</div>
          <div class="sc-row">
            <select v-model="fbOutcome" class="sc-sel" style="flex:1">
              <option value="">اختر النتيجة</option>
              <option value="correct">صحيح ✅</option>
              <option value="wrong">خاطئ ❌</option>
              <option value="partial">جزئي ⚠️</option>
            </select>
            <button class="sc-btn-ghost" @click="sendFb" :disabled="!fbOutcome">حفظ</button>
          </div>
        </div>
      </div>

    </div>
  </div>
</template>

<script>
export default {
  name: 'SimCoreView',
  data() {
    return {
      domain: 'general', domainCustom: '',
      sources: [],
      ns: { url:'', name:'', api_key:'', account_id:'', source_type:'web' },
      pr: null, probing: false,
      platforms: [],
      newPlatform: { name: '', url: '', api_key: '', secret: '', account_id: '', source_type: 'exchange' },
      ppResult: null,
      pprobing: false,
      showAddSource: false,
      extraSource: { url: '', name: '' },
      keys: {
        global_model_key:'', global_model_url:'', global_model_name:'',
        monitor_key:'', tracker_key:'', oracle_key:'',
      },
      keyRows: [
        { key:'global_model_key',  label:'مفتاح عام',    ph:'global model key (اختياري)',         pw:true  },
        { key:'global_model_url',  label:'Base URL',     ph:'https://.../v1/chat/completions',    pw:false, dir:'ltr' },
        { key:'global_model_name', label:'اسم النموذج', ph:'gpt-4o-mini (اختياري)',              pw:false },
        { key:'monitor_key',       label:'المراقبة',     ph:'مفتاح وكيل المراقبة (اختياري)',     pw:true  },
        { key:'tracker_key',       label:'التتبع',       ph:'مفتاح وكيل التتبع (اختياري)',       pw:true  },
        { key:'oracle_key',        label:'Oracle',       ph:'مفتاح OracleAgent (اختياري)',        pw:true  },
      ],
      running: false, result: null, fbOutcome: '',
    }
  },
  computed: {
    domainLabel() {
      return { general:'عام',trading:'تداول',medicine:'طب',engineering:'هندسة',
               law:'قانون',marketing:'تسويق',security:'أمن',education:'تعليم',
               politics:'سياسة',other:this.domainCustom||'أخرى' }[this.domain]||this.domain
    }
  },
  methods: {
    async probe() {
      if (!this.ns.url.trim()) return
      this.probing=true; this.pr=null
      try {
        const r = await fetch('/api/simcore/probe',{
          method:'POST', headers:{'Content-Type':'application/json'},
          body: JSON.stringify({url:this.ns.url})})
        const d = await r.json()
        this.pr = d.result
        this.ns.source_type = d.result?.suggested_type||'web'
      } catch(e) { this.pr={reachable:false,error:e.message} }
      finally { this.probing=false }
    },
    addSource() {
      if (!this.ns.url||!this.ns.name) return
      this.sources.push({...this.ns})
      this.ns={url:'',name:'',api_key:'',account_id:'',source_type:'web'}; this.pr=null
    },
    async probePlatform() {
      if (!this.newPlatform.url.trim()) return
      this.pprobing = true; this.ppResult = null
      try {
        const r = await fetch('/api/simcore/probe', {
          method: 'POST', headers: {'Content-Type': 'application/json'},
          body: JSON.stringify({ url: this.newPlatform.url,
                                 api_key: this.newPlatform.api_key,
                                 secret: this.newPlatform.secret })})
        const d = await r.json()
        this.ppResult = d.result
        this.newPlatform.source_type = d.result?.suggested_type || 'exchange'
      } catch(e) { this.ppResult = {reachable: false, error: e.message} }
      finally { this.pprobing = false }
    },
    addPlatform() {
      if (!this.newPlatform.url || !this.newPlatform.name) return
      this.platforms.push({ ...this.newPlatform, auth_ok: this.ppResult?.auth_ok || false })
      this.newPlatform = {name:'',url:'',api_key:'',secret:'',account_id:'',source_type:'exchange'}
      this.ppResult = null
    },
    confirmExtraSource() {
      if (!this.extraSource.url || !this.extraSource.name) return
      this.sources.push({ ...this.extraSource, source_type: 'web' })
      this.showAddSource = false
    },
    async run() {
      this.running=true; this.result=null
      try {
        const r = await fetch('/api/simcore/run',{
          method:'POST', headers:{'Content-Type':'application/json'},
          body: JSON.stringify({
            domain:    this.domain === 'other' ? this.domainCustom : this.domain,
            sources:   this.sources,
            platforms: this.platforms,
            ...this.keys,
          })})
        const d = await r.json()
        if (d.success) this.result=d; else alert('خطأ: '+d.error)
      } catch(e) { alert('خطأ: '+e.message) }
      finally { this.running=false }
    },
    async sendFb() {
      if (!this.result?.decision?.ts||!this.fbOutcome) return
      await fetch('/api/simcore/feedback',{
        method:'POST', headers:{'Content-Type':'application/json'},
        body: JSON.stringify({ts:this.result.decision.ts,
          outcome:this.fbOutcome,domain:this.domain})})
      alert('تم حفظ التغذية ✅')
    },
  }
}
</script>

<style scoped>
*{box-sizing:border-box}
.sc-wrap{background:#0d1520;min-height:100vh;color:#e8f0fa;font-family:system-ui,sans-serif}
.sc-header{display:flex;align-items:center;justify-content:space-between;padding:12px 20px;background:#111b2b;border-bottom:1px solid #1e3352}
.sc-brand{font-size:18px;font-weight:800;color:#e8523a;cursor:pointer;letter-spacing:1px}
.sc-domain-badge{background:#1c2f47;color:#2dd4bf;padding:4px 12px;border-radius:20px;font-size:12px}
.sc-body{max-width:700px;margin:0 auto;padding:20px;display:flex;flex-direction:column;gap:14px}
.sc-panel{background:#111b2b;border:1px solid #1e3352;border-radius:12px;padding:16px}
.sc-panel-title{font-weight:700;font-size:13px;margin-bottom:12px}
.sc-sel{width:100%;background:#162235;color:#e8f0fa;border:1px solid #1e3352;border-radius:8px;padding:8px 12px;margin-bottom:8px}
.sc-inp{width:100%;background:#162235;color:#e8f0fa;border:1px solid #1e3352;border-radius:8px;padding:8px 12px;margin-bottom:8px}
.sc-inp-url{flex:1;margin-bottom:0}
.sc-row{display:flex;gap:8px;margin-bottom:8px;align-items:center}
.sc-label{font-size:11px;color:#8ba4c4;margin-bottom:4px}
.sc-hint{font-size:11px;color:#3d5a7c;margin-bottom:12px}
.sc-btn-ghost{background:transparent;border:1px solid #1e3352;color:#8ba4c4;border-radius:8px;padding:8px 14px;cursor:pointer;white-space:nowrap}
.sc-btn-ghost:hover{border-color:#e8523a;color:#e8523a}
.sc-btn-add{width:100%;background:#1c2f47;color:#2dd4bf;border:1px solid #2dd4bf;border-radius:8px;padding:9px;cursor:pointer;font-weight:700;margin-top:4px}
.sc-btn-run{width:100%;background:#e8523a;color:#fff;border:none;border-radius:12px;padding:14px;cursor:pointer;font-size:15px;font-weight:800}
.sc-del{background:transparent;border:none;color:#ef4444;cursor:pointer}
.sc-probe{padding:6px 12px;border-radius:6px;font-size:12px;margin-bottom:8px}
.sc-probe.ok{background:#0a2e18;color:#22c55e}
.sc-probe.fail{background:#2a0808;color:#ef4444}
.sc-tbl{width:100%;border-collapse:collapse;font-size:12px;margin-top:12px}
.sc-tbl th{color:#3d5a7c;text-align:right;padding:6px;border-bottom:1px solid #1e3352}
.sc-tbl td{padding:6px;border-bottom:1px solid #1e3352;color:#8ba4c4}
.mono{font-family:monospace;font-size:11px}
.sc-empty{color:#3d5a7c;font-size:12px;text-align:center;padding:12px}
.sc-type{background:#1c2f47;color:#2dd4bf;padding:2px 8px;border-radius:10px;font-size:10px}
.sc-key-row{display:grid;grid-template-columns:90px 1fr;align-items:center;gap:8px;margin-bottom:6px}
.sc-key-row label{font-size:11px;color:#8ba4c4}
.sc-key-row .sc-inp{margin-bottom:0}
.sc-results{margin-top:4px}
.sc-decision{border-radius:10px;padding:16px;margin-bottom:14px;background:#162235;border:2px solid #2dd4bf}
.sc-decision.buy{border-color:#22c55e}.sc-decision.sell{border-color:#ef4444}
.sc-decision.wait{border-color:#f59e0b}.sc-decision.alert{border-color:#e8523a}
.dec-val{font-size:28px;font-weight:900;color:#2dd4bf}
.sc-decision.buy .dec-val{color:#22c55e}.sc-decision.sell .dec-val{color:#ef4444}
.sc-decision.wait .dec-val{color:#f59e0b}
.dec-conf{font-size:12px;color:#8ba4c4;margin:4px 0}
.dec-reason{font-size:13px;margin:8px 0}
.dec-action{font-size:12px;color:#2dd4bf;margin-top:6px}
.dec-risks{list-style:none;padding:0;margin:8px 0 0;font-size:12px;color:#f59e0b}
.sc-sub-title{font-size:12px;font-weight:700;color:#8ba4c4;margin:12px 0 6px}
.sc-signal{background:#162235;border-radius:8px;padding:10px;margin-bottom:6px;border-right:3px solid #f59e0b}
.sc-signal.critical{border-right-color:#ef4444}.sc-signal.high{border-right-color:#f59e0b}
.sig-type{font-size:10px;background:#1c2f47;padding:2px 6px;border-radius:4px;margin-left:6px}
.sig-sev{font-size:10px;color:#f59e0b}
.sc-track{background:#162235;border-radius:8px;padding:10px;margin-bottom:6px}
.track-src{font-weight:700;font-size:12px;color:#2dd4bf;margin-bottom:4px}
.sc-feedback{margin-top:14px;padding-top:12px;border-top:1px solid #1e3352}
.txt-green { color: #22c55e; }
.txt-amber { color: #f59e0b; }
.sc-modal { position:fixed;top:0;left:0;right:0;bottom:0;background:#000a;display:flex;align-items:center;justify-content:center;z-index:100 }
.sc-modal-body { background:#111b2b;border:1px solid #1e3352;border-radius:12px;padding:20px;width:90%;max-width:400px }
.sc-btn-primary { background:#e8523a;color:#fff;border:none;border-radius:8px;padding:8px 16px;cursor:pointer;font-weight:700 }
</style>
