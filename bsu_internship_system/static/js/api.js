/**
 * BSU OJT System — API Client & Shared UI Helpers
 */

/* ── API wrapper ── */
const API = {
  base: '/api',
  async req(method, path, body, isForm) {
    const opts = { method, credentials: 'same-origin' };
    if (body && !isForm) { opts.headers = { 'Content-Type': 'application/json' }; opts.body = JSON.stringify(body); }
    else if (body) { opts.body = body; }
    const res = await fetch(this.base + path, opts);
    const data = await res.json().catch(() => ({}));
    if (!res.ok) throw new Error(data.error || `HTTP ${res.status}`);
    return data;
  },
  get:    p       => API.req('GET',    p),
  post:   (p, b)  => API.req('POST',   p, b),
  put:    (p, b)  => API.req('PUT',    p, b),
  delete: p       => API.req('DELETE', p),
  upload: (p, f)  => API.req('POST',   p, f, true),
};

/* ── Session ── */
const Session = {
  get()  { try { return JSON.parse(localStorage.getItem('bsu_user') || 'null'); } catch { return null; } },
  set(u) { localStorage.setItem('bsu_user', JSON.stringify(u)); },
  clear(){ localStorage.removeItem('bsu_user'); },
  requireRole(...roles) {
    const u = this.get();
    if (!u) { location.href = '/login'; return null; }
    if (roles.length && !roles.includes(u.role)) { location.href = '/login'; return null; }
    return u;
  }
};

/* ── Toast ── */
function showToast(msg, type = 'info') {
  let c = document.getElementById('_tc');
  if (!c) {
    c = document.createElement('div');
    c.id = '_tc';
    c.style.cssText = 'position:fixed;bottom:1.5rem;right:1.5rem;z-index:9999;display:flex;flex-direction:column;gap:.45rem;';
    document.body.appendChild(c);
  }
  const colors = { ok:'#166534',danger:'#dc2626',warn:'#92400e',info:'#1e40af' };
  const t = document.createElement('div');
  t.style.cssText = `background:#fff;border-left:4px solid ${colors[type]||colors.info};border-radius:10px;padding:.82rem 1.15rem;box-shadow:0 4px 20px rgba(0,0,0,.13);display:flex;align-items:center;gap:.55rem;font-size:.875rem;color:#111827;min-width:230px;max-width:310px;animation:_tIn .2s ease;`;
  if (!document.getElementById('_ts')) {
    const s = document.createElement('style'); s.id='_ts';
    s.textContent = '@keyframes _tIn{from{opacity:0;transform:translateX(20px)}to{opacity:1;transform:none}}';
    document.head.appendChild(s);
  }
  t.textContent = msg; c.appendChild(t);
  setTimeout(() => { t.style.opacity='0'; t.style.transition='opacity .25s'; setTimeout(()=>t.remove(),260); }, 3500);
}

/* ── Modal ── */
function openModal(id)  { document.getElementById(id)?.classList.add('show'); }
function closeModal(id) { document.getElementById(id)?.classList.remove('show'); }
function initModals() {
  document.querySelectorAll('[data-md]').forEach(el => el.addEventListener('click', () => openModal(el.dataset.md)));
  document.querySelectorAll('.mdx,[data-close]').forEach(el => el.addEventListener('click', () => el.closest('.mo')?.classList.remove('show')));
  document.querySelectorAll('.mo').forEach(el => el.addEventListener('click', e => { if (e.target === el) el.classList.remove('show'); }));
}

/* ── Sidebar ── */
function initSidebar() {
  const sb = document.getElementById('sidebar');
  const ham = document.getElementById('hamburger');
  const main = document.getElementById('mainContent');
  const ov = document.getElementById('sbOverlay');
  const isPermanent = sb?.classList.contains('permanent');
  if (isPermanent) {
    // On mobile (<1000px), allow toggling; on desktop, sidebar stays open always
    const applyPermanent = () => {
      if (window.innerWidth > 1000) {
        sb?.classList.add('permanent');
        sb?.classList.remove('closed', 'open');
        main?.classList.add('sb-permanent');
        main?.classList.remove('exp');
        ov?.classList.remove('show');
      }
    };
    applyPermanent();
    window.addEventListener('resize', applyPermanent);
    ham?.addEventListener('click', () => {
      if (window.innerWidth <= 1000) {
        sb?.classList.toggle('open');
        sb?.classList.toggle('closed');
        ov?.classList.toggle('show');
      }
    });
    ov?.addEventListener('click', () => {
      if (window.innerWidth <= 1000) {
        sb?.classList.remove('open');
        sb?.classList.add('closed');
        ov?.classList.remove('show');
      }
    });
  } else {
    ham?.addEventListener('click', () => {
      sb?.classList.toggle('open');
      sb?.classList.toggle('closed');
      main?.classList.toggle('exp');
      ov?.classList.toggle('show');
    });
    ov?.addEventListener('click', () => { sb?.classList.remove('open'); ov?.classList.remove('show'); });
  }
}

/* ── Active nav ── */
function setActive(id) {
  document.querySelectorAll('.sb-nav a').forEach(a => a.classList.remove('on'));
  document.getElementById(id)?.classList.add('on');
}

/* ── Populate nav user ── */
function fillUser(user) {
  if (!user) return;
  const name = user.full_name || user.name || '—';
  const code = user.sr_code || user.role || '—';
  ['#navName','#sbName'].forEach(sel => { const el = document.querySelector(sel); if(el) el.textContent = name; });
  const sc = document.querySelector('#sbCode'); if(sc) sc.textContent = code;
  const rp = document.querySelector('.nb-role'); if(rp) rp.textContent = user.role;
}

/* ── Logout ── */
function initLogout() {
  document.querySelectorAll('.signout').forEach(a => {
    a.addEventListener('click', async e => {
      e.preventDefault();
      try { await API.post('/auth/logout'); } catch {}
      Session.clear();
      location.href = '/login';
    });
  });
}

/* ── Badge ── */
function badge(status) {
  const map = { pending:'bx-pending',approved:'bx-approved',rejected:'bx-rejected',active:'bx-active',
                ongoing:'bx-ongoing',completed:'bx-completed',student:'bx-student',
                facilitator:'bx-facilitator',admin:'bx-admin',inactive:'bx-inactive' };
  return `<span class="bx ${map[status]||''}">${status}</span>`;
}

/* ── Date format ── */
function fmtDate(dt) {
  if (!dt) return '—';
  return new Date(dt).toLocaleDateString('en-PH', { year:'numeric', month:'short', day:'numeric' });
}

/* ── Table search ── */
function initSearch(inputId, tbodyId) {
  const inp = document.getElementById(inputId);
  if (!inp) return;
  inp.addEventListener('input', () => {
    const q = inp.value.toLowerCase();
    document.querySelectorAll(`#${tbodyId} tr`).forEach(r => r.style.display = r.textContent.toLowerCase().includes(q) ? '' : 'none');
  });
}
