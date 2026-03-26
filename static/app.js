/* ═══════════════════════════════════════════════════════════
   Backlink Hunter — App JS  (iOS design edition)
   ═══════════════════════════════════════════════════════════ */

// ── Toast ─────────────────────────────────────────────────
const toastEl   = document.getElementById('toast');
const toastIcon = document.getElementById('toast-icon');
const toastText = document.getElementById('toast-text');
let toastTimer;

function toast(msg, type = 'success', duration = 2800) {
  const icons = { success: '✓', error: '✕', info: 'ℹ' };
  toastEl.className = `ios-toast show ${type}`;
  toastIcon.textContent = icons[type] || '';
  toastText.textContent = msg;
  clearTimeout(toastTimer);
  toastTimer = setTimeout(() => toastEl.classList.remove('show'), duration);
}

// ── Escape helper ─────────────────────────────────────────
function esc(str) {
  return String(str || '')
    .replace(/&/g,'&amp;').replace(/</g,'&lt;')
    .replace(/>/g,'&gt;').replace(/"/g,'&quot;');
}

// ── Badge helpers ─────────────────────────────────────────
function strategyBadge(s) {
  const map = { 'Guest Post':'guest','Broken Link':'broken','Resource Page':'resource','Competitor Mention':'competitor' };
  return `<span class="strategy-badge ${map[s]||''}">${esc(s)||'—'}</span>`;
}
function scorePill(n) {
  const v = parseInt(n) || 0;
  const cls = v >= 60 ? 'score-high' : v >= 35 ? 'score-mid' : 'score-low';
  return `<span class="score-pill ${cls}">${v}</span>`;
}
function emailCheck(email) {
  return email
    ? `<svg viewBox="0 0 24 24" fill="none" stroke="var(--green)" stroke-width="2.5" width="14" height="14" title="${esc(email)}"><polyline points="20 6 9 17 4 12"/></svg>`
    : `<span style="color:var(--label3)">—</span>`;
}

// ── Skeleton helpers ──────────────────────────────────────
function skRows(n = 5) {
  return Array.from({length:n}, (_, i) => `
    <div class="sk-row">
      <div class="sk-cell sk-rect" style="width:${88+i*4}px"></div>
      <div class="sk-cell sk-rect" style="width:76px"></div>
      <div class="sk-cell sk-rect" style="width:38px"></div>
      <div class="sk-cell sk-rect" style="width:58px"></div>
      <div class="sk-cell sk-rect" style="flex:1"></div>
    </div>`).join('');
}
function skCards(n = 6) {
  return Array.from({length:n}, () => `<div class="sk-card-block sk-rect"></div>`).join('');
}

// ── Empty state template ──────────────────────────────────
function emptyState(svg, title, body, cta = '') {
  return `<div class="empty-state">${svg}<h3>${title}</h3><p>${body}</p>${cta}</div>`;
}

// ── Config helpers ────────────────────────────────────────
function isConfigured(cfg) {
  return !!(cfg?.target?.domain && cfg?.niche?.primary);
}
function updateSettingsDot(cfg) {
  document.getElementById('settings-dot').style.display = isConfigured(cfg) ? 'none' : 'block';
}
function updateRunWarning(cfg) {
  const warn = document.getElementById('run-config-warn');
  const btn  = document.getElementById('run-btn');
  if (!isConfigured(cfg)) {
    warn.style.display = 'flex'; btn.disabled = true;
  } else {
    warn.style.display = 'none';
    if (!isRunning) btn.disabled = false;
  }
  const s1 = document.getElementById('step-1');
  s1?.classList.toggle('done',   isConfigured(cfg));
  s1?.classList.toggle('active', !isConfigured(cfg));
}

// ── Tab navigation ────────────────────────────────────────
const navItems  = document.querySelectorAll('.nav-item');
const tabPanels = document.querySelectorAll('.tab-panel');

function switchTab(name) {
  navItems.forEach(b  => b.classList.toggle('active', b.dataset.tab === name));
  tabPanels.forEach(p => {
    const on = p.id === `tab-${name}`;
    if (on) p.classList.add('active'); else p.classList.remove('active');
  });
  if (name === 'dashboard')     loadDashboard();
  if (name === 'opportunities') loadOpportunities();
  if (name === 'emails')        loadEmails();
  if (name === 'settings')      loadSettings();
  if (name === 'directories')   loadDirectories();
}

navItems.forEach(b => b.addEventListener('click', () => switchTab(b.dataset.tab)));
document.getElementById('quick-run-btn').addEventListener('click', () => switchTab('run'));
document.getElementById('onboarding-setup-btn')?.addEventListener('click', () => switchTab('settings'));
document.addEventListener('keydown', e => { if (e.key === 'Escape') closeModal(); });

// ══ DASHBOARD ══════════════════════════════════════════════
async function loadDashboard() {
  // Skeletons
  document.getElementById('stats-grid').innerHTML = Array(4).fill(`
    <div class="stat-card sk">
      <div class="sk-rect sk-icon"></div>
      <div class="sk-lines"><div class="sk-rect sk-val"></div><div class="sk-rect sk-lbl"></div></div>
    </div>`).join('');
  document.getElementById('strategy-chart').innerHTML = '<div class="sk-block sk-rect"></div>';
  document.getElementById('status-chart').innerHTML   = '<div class="sk-block sk-rect"></div>';
  document.getElementById('dashboard-table-wrap').innerHTML = `<div class="sk-table">${skRows(5)}</div>`;

  const [stats, opps, cfg] = await Promise.all([
    fetch('/api/stats').then(r=>r.json()).catch(()=>({})),
    fetch('/api/opportunities').then(r=>r.json()).catch(()=>[]),
    fetch('/api/config').then(r=>r.json()).catch(()=>({})),
  ]);

  // Subtitle
  document.getElementById('dashboard-subtitle').textContent = opps.length
    ? `${opps.length} opportunities · ${Object.keys(stats.by_strategy||{}).length} strategies`
    : 'No data yet — run prospecting to get started';

  // Onboarding
  const hasCfg  = isConfigured(cfg);
  const hasData = opps.length > 0;
  document.getElementById('onboarding-banner').style.display = !hasCfg ? 'flex' : 'none';
  document.getElementById('get-started-card').style.display  = (!hasData) ? 'block' : 'none';
  document.getElementById('gs-step-1')?.classList.toggle('done', hasCfg);
  document.getElementById('gs-step-2')?.classList.toggle('done', hasData);

  updateSettingsDot(cfg);

  // Stat cards
  const statDefs = [
    { icon:'blue',   value: stats.total??0,       label:'Total Opportunities',
      svg:`<svg viewBox="0 0 24 24" fill="currentColor" width="20" height="20"><path d="M20 6h-2.18c.07-.44.18-.88.18-1.34C18 2.54 15.46 0 12.34 0c-1.7 0-3.2.9-4.09 2.23L12 6H9.34L8.08 4.22C7.63 3.48 6.83 3 6 3c-1.3 0-2.38.93-2.58 2.18L2 6H0l2.29 8H22l-2-8z"/></svg>` },
    { icon:'green',  value: stats.with_email??0,   label:'With Contact Email',
      svg:`<svg viewBox="0 0 24 24" fill="currentColor" width="20" height="20"><path d="M20 4H4c-1.1 0-2 .9-2 2v12c0 1.1.9 2 2 2h16c1.1 0 2-.9 2-2V6c0-1.1-.9-2-2-2zm0 4l-8 5-8-5V6l8 5 8-5v2z"/></svg>` },
    { icon:'purple', value: stats.top_score??0,    label:'Top Score',
      svg:`<svg viewBox="0 0 24 24" fill="currentColor" width="20" height="20"><path d="M16 6l2.29 2.29-4.88 4.88-4-4L2 16.59 3.41 18l6-6 4 4 6.3-6.29L22 12V6z"/></svg>` },
    { icon:'orange', value: stats.won??0,           label:'Links Won',
      svg:`<svg viewBox="0 0 24 24" fill="currentColor" width="20" height="20"><path d="M12 1L3 5v6c0 5.55 3.84 10.74 9 12 5.16-1.26 9-6.45 9-12V5l-9-4zm-2 16l-4-4 1.41-1.41L10 14.17l6.59-6.59L18 9l-8 8z"/></svg>` },
  ];

  document.getElementById('stats-grid').innerHTML = statDefs.map(s => `
    <div class="stat-card">
      <div class="stat-icon ${s.icon}">${s.svg}</div>
      <div>
        <div class="stat-value">${s.value}</div>
        <div class="stat-label">${s.label}</div>
      </div>
    </div>`).join('');

  document.getElementById('badge-opps').textContent   = stats.total       ?? 0;
  document.getElementById('badge-emails').textContent = stats.email_drafts ?? 0;

  renderBarChart('strategy-chart', stats.by_strategy || {}, 'No strategies run yet.');
  renderBarChart('status-chart',   stats.by_status   || {}, 'No status data yet.');

  // Top 10 table
  const top  = [...opps].sort((a,b)=>(parseInt(b.score)||0)-(parseInt(a.score)||0)).slice(0,10);
  const wrap = document.getElementById('dashboard-table-wrap');
  if (!top.length) {
    wrap.innerHTML = emptyState(
      `<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.4" width="48" height="48"><path d="M21 16V8a2 2 0 00-1-1.73l-7-4a2 2 0 00-2 0l-7 4A2 2 0 003 8v8a2 2 0 001 1.73l7 4a2 2 0 002 0l7-4A2 2 0 0021 16z"/></svg>`,
      'No opportunities yet',
      'Run prospecting to discover backlink targets automatically.',
      `<button class="ios-btn ios-btn-primary ios-btn-sm" onclick="switchTab('run')">
         <svg viewBox="0 0 24 24" fill="currentColor" width="12" height="12"><path d="M8 5v14l11-7z"/></svg>
         Run Now
       </button>`
    );
    return;
  }
  wrap.innerHTML = buildTable(top, { compact: true });
  attachRowTaps(wrap, top);
}

function renderBarChart(elId, data, emptyMsg) {
  const el = document.getElementById(elId);
  const entries = Object.entries(data).sort((a,b)=>b[1]-a[1]);
  const total   = entries.reduce((s,[,n])=>s+n,0) || 1;
  if (!entries.length) {
    el.innerHTML = `<p style="color:var(--label3);font-size:13px;text-align:center;padding:24px 0">${emptyMsg}</p>`;
    return;
  }
  el.innerHTML = entries.map(([label, count]) => `
    <div class="bar-row">
      <div class="bar-label" title="${esc(label)}">${esc(label)}</div>
      <div class="bar-track"><div class="bar-fill" style="width:${Math.round(count/total*100)}%"></div></div>
      <div class="bar-count">${count}</div>
    </div>`).join('');
}

// ══ OPPORTUNITIES ══════════════════════════════════════════
let allOpps = [];
let sortCol = 'score', sortDir = -1;

async function loadOpportunities() {
  document.getElementById('opps-table-wrap').innerHTML =
    `<div class="sk-table-full">${skRows(8)}</div>`;
  allOpps = await fetch('/api/opportunities').then(r=>r.json()).catch(()=>[]);
  document.getElementById('opps-subtitle').textContent =
    allOpps.length ? `${allOpps.length} total` : 'No data yet';
  renderOpps();
}

function renderOpps() {
  const search   = document.getElementById('opp-search').value.toLowerCase().trim();
  const strategy = document.getElementById('filter-strategy').value;
  const status   = document.getElementById('filter-status').value;

  let rows = allOpps.filter(o => {
    if (strategy && o.strategy !== strategy) return false;
    if (status   && (o.status||'New') !== status) return false;
    if (search) {
      if (!(o.site_name+o.url+o.snippet+o.notes).toLowerCase().includes(search)) return false;
    }
    return true;
  });

  rows.sort((a,b) => {
    let av = a[sortCol]||'', bv = b[sortCol]||'';
    if (sortCol==='score') { av=parseInt(av)||0; bv=parseInt(bv)||0; }
    return av<bv ? -sortDir : av>bv ? sortDir : 0;
  });

  // Chips
  const chips = [];
  if (search)   chips.push({ label:`"${search}"`,      clear:()=>{ document.getElementById('opp-search').value=''; renderOpps(); } });
  if (strategy) chips.push({ label:strategy,           clear:()=>{ document.getElementById('filter-strategy').value=''; renderOpps(); } });
  if (status)   chips.push({ label:status,             clear:()=>{ document.getElementById('filter-status').value=''; renderOpps(); } });
  const chipsEl = document.getElementById('filter-chips');
  if (chips.length) {
    chipsEl.style.display = 'flex';
    chipsEl.innerHTML = chips.map((c,i)=>`
      <span class="chip">${esc(c.label)}
        <button class="chip-remove" data-i="${i}">×</button>
      </span>`).join('') +
      `<button class="ios-btn ios-btn-ghost ios-btn-sm" id="clear-chips">Clear all</button>`;
    chipsEl.querySelectorAll('.chip-remove').forEach(b =>
      b.addEventListener('click', () => chips[+b.dataset.i].clear())
    );
    document.getElementById('clear-chips')?.addEventListener('click', () => {
      document.getElementById('opp-search').value='';
      document.getElementById('filter-strategy').value='';
      document.getElementById('filter-status').value='';
      renderOpps();
    });
  } else {
    chipsEl.style.display = 'none';
  }

  document.getElementById('opps-subtitle').textContent =
    `${rows.length} of ${allOpps.length}`;

  const wrap = document.getElementById('opps-table-wrap');
  if (!allOpps.length) {
    wrap.innerHTML = emptyState(
      `<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.4" width="48" height="48"><circle cx="12" cy="12" r="10"/><line x1="12" y1="8" x2="12" y2="12"/><line x1="12" y1="16" x2="12.01" y2="16"/></svg>`,
      'No opportunities yet',
      'Run prospecting to start finding backlink targets.',
      `<button class="ios-btn ios-btn-primary ios-btn-sm" onclick="switchTab('run')">Run Now →</button>`
    );
    return;
  }
  if (!rows.length) {
    wrap.innerHTML = emptyState(
      `<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.4" width="48" height="48"><circle cx="11" cy="11" r="8"/><line x1="21" y1="21" x2="16.65" y2="16.65"/></svg>`,
      'No matches found',
      'Try adjusting your search or filter criteria.',
      `<button class="ios-btn ios-btn-ghost ios-btn-sm"
         onclick="document.getElementById('opp-search').value='';document.getElementById('filter-strategy').value='';document.getElementById('filter-status').value='';renderOpps()">
         Clear filters
       </button>`
    );
    return;
  }
  wrap.innerHTML = buildTable(rows, { sortable: true });
  attachStatusSelects();
  attachRowTaps(wrap, rows);
}

function buildTable(rows, { compact=false, sortable=false } = {}) {
  const th = (col, label) => {
    const cls = sortCol===col ? (sortDir>0?'sorted-asc':'sorted-desc') : '';
    return `<th class="${cls}" ${sortable?`data-sort="${col}"`:''}>${label}</th>`;
  };
  const head = `<tr>
    ${th('site_name','Site')} ${th('strategy','Strategy')} ${th('score','Score')}
    <th>Email</th>
    ${!compact?`<th>Status</th>`:''}
    ${th('url','URL')}
    ${!compact?`<th>Notes</th>`:''}
  </tr>`;
  const body = rows.map(o => `
    <tr tabindex="0">
      <td class="td-site" title="${esc(o.site_name)}">${esc(o.site_name||'—')}</td>
      <td>${strategyBadge(o.strategy)}</td>
      <td class="td-score">${scorePill(o.score)}</td>
      <td class="td-email">${emailCheck(o.contact_email)}</td>
      ${!compact?`<td>
        <select class="status-select" data-url="${esc(o.url)}">
          ${['New','Emailed','Replied','Won','Lost','Skipped'].map(s=>
            `<option${s===(o.status||'New')?' selected':''}>${s}</option>`).join('')}
        </select></td>`:''}
      <td class="td-url"><a href="${esc(o.url)}" target="_blank" rel="noopener">${esc(o.url)}</a></td>
      ${!compact?`<td style="max-width:190px;color:var(--label2);font-size:12px;overflow:hidden;text-overflow:ellipsis;white-space:nowrap" title="${esc(o.notes||o.snippet||'')}">${esc(o.notes||o.snippet||'—')}</td>`:''}
    </tr>`).join('');
  return `<table><thead>${head}</thead><tbody>${body}</tbody></table>`;
}

function attachStatusSelects() {
  document.querySelectorAll('.status-select').forEach(sel => {
    sel.addEventListener('change', async () => {
      const url = sel.dataset.url;
      const res = await fetch('/api/opportunities/update', {
        method:'POST', headers:{'Content-Type':'application/json'},
        body: JSON.stringify({ url, field:'status', value:sel.value }),
      });
      if (res.ok) {
        toast(`Status → ${sel.value}`);
        const o = allOpps.find(x=>x.url===url);
        if (o) o.status = sel.value;
        fetch('/api/stats').then(r=>r.json()).then(refreshBadges);
      } else {
        toast('Failed to update status','error');
      }
    });
  });
}
function attachRowTaps(container, rows) {
  container.querySelectorAll('tbody tr').forEach((row, i) => {
    const open = e => { if (e.target.closest('select,a,button')) return; openModal(rows[i]); };
    row.addEventListener('click', open);
    row.addEventListener('keydown', e => { if (e.key==='Enter'||e.key===' ') open(e); });
  });
}

// Sortable col headers
document.getElementById('opps-table-wrap').addEventListener('click', e => {
  const th = e.target.closest('th[data-sort]'); if (!th) return;
  const col = th.dataset.sort;
  sortCol===col ? sortDir*=-1 : (sortCol=col, sortDir=-1);
  renderOpps();
});
document.getElementById('opp-search').addEventListener('input', renderOpps);
document.getElementById('filter-strategy').addEventListener('change', renderOpps);
document.getElementById('filter-status').addEventListener('change', renderOpps);
document.getElementById('refresh-opps-btn').addEventListener('click', () => {
  const btn = document.getElementById('refresh-opps-btn');
  btn.disabled = true; loadOpportunities().finally(()=>btn.disabled=false);
});

// ══ EMAILS ══════════════════════════════════════════════════
let allEmails = [];

async function loadEmails() {
  document.getElementById('emails-grid').innerHTML = `<div class="sk-cards">${skCards(6)}</div>`;
  allEmails = await fetch('/api/emails').then(r=>r.json()).catch(()=>[]);
  document.getElementById('emails-subtitle').textContent =
    allEmails.length ? `${allEmails.length} drafts ready` : 'No drafts yet';
  renderEmails();
}

function renderEmails() {
  const filter = document.getElementById('email-filter-strategy').value;
  const rows   = allEmails.filter(e=>!filter||e.strategy===filter);
  const grid   = document.getElementById('emails-grid');

  if (!allEmails.length) {
    grid.innerHTML = emptyState(
      `<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.4" width="48" height="48"><path d="M4 4h16c1.1 0 2 .9 2 2v12c0 1.1-.9 2-2 2H4c-1.1 0-2-.9-2-2V6c0-1.1.9-2 2-2z"/><polyline points="22,6 12,13 2,6"/></svg>`,
      'No email drafts yet',
      'Run prospecting with email generation enabled to get outreach drafts here.',
      `<button class="ios-btn ios-btn-primary ios-btn-sm" onclick="switchTab('run')">Run Now →</button>`
    );
    return;
  }
  if (!rows.length) {
    grid.innerHTML = emptyState(
      `<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.4" width="48" height="48"><circle cx="11" cy="11" r="8"/><line x1="21" y1="21" x2="16.65" y2="16.65"/></svg>`,
      'No emails for that strategy',
      'Try a different filter.', ``);
    return;
  }

  grid.innerHTML = rows.map((e,i)=>`
    <div class="email-card" data-idx="${i}" tabindex="0" role="button">
      <div class="email-card-header">
        <div>
          <div class="email-card-title">${esc(e.site_name||'—')}</div>
          <div class="email-card-url">${esc(e.url||'')}</div>
        </div>
        ${strategyBadge(e.strategy)}
      </div>
      <div class="email-card-preview">${esc((e.email_draft||'').slice(0,200).trim())}…</div>
      <div class="email-card-footer">
        ${scorePill(e.score)}
        <span style="font-size:12px;color:var(--label2);display:flex;align-items:center;gap:5px">
          ${emailCheck(e.contact_email)}
          <span>${esc(e.contact_email||'no email')}</span>
        </span>
      </div>
    </div>`).join('');

  grid.querySelectorAll('.email-card').forEach(card => {
    const open = () => {
      const filtered = allEmails.filter(e=>!filter||e.strategy===filter);
      openModal(filtered[+card.dataset.idx]);
    };
    card.addEventListener('click', open);
    card.addEventListener('keydown', e=>{ if(e.key==='Enter'||e.key===' ') open(); });
  });
}

document.getElementById('email-filter-strategy').addEventListener('change', renderEmails);
document.getElementById('refresh-emails-btn').addEventListener('click', () => {
  const btn = document.getElementById('refresh-emails-btn');
  btn.disabled = true; loadEmails().finally(()=>btn.disabled=false);
});

// ══ MODAL / SHEET ══════════════════════════════════════════
function openModal(opp) {
  if (!opp) return;
  let draft = opp.email_draft || '';
  if (!draft) { const m = allEmails.find(e=>e.url===opp.url); draft = m?.email_draft||''; }

  document.getElementById('modal-site-name').textContent = opp.site_name||'—';
  const strat = document.getElementById('modal-strategy');
  strat.textContent = opp.strategy||'';
  const map = {'Guest Post':'guest','Broken Link':'broken','Resource Page':'resource','Competitor Mention':'competitor'};
  strat.className = `strategy-badge ${map[opp.strategy]||''}`;
  document.getElementById('modal-score-badge').innerHTML = scorePill(opp.score);
  document.getElementById('modal-url').href = opp.url||'#';
  document.getElementById('modal-url-text').textContent = opp.url||'';
  document.getElementById('modal-contact').textContent = opp.contact_email ? `✉ ${opp.contact_email}` : '';
  document.getElementById('modal-email').textContent =
    draft || 'No draft available.\n\nTip: re-run without "Skip email generation" to auto-create outreach emails.';
  document.getElementById('copy-hint').textContent = '';
  document.getElementById('modal-overlay').classList.add('open');
  document.getElementById('modal-close').focus();
}
function closeModal() {
  document.getElementById('modal-overlay').classList.remove('open');
}
document.getElementById('modal-close').addEventListener('click', closeModal);
document.getElementById('modal-close-btn').addEventListener('click', closeModal);
document.getElementById('modal-overlay').addEventListener('click', e => {
  if (e.target === document.getElementById('modal-overlay')) closeModal();
});
document.getElementById('modal-copy-btn').addEventListener('click', () => {
  const text = document.getElementById('modal-email').textContent;
  const hint = document.getElementById('copy-hint');
  navigator.clipboard.writeText(text)
    .then(()=>{ hint.textContent='✓ Copied!'; toast('Email copied'); setTimeout(()=>hint.textContent='',3000); })
    .catch(()=>{
      const ta = document.createElement('textarea');
      ta.value=text; document.body.appendChild(ta); ta.select();
      document.execCommand('copy'); document.body.removeChild(ta);
      hint.textContent='✓ Copied!'; toast('Email copied');
    });
});

// ══ SETTINGS ═══════════════════════════════════════════════
let competitors = [];

async function loadSettings() {
  const cfg = await fetch('/api/config').then(r=>r.json()).catch(()=>({}));
  const hasDomain = !!(cfg.target?.domain);

  // Always populate domain hero input
  const domainHero = document.getElementById('domain-hero-input');
  if (domainHero && cfg.target?.domain) domainHero.value = cfg.target.domain;

  if (hasDomain) {
    showDiscoveredFields();
    populateFields(cfg);
  }

  updateSettingsDot(cfg);
  updateRunWarning(cfg);
}

function showDiscoveredFields() {
  document.getElementById('discovered-fields').style.display = 'block';
}

function populateFields(cfg) {
  const form = document.getElementById('settings-form');
  const set  = (name, val) => {
    const el = form.querySelector(`[name="${name}"]`);
    if (el && val !== undefined && val !== null) el.value = val;
  };
  set('target.name',        cfg.target?.name);
  set('target.description', cfg.target?.description);
  set('niche.primary',      cfg.niche?.primary);
  set('niche.keywords',     (cfg.niche?.keywords||[]).join('\n'));
  set('outreach.sender_name',  cfg.outreach?.sender_name);
  set('outreach.sender_email', cfg.outreach?.sender_email);
  set('scraper.max_results_per_strategy', cfg.scraper?.max_results_per_strategy ?? 30);
  set('scraper.request_delay_seconds',    cfg.scraper?.request_delay_seconds    ?? 2);
  set('scraper.timeout_seconds',          cfg.scraper?.timeout_seconds          ?? 10);
  set('scraper.check_broken_links', cfg.scraper?.check_broken_links !== false ? 'true' : 'false');
  renderCompetitors(cfg.competitors||[]);
}

// ── Analyse site button ───────────────────────────────────
document.getElementById('analyse-btn').addEventListener('click', async () => {
  const domainInput = document.getElementById('domain-hero-input');
  const raw = domainInput.value.trim().replace(/^https?:\/\//,'').replace(/\/$/,'');
  if (!raw) { setAnalyseHint('Enter your domain first.','error'); return; }

  const btn = document.getElementById('analyse-btn');
  const inner = document.getElementById('analyse-btn-inner');
  btn.disabled = true;
  inner.innerHTML = `<span class="btn-spinner"></span> Analysing…`;
  setAnalyseHint('Scraping your homepage…');

  const res  = await fetch('/api/analyse-site', {
    method:'POST', headers:{'Content-Type':'application/json'},
    body: JSON.stringify({ domain: raw }),
  });
  const data = await res.json().catch(()=>({ok:false,error:'Network error'}));

  btn.disabled = false;
  inner.innerHTML = `<svg viewBox="0 0 24 24" fill="currentColor" width="14" height="14"><path d="M15.5 14h-.79l-.28-.27A6.471 6.471 0 0016 9.5 6.5 6.5 0 109.5 16c1.61 0 3.09-.59 4.23-1.57l.27.28v.79l5 4.99L20.49 19l-4.99-5zm-6 0C7.01 14 5 11.99 5 9.5S7.01 5 9.5 5 14 7.01 14 9.5 11.99 14 9.5 14z"/></svg> Analyse Site`;

  if (!data.ok) {
    setAnalyseHint(data.error || 'Could not reach site.', 'error');
    toast(data.error || 'Analysis failed', 'error');
    return;
  }

  setAnalyseHint(`✓ Detected: ${data.brand_name} · ${data.niche} — finding competitors…`, 'success');
  showDiscoveredFields();

  const form = document.getElementById('settings-form');
  const set  = (name, val) => { const el = form.querySelector(`[name="${name}"]`); if (el && val) el.value = val; };
  set('target.name',        data.brand_name);
  set('target.description', data.description);
  set('niche.primary',      data.niche);
  set('niche.keywords',     (data.keywords||[]).join('\n'));
  set('outreach.sender_name',  data.sender_name);
  set('outreach.sender_email', data.sender_email);

  _autoDiscoverCompetitors(raw, data.niche, data.keywords || []);
});

function setAnalyseHint(msg, type='') {
  const el = document.getElementById('analyse-hint');
  el.textContent = msg;
  el.className   = 'domain-hero-hint' + (type ? ` ${type}` : '');
}

// ── Auto-discover competitors (called after Analyse Site) ─
async function _autoDiscoverCompetitors(domain, niche, keywords) {
  const listEl = document.getElementById('competitors-list');
  listEl.innerHTML = `<div class="comp-discovering"><span class="btn-spinner" style="border-color:rgba(0,122,255,.2);border-top-color:var(--blue);width:12px;height:12px"></span> Finding competitors…</div>`;

  // Save niche + keywords to config first so the endpoint can build geo queries from them
  const existing = await fetch('/api/config').then(r=>r.json()).catch(()=>({}));
  const patch = {
    ...existing,
    niche:  { ...(existing.niche||{}), primary: niche, keywords },
    target: { ...(existing.target||{}), domain },
  };
  await fetch('/api/config', { method:'POST', headers:{'Content-Type':'application/json'}, body: JSON.stringify(patch) });

  const res  = await fetch('/api/discover-competitors', { method:'POST' });
  const data = await res.json().catch(()=>({ok:false}));

  if (!data.ok || !data.competitors?.length) {
    setAnalyseHint(`✓ Detected: ${niche} — no competitors found, add manually`, 'success');
    renderCompetitors([]);
    return;
  }

  renderCompetitors(data.competitors);
  setAnalyseHint(`✓ Detected niche · ${data.competitors.length} competitors found — review and save`, 'success');
  toast(`Found ${data.competitors.length} competitor${data.competitors.length!==1?'s':''}`, 'success');
}

function renderCompetitors(list) {
  competitors = list.map(c=>({...c}));
  const el = document.getElementById('competitors-list');
  if (!competitors.length) {
    el.innerHTML = '<div class="empty-competitors">No competitors added yet.</div>';
    return;
  }
  el.innerHTML = competitors.map((c,i)=>`
    <div class="comp-row">
      <input class="comp-input" type="text" placeholder="domain.com" value="${esc(c.domain||'')}" data-ci="${i}" data-cf="domain" />
      <input class="comp-input" type="text" placeholder="Brand name" value="${esc(c.name||'')}"   data-ci="${i}" data-cf="name" style="color:var(--label2)" />
      <button class="comp-remove" data-rm="${i}" title="Remove">−</button>
    </div>`).join('');
  el.querySelectorAll('[data-ci]').forEach(inp =>
    inp.addEventListener('input', ()=> competitors[+inp.dataset.ci][inp.dataset.cf] = inp.value)
  );
  el.querySelectorAll('[data-rm]').forEach(btn =>
    btn.addEventListener('click', ()=>{ competitors.splice(+btn.dataset.rm,1); renderCompetitors(competitors); })
  );
}

document.getElementById('add-competitor-btn').addEventListener('click', ()=>{
  competitors.push({domain:'',name:''});
  renderCompetitors(competitors);
  const inputs = document.querySelectorAll('.comp-input[data-cf="domain"]');
  inputs[inputs.length-1]?.focus();
});

document.getElementById('settings-form').addEventListener('submit', async e => {
  e.preventDefault();
  const form = e.target;
  const val  = n => form.querySelector(`[name="${n}"]`)?.value?.trim()||'';

  // Derive domain + URL from the hero input (not a hidden form field)
  const rawDomain = (document.getElementById('domain-hero-input')?.value || '').trim()
    .replace(/^https?:\/\//,'').replace(/\/$/,'');
  const derivedUrl = rawDomain ? `https://${rawDomain}` : '';

  // Validation
  const errEl = document.getElementById('err-website');
  if (!rawDomain) {
    errEl.textContent = 'Domain is required';
    toast('Enter your domain first', 'error');
    document.getElementById('domain-hero-input').focus();
    return;
  }
  errEl.textContent = '';

  const cfg = {
    target: { domain:rawDomain, url:derivedUrl, name:val('target.name'), description:val('target.description') },
    niche:  { primary:val('niche.primary'), keywords:val('niche.keywords').split('\n').map(s=>s.trim()).filter(Boolean) },
    competitors: competitors.filter(c=>c.domain),
    outreach:    { sender_name:val('outreach.sender_name'), sender_email:val('outreach.sender_email') },
    scraper: {
      max_results_per_strategy: parseInt(val('scraper.max_results_per_strategy'))||30,
      request_delay_seconds:    parseFloat(val('scraper.request_delay_seconds'))||2,
      timeout_seconds:          parseInt(val('scraper.timeout_seconds'))||10,
      check_broken_links:       val('scraper.check_broken_links')!=='false',
      user_agent: 'Mozilla/5.0 (compatible; BacklinkHunter/1.0)',
    },
    output: { directory:'output', csv_filename:'backlink_opportunities.csv', email_drafts_filename:'outreach_emails.csv' },
  };

  const saveBtn = document.getElementById('save-btn');
  const fb      = document.getElementById('save-feedback');
  saveBtn.disabled = true;
  saveBtn.innerHTML = `<span class="btn-spinner"></span> Saving…`;

  const res = await fetch('/api/config', { method:'POST', headers:{'Content-Type':'application/json'}, body:JSON.stringify(cfg) });

  saveBtn.disabled = false;
  saveBtn.textContent = 'Save Settings';

  if (res.ok) {
    fb.className = 'save-msg ok';
    fb.textContent = '✓ Saved!';
    toast('Settings saved');
    updateSettingsDot(cfg);
    updateRunWarning(cfg);
    errEl.textContent = '';
    setTimeout(()=>fb.textContent='', 4000);
  } else {
    fb.className = 'save-msg err';
    fb.textContent = '✕ Save failed';
    toast('Save failed','error');
  }
});

// ══ DIRECTORIES ════════════════════════════════════════════

const DIR_LIST = [
  // Local / Maps
  {id:"google_biz",   name:"Google Business Profile", category:"Local",             authority:"Essential"},
  {id:"bing_places",  name:"Bing Places",             category:"Local",             authority:"High"},
  {id:"apple_maps",   name:"Apple Maps",              category:"Local",             authority:"High"},
  // B2B & Reviews
  {id:"clutch",       name:"Clutch",                  category:"B2B Reviews",       authority:"High"},
  {id:"goodfirms",    name:"GoodFirms",               category:"B2B Reviews",       authority:"High"},
  {id:"designrush",   name:"DesignRush",              category:"B2B Directory",     authority:"High"},
  {id:"trustpilot",   name:"Trustpilot",              category:"Reviews",           authority:"High"},
  // Security industry
  {id:"sec_informed", name:"SecurityInformed",        category:"Security Industry", authority:"High"},
  {id:"ifsec",        name:"IFSEC Global",            category:"Security Industry", authority:"High"},
  {id:"security_mag", name:"Security Magazine",       category:"Security Industry", authority:"Medium"},
  // MENA / Lebanon
  {id:"ypLB",         name:"Yellow Pages Lebanon",    category:"Local (MENA)",      authority:"Medium"},
  {id:"kompass",      name:"Kompass",                 category:"B2B Directory",     authority:"High"},
  {id:"dnb",          name:"Dun & Bradstreet",        category:"Business Reg.",     authority:"High"},
];

let dirState  = {};   // {id: {status, submit_url}}
let dirSource = null;

function _dirAvatarColor(str) {
  const palette = ['#007AFF','#34C759','#FF9500','#AF52DE','#5AC8FA','#FF2D55','#5856D6','#FF6B35'];
  let h = 0;
  for (let i = 0; i < str.length; i++) h = (h * 31 + str.charCodeAt(i)) & 0xFFFF;
  return palette[h % palette.length];
}

function _dirStatusHtml(status) {
  if (status === 'idle')        return `<span class="dir-status dir-status-idle">Not scanned</span>`;
  if (status === 'checking')    return `<span class="dir-status dir-status-checking"><span class="dir-spin"></span>Checking…</span>`;
  if (status === 'listed')      return `<span class="dir-status dir-status-listed"><svg viewBox="0 0 24 24" fill="currentColor" width="11" height="11"><path d="M9 16.17L4.83 12l-1.42 1.41L9 19 21 7l-1.41-1.41z"/></svg>Listed</span>`;
  if (status === 'not_listed')  return `<span class="dir-status dir-status-missing">Not listed</span>`;
  if (status === 'manual')      return `<span class="dir-status dir-status-manual"><svg viewBox="0 0 24 24" fill="currentColor" width="11" height="11"><path d="M12 4.5C7 4.5 2.73 7.61 1 12c1.73 4.39 6 7.5 11 7.5s9.27-3.11 11-7.5c-1.73-4.39-6-7.5-11-7.5zM12 17c-2.76 0-5-2.24-5-5s2.24-5 5-5 5 2.24 5 5-2.24 5-5 5zm0-8c-1.66 0-3 1.34-3 3s1.34 3 3 3 3-1.34 3-3-1.34-3-3-3z"/></svg>Verify</span>`;
  return `<span class="dir-status dir-status-idle">Unknown</span>`;
}

function _buildDirCard(d, state) {
  const status     = state?.status || 'idle';
  const submitUrl  = state?.submit_url || '';
  const authCls    = {Essential:'dir-auth-essential', High:'dir-auth-high', Medium:'dir-auth-medium'}[d.authority] || '';
  const isHighlight= status === 'not_listed';

  const submitBtn = (status === 'not_listed' || status === 'manual') && submitUrl
    ? `<a href="${esc(submitUrl)}" target="_blank" rel="noopener" class="dir-submit-btn ios-btn ios-btn-primary ios-btn-sm">Submit →</a>`
    : '';

  return `
    <div class="dir-card${isHighlight?' dir-card-highlight':''}" id="dir-${d.id}">
      <div class="dir-avatar" style="background:${_dirAvatarColor(d.name)}">${d.name[0]}</div>
      <div class="dir-card-body">
        <div class="dir-card-name">${esc(d.name)}</div>
        <div class="dir-card-meta">
          <span class="dir-category">${esc(d.category)}</span>
          <span class="dir-auth ${authCls}">${esc(d.authority)}</span>
        </div>
      </div>
      <div class="dir-card-right" id="dir-right-${d.id}">
        ${_dirStatusHtml(status)}
        ${submitBtn}
      </div>
    </div>`;
}

function _updateDirCard(id, state) {
  const right = document.getElementById(`dir-right-${id}`);
  if (!right) return;
  const d          = DIR_LIST.find(x => x.id === id);
  const status     = state?.status || 'idle';
  const submitUrl  = state?.submit_url || '';
  const submitBtn  = (status === 'not_listed' || status === 'manual') && submitUrl
    ? `<a href="${esc(submitUrl)}" target="_blank" rel="noopener" class="dir-submit-btn ios-btn ios-btn-primary ios-btn-sm">Submit →</a>`
    : '';
  right.innerHTML = _dirStatusHtml(status) + submitBtn;

  const card = document.getElementById(`dir-${id}`);
  if (card) {
    if (status === 'listed') {
      card.style.transition = 'opacity .3s, max-height .4s';
      card.style.opacity = '0';
      card.style.overflow = 'hidden';
      setTimeout(() => { card.style.maxHeight = '0'; card.style.marginBottom = '0'; }, 300);
      setTimeout(() => card.remove(), 700);
    } else {
      card.classList.toggle('dir-card-highlight', status === 'not_listed');
    }
  }
}

function _updateDirSummary() {
  const vals = Object.values(dirState);
  const listed  = vals.filter(v => v.status === 'listed').length;
  const missing = vals.filter(v => v.status === 'not_listed').length;
  const manual  = vals.filter(v => v.status === 'manual').length;
  const total   = vals.filter(v => v.status !== 'idle').length;

  const sum = document.getElementById('dir-summary');
  if (total > 0) {
    sum.style.display = 'flex';
    document.getElementById('dir-listed-count').textContent  = listed;
    document.getElementById('dir-missing-count').textContent = missing;
    document.getElementById('dir-manual-count').textContent  = manual;
  }

  // Badge: show count of not_listed
  const badge = document.getElementById('badge-dirs');
  if (missing > 0) {
    badge.textContent = missing;
    badge.style.display = 'inline-flex';
  } else {
    badge.style.display = 'none';
  }

  // Subtitle
  const sub = document.getElementById('dir-subtitle');
  if (total === DIR_LIST.length) {
    sub.textContent = missing > 0
      ? `${missing} director${missing!==1?'ies':'y'} to submit — click Submit → on any highlighted card.`
      : 'All scanned directories already have a listing for your brand.';
  }
}

function loadDirectories() {
  const grid = document.getElementById('dir-grid');
  // Only show non-listed cards (hide already-confirmed listings)
  grid.innerHTML = DIR_LIST
    .filter(d => (dirState[d.id]?.status || 'idle') !== 'listed')
    .map(d => _buildDirCard(d, dirState[d.id]))
    .join('');
  _updateDirSummary();
}

document.getElementById('scan-dir-btn').addEventListener('click', async () => {
  const cfg = await fetch('/api/config').then(r => r.json()).catch(() => ({}));
  if (!cfg?.target?.domain) {
    toast('Configure your domain in Settings first', 'error');
    switchTab('settings');
    return;
  }

  if (dirSource) { dirSource.close(); dirSource = null; }

  // Reset state & render idle cards
  dirState = {};
  DIR_LIST.forEach(d => dirState[d.id] = {status:'idle'});
  loadDirectories();
  document.getElementById('dir-summary').style.display = 'none';
  document.getElementById('badge-dirs').style.display  = 'none';

  const btn   = document.getElementById('scan-dir-btn');
  const inner = document.getElementById('scan-dir-inner');
  btn.disabled = true;
  inner.innerHTML = `<span class="btn-spinner" style="border-color:rgba(255,255,255,.3);border-top-color:#fff;width:11px;height:11px"></span> Scanning…`;

  dirSource = new EventSource('/api/directory-scan');

  dirSource.onmessage = e => {
    const msg = JSON.parse(e.data);

    if (msg.type === 'error') {
      toast(msg.text || 'Scan error', 'error');
      btn.disabled = false;
      inner.textContent = 'Scan Directories';
      dirSource.close(); dirSource = null;
      return;
    }

    if (msg.type === 'checking') {
      dirState[msg.id] = {status:'checking'};
      _updateDirCard(msg.id, dirState[msg.id]);
    }

    if (msg.type === 'result') {
      const r = msg.directory;
      dirState[r.id] = {status: r.status, submit_url: r.submit_url};
      _updateDirCard(r.id, dirState[r.id]);
      _updateDirSummary();
    }

    if (msg.type === 'done') {
      dirSource.close(); dirSource = null;
      btn.disabled = false;
      inner.innerHTML = `<svg viewBox="0 0 24 24" fill="currentColor" width="13" height="13"><path d="M17.65 6.35A7.958 7.958 0 0012 4c-4.42 0-7.99 3.58-7.99 8s3.57 8 7.99 8c3.73 0 6.84-2.55 7.73-6h-2.08A5.99 5.99 0 0112 18c-3.31 0-6-2.69-6-6s2.69-6 6-6c1.66 0 3.14.69 4.22 1.78L13 11h7V4l-2.35 2.35z"/></svg> Re-scan`;
      const missing = Object.values(dirState).filter(v => v.status === 'not_listed').length;
      toast(
        missing > 0
          ? `Found ${missing} unlisted director${missing!==1?'ies':'y'} — submit now!`
          : 'Scan complete',
        missing > 0 ? 'info' : 'success',
        5000
      );
    }
  };

  dirSource.onerror = () => {
    btn.disabled = false;
    inner.textContent = 'Scan Directories';
    toast('Scan disconnected — try again', 'error');
    if (dirSource) { dirSource.close(); dirSource = null; }
  };
});

// ══ RUN ════════════════════════════════════════════════════
const terminal     = document.getElementById('terminal');
const runBtn       = document.getElementById('run-btn');
const indicator    = document.getElementById('run-indicator');
const progressWrap = document.getElementById('run-progress-wrap');
let isRunning = false;
let eventSource = null;

function appendLog(text, cls='') {
  terminal.querySelector('.term-placeholder')?.remove();
  const span = document.createElement('span');
  if (cls) span.className = cls;
  span.textContent = text + '\n';
  terminal.appendChild(span);
  terminal.scrollTop = terminal.scrollHeight;
}

async function startRun() {
  if (isRunning) return;
  const checked = [...document.querySelectorAll('input[name="strategy"]:checked')];
  if (!checked.length) { toast('Select at least one strategy','error'); return; }

  const strategies = checked.map(c=>c.value);
  const maxResults = parseInt(document.getElementById('max-results').value)||20;
  const skipEmails = document.getElementById('skip-emails').checked;

  const res = await fetch('/api/run', {
    method:'POST', headers:{'Content-Type':'application/json'},
    body: JSON.stringify({ strategies, max_results:maxResults, skip_emails:skipEmails }),
  });
  if (!res.ok) { toast((await res.json().catch(()=>({}))).error||'Could not start','error'); return; }

  isRunning = true;
  runBtn.disabled = true;
  runBtn.innerHTML = `<span class="btn-spinner"></span> Running…`;
  indicator.style.display    = 'flex';
  progressWrap.style.display = 'block';
  terminal.innerHTML = '';
  appendLog(`▶  Strategies: ${strategies.join(', ')}  |  Max: ${maxResults}`, 'log-info');
  appendLog('', '');

  document.getElementById('step-2')?.classList.add('active');
  document.getElementById('step-3')?.classList.remove('active','done');

  eventSource = new EventSource('/api/run/stream');
  eventSource.onmessage = e => {
    const msg = JSON.parse(e.data);
    if (msg.type==='log') {
      const l = msg.text.toLowerCase();
      appendLog(msg.text,
        l.includes('error')||l.includes('failed') ? 'log-error' :
        l.includes('warn') ? 'log-warn' :
        l.includes('✓')||l.includes('found')||l.includes('done') ? 'log-info' : '');
    }
    if (msg.type==='done') finishRun(msg.code===0);
    if (msg.type==='error') appendLog(`Error: ${msg.text}`,'log-error');
  };
  eventSource.onerror = () => { appendLog('\n✕  Disconnected.','log-error'); finishRun(false); };
}

function finishRun(ok) {
  isRunning = false;
  runBtn.disabled = false;
  runBtn.innerHTML = `<svg viewBox="0 0 24 24" fill="currentColor" width="14" height="14"><path d="M8 5v14l11-7z"/></svg> Start Prospecting`;
  indicator.style.display    = 'none';
  progressWrap.style.display = 'none';
  appendLog('', '');
  appendLog(ok ? '✓  Done! Check the Opportunities tab.' : '✗  Finished with errors.', ok?'log-done':'log-error');
  if (ok) {
    document.getElementById('step-2')?.classList.replace('active','done');
    document.getElementById('step-3')?.classList.add('active');
    toast('Prospecting complete — view opportunities →','success',5000);
  }
  if (eventSource) { eventSource.close(); eventSource=null; }
  fetch('/api/stats').then(r=>r.json()).then(refreshBadges);
}

function refreshBadges(s) {
  document.getElementById('badge-opps').textContent   = s.total       ?? 0;
  document.getElementById('badge-emails').textContent = s.email_drafts ?? 0;
}

runBtn.addEventListener('click', startRun);
document.getElementById('clear-log-btn').addEventListener('click', ()=>{
  terminal.innerHTML = '<span class="term-placeholder">Output streams here live when you start a run…</span>';
});

// ══ INIT ════════════════════════════════════════════════════
(async () => {
  // Sync running state from server
  const s = await fetch('/api/run/status').then(r=>r.json()).catch(()=>({active:false}));
  if (s.active) {
    isRunning = true;
    runBtn.disabled = true;
    runBtn.innerHTML = `<span class="btn-spinner"></span> Running…`;
    indicator.style.display    = 'flex';
    progressWrap.style.display = 'block';
    appendLog('Reconnected to active job…','log-info');
    eventSource = new EventSource('/api/run/stream');
    eventSource.onmessage = e => {
      const msg = JSON.parse(e.data);
      if (msg.type==='log')  appendLog(msg.text);
      if (msg.type==='done') finishRun(msg.code===0);
    };
  }
  const cfg = await fetch('/api/config').then(r=>r.json()).catch(()=>({}));
  updateRunWarning(cfg);
  switchTab('dashboard');
})();
