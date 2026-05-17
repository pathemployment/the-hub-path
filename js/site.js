// theHUB @PATH - site interactions
(function () {
  'use strict';

  const toggle = document.querySelector('.nav__toggle');
  const links = document.querySelector('.nav__links');
  if (toggle && links) {
    toggle.addEventListener('click', () => {
      const open = links.classList.toggle('is-open');
      toggle.setAttribute('aria-expanded', open ? 'true' : 'false');
    });
    links.querySelectorAll('a').forEach(a => {
      a.addEventListener('click', () => links.classList.remove('is-open'));
    });
  }

  const path = location.pathname.split('/').pop() || 'index.html';
  document.querySelectorAll('.nav__links a').forEach(a => {
    const href = a.getAttribute('href');
    if (href === path || (path === '' && href === 'index.html')) a.classList.add('is-active');
  });

  const yearEl = document.querySelector('#year');
  if (yearEl) yearEl.textContent = new Date().getFullYear();

  const banner = document.querySelector('#cookie-banner');
  const CONSENT_KEY = 'hub-analytics-consent';

  function loadAnalytics() {
    const GA_ID = 'G-VBXW6R9FE0';
    if (!GA_ID || GA_ID.includes('XXXX')) return;
    const s = document.createElement('script');
    s.async = true;
    s.src = 'https://www.googletagmanager.com/gtag/js?id=' + GA_ID;
    document.head.appendChild(s);
    window.dataLayer = window.dataLayer || [];
    function gtag() { dataLayer.push(arguments); }
    window.gtag = gtag;
    gtag('js', new Date());
    gtag('config', GA_ID, { anonymize_ip: true });
  }

  const consent = localStorage.getItem(CONSENT_KEY);
  if (consent === 'accepted') loadAnalytics();
  else if (!consent && banner) banner.classList.add('is-visible');

  document.querySelectorAll('[data-consent]').forEach(btn => {
    btn.addEventListener('click', () => {
      const choice = btn.getAttribute('data-consent');
      localStorage.setItem(CONSENT_KEY, choice);
      if (banner) banner.classList.remove('is-visible');
      if (choice === 'accepted') loadAnalytics();
    });
  });
})();

// ---- Job board welcome tour ----
(function () {
  const overlay = document.querySelector('#tour-overlay');
  if (!overlay) return;
  const TOUR_KEY = 'hub-job-tour-seen';
  const closeBtn = document.querySelector('#tour-close');
  const dismissBtn = document.querySelector('#tour-dismiss');
  const showBtn = document.querySelector('#show-tour');

  function open() { overlay.hidden = false; document.body.style.overflow = 'hidden'; }
  function close() {
    overlay.hidden = true;
    document.body.style.overflow = '';
    try { localStorage.setItem(TOUR_KEY, '1'); } catch (e) {}
  }

  if (!localStorage.getItem(TOUR_KEY)) {
    setTimeout(open, 400);
  }
  if (closeBtn) closeBtn.addEventListener('click', close);
  if (dismissBtn) dismissBtn.addEventListener('click', close);
  if (showBtn) showBtn.addEventListener('click', open);
  overlay.addEventListener('click', e => { if (e.target === overlay) close(); });
  document.addEventListener('keydown', e => { if (e.key === 'Escape' && !overlay.hidden) close(); });
})();

// ---- Job board ----
(function () {
  const list = document.querySelector('#job-list');
  if (!list) return;
  const search = document.querySelector('#job-search');
  const regionSel = document.querySelector('#job-region');
  const catSel = document.querySelector('#job-category');
  const eduSel = document.querySelector('#job-edu');
  const srcSel = document.querySelector('#job-source');
  const submittedOnly = document.querySelector('#job-submitted-only');
  const empty = document.querySelector('#job-empty');
  const countEl = document.querySelector('#job-count');
  const statsEl = document.querySelector('#jobs-stats');
  const REGION_ORDER = ['Hamilton', 'Halton', 'Niagara', 'Brantford', 'Haldimand-Norfolk', 'Other'];

  const jobs = (window.HUB_JOBS || []).slice();
  const meta = window.HUB_JOBS_META || {};
  if (!jobs.length) { list.innerHTML = '<p>No jobs posted yet. Check back soon.</p>'; return; }
  jobs.sort((a, b) => (b.date || '').localeCompare(a.date || ''));

  if (statsEl) {
    const sub = jobs.filter(j => j.submitted).length;
    statsEl.innerHTML =
      '<span><strong>' + jobs.length + '</strong> listings</span>' +
      '<span><strong>' + sub + '</strong> submitted by PATH</span>' +
      (meta.generated ? '<span>Updated <strong>' + meta.generated + '</strong></span>' : '') +
      (meta.window_days ? '<span>Past <strong>' + meta.window_days + ' days</strong></span>' : '');
  }

  const regions = REGION_ORDER.filter(r => jobs.some(j => j.region === r));
  const cats = [...new Set(jobs.map(j => j.category).filter(Boolean))].sort();
  const sources = [...new Set(jobs.map(j => j.source).filter(Boolean))].sort();
  if (regionSel) regionSel.innerHTML = '<option value="">All regions</option>' + regions.map(r => '<option value="' + esc(r) + '">' + esc(r) + '</option>').join('');
  if (catSel) catSel.innerHTML = '<option value="">All job types</option>' + cats.map(c => '<option value="' + esc(c) + '">' + esc(c) + '</option>').join('');
  if (srcSel) srcSel.innerHTML = '<option value="">All sources</option>' + sources.map(s => '<option value="' + esc(s) + '">' + esc(s) + '</option>').join('');

  render();
  [search, regionSel, catSel, eduSel, srcSel, submittedOnly].forEach(el => el && el.addEventListener('input', render));

  function render() {
    const q = (search.value || '').trim().toLowerCase();
    const region = regionSel ? regionSel.value : '';
    const cat = catSel ? catSel.value : '';
    const edu = eduSel ? eduSel.value : '';
    const src = srcSel ? srcSel.value : '';
    const subOnly = submittedOnly && submittedOnly.checked;
    const filtered = jobs.filter(j => {
      if (region && j.region !== region) return false;
      if (cat && j.category !== cat) return false;
      if (edu && j.edu_level !== edu) return false;
      if (src && j.source !== src) return false;
      if (subOnly && !j.submitted) return false;
      if (q) {
        const hay = (j.title + ' ' + j.employer + ' ' + (j.location || '')).toLowerCase();
        if (!hay.includes(q)) return false;
      }
      return true;
    });
    if (countEl) {
      countEl.textContent = filtered.length === jobs.length
        ? 'Showing all ' + jobs.length + ' listings'
        : 'Showing ' + filtered.length + ' of ' + jobs.length + ' listings';
    }
    list.innerHTML = renderGrouped(filtered);
    if (empty) empty.classList.toggle('hidden', filtered.length > 0);
  }

  function renderGrouped(filtered) {
    const byRegion = {};
    filtered.forEach(j => {
      const r = j.region || 'Other';
      const c = j.category || 'Other';
      if (!byRegion[r]) byRegion[r] = {};
      if (!byRegion[r][c]) byRegion[r][c] = [];
      byRegion[r][c].push(j);
    });
    const regionList = REGION_ORDER.filter(r => byRegion[r]);
    return regionList.map((r) => {
      const catMap = byRegion[r];
      const catList = Object.keys(catMap).sort();
      const regionCount = catList.reduce((n, c) => n + catMap[c].length, 0);
      // All regions collapsed by default - users open the one they want
      return (
        '<details class="region-block">' +
          '<summary class="region-heading">' +
            '<span class="region-heading__name">' + esc(r) + '</span>' +
            '<span class="region-heading__count">' + regionCount + ' listing' + (regionCount === 1 ? '' : 's') + '</span>' +
          '</summary>' +
          catList.map(c =>
            '<details class="category-block" open>' +
              '<summary class="category-heading">' + esc(c) + ' <span class="category-heading__count">(' + catMap[c].length + ')</span></summary>' +
              catMap[c].map(jobCard).join('') +
            '</details>'
          ).join('') +
        '</details>'
      );
    }).join('');
  }

  function jobCard(j) {
    const star = j.submitted ? '<span class="star-submitted" title="Submitted by PATH">&#11088; Submitted by PATH</span>' : '';
    const posted = j.date ? 'Posted ' + fmtDate(j.date) : '';
    const tips = (j.tip_resume || j.tip_cover)
      ? '<details class="job-tips"><summary>Resume &amp; cover letter tips</summary>' +
        (j.tip_resume ? '<div class="tip"><span class="tip-label">Resume</span> ' + esc(j.tip_resume) + '</div>' : '') +
        (j.tip_cover  ? '<div class="tip"><span class="tip-label">Cover letter</span> ' + esc(j.tip_cover) + '</div>' : '') +
        '</details>'
      : '';
    const clientLink = (j.client_subject && j.client_body)
      ? '<a class="btn btn--outline btn--small" href="mailto:?subject=' + encodeURIComponent(j.client_subject) + '&body=' + encodeURIComponent(j.client_body) + '" title="Send to client">&#9993; Send to client</a>'
      : '';
    return '<article class="job-card" data-edu="' + esc(j.edu_level || '') + '">' +
      '<div class="job-card__main">' +
        '<h3 class="job-card__title">' +
          (j.url ? '<a href="' + esc(j.url) + '" target="_blank" rel="noopener">' + esc(j.title) + '</a>' : esc(j.title)) +
          ' ' + star +
        '</h3>' +
        '<p class="job-card__meta">' +
          '<span><strong>' + esc(j.employer || '') + '</strong></span>' +
          (j.location ? '<span class="sep">&middot;</span><span>' + esc(j.location) + '</span>' : '') +
          (j.edu_label ? '<span class="sep">&middot;</span><span class="edu-tag edu-' + esc(j.edu_level) + '">' + esc(j.edu_label) + '</span>' : '') +
        '</p>' +
        tips +
      '</div>' +
      '<div class="job-card__aside">' +
        '<div class="job-card__salary"><strong>' + esc(j.salary || 'Not listed') + '</strong></div>' +
        (posted ? '<div class="job-card__posted"><span class="dot"></span>' + esc(posted) + '</div>' : '') +
        (j.source ? '<span class="source-pill source-pill--' + slug(j.source) + '">' + esc(j.source) + '</span>' : '') +
        (j.url ? '<a class="btn btn--primary btn--small" href="' + esc(j.url) + '" target="_blank" rel="noopener">Apply &#8599;</a>' : '') +
        clientLink +
      '</div>' +
    '</article>';
  }

  function esc(s) { return String(s == null ? '' : s).replace(/[&<>"']/g, c => ({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'})[c]); }
  function slug(s) { return String(s).toLowerCase().replace(/[^a-z0-9]+/g, '-'); }
  function fmtDate(iso) { try { return new Date(iso).toLocaleDateString('en-CA', { month: 'short', day: 'numeric' }); } catch (e) { return iso; } }
})();

// ---- Events ----
(function () {
  const featured = document.querySelector('#event-featured');
  const upcoming = document.querySelector('#event-upcoming');
  if (!featured && !upcoming) return;
  const data = window.HUB_EVENTS || [];
  const now = new Date();
  const sorted = data
    .map(e => Object.assign({}, e, { _d: new Date(e.date) }))
    .filter(e => e._d >= new Date(now.toDateString()))
    .sort((a, b) => a._d - b._d);
  if (!sorted.length) {
    if (featured) featured.innerHTML = '<p>No upcoming events scheduled. Check back soon.</p>';
    if (upcoming) upcoming.innerHTML = '';
    return;
  }
  const feat = sorted.find(e => e.featured) || sorted[0];
  if (feat && featured) featured.innerHTML = featuredHTML(feat);
  const rest = sorted.filter(e => e !== feat);
  if (upcoming) upcoming.innerHTML = rest.length ? rest.map(eventCardHTML).join('') : '<p>No additional events scheduled. Check back soon.</p>';

  function fmt(d) { return new Date(d).toLocaleDateString('en-CA', { weekday: 'long', month: 'long', day: 'numeric', year: 'numeric' }); }
  function dateParts(d) {
    const dt = new Date(d);
    return {
      day: dt.toLocaleDateString('en-CA', { weekday: 'long' }),
      month: dt.toLocaleDateString('en-CA', { month: 'short' }).toUpperCase(),
      num: dt.getDate(),
      year: dt.getFullYear()
    };
  }
  function featuredHTML(e) {
    const dp = dateParts(e.date);
    const visual = e.image
      ? '<div class="event__image" style="background-image:url(\'' + e.image + '\')"></div>'
      : '<div class="event__datetile" aria-hidden="true">' +
          '<span class="event__datetile-day">' + dp.day + '</span>' +
          '<span class="event__datetile-month">' + dp.month + '</span>' +
          '<span class="event__datetile-num">' + dp.num + '</span>' +
          '<span class="event__datetile-year">' + dp.year + '</span>' +
        '</div>';
    const ext = e.registerUrl && /^https?:/.test(e.registerUrl);
    return visual +
      '<div class="event__body">' +
        '<span class="event__featured-tag">Featured Event</span>' +
        '<h2>' + e.title + '</h2>' +
        '<p class="lead">' + (e.description || '') + '</p>' +
        (e.location ? '<p><strong>Where:</strong> ' + e.location + '</p>' : '') +
        (e.time ? '<p><strong>When:</strong> ' + fmt(e.date) + ' &middot; ' + e.time + '</p>' : '<p><strong>When:</strong> ' + fmt(e.date) + '</p>') +
        (e.registerUrl ? '<a class="btn btn--accent" href="' + e.registerUrl + '"' + (ext ? ' target="_blank" rel="noopener"' : '') + '>Register</a>' : '') +
      '</div>';
  }
  function eventCardHTML(e) {
    const ext = e.registerUrl && /^https?:/.test(e.registerUrl);
    return '<article class="card">' +
      '<span class="event__date">' + fmt(e.date) + '</span>' +
      '<h3>' + e.title + '</h3>' +
      (e.time ? '<p class="card__meta">' + e.time + (e.location ? ' &middot; ' + e.location : '') + '</p>' : '') +
      '<p>' + (e.description || '') + '</p>' +
      '<div class="card__footer">' +
        (e.registerUrl ? '<a class="btn btn--outline" href="' + e.registerUrl + '"' + (ext ? ' target="_blank" rel="noopener"' : '') + '>Register</a>' : '') +
      '</div>' +
    '</article>';
  }
})();

// ---- Newsletter sidebar ----
(function () {
  const sidebar = document.querySelector('#newsletter-sidebar-list');
  if (!sidebar) return;
  const data = window.HUB_NEWSLETTERS || [];
  const sorted = data.slice().sort((a, b) => new Date(b.date) - new Date(a.date));
  const here = location.pathname.split('/').pop();
  sidebar.innerHTML = sorted.map(n => {
    const d = new Date(n.date);
    const label = d.toLocaleDateString('en-CA', { month: 'long', year: 'numeric' });
    const href = n.page || '#';
    const current = (n.page && href === here) ? ' is-current' : '';
    return '<li><a href="' + href + '" class="' + current.trim() + '"><span class="sidebar-date">' + label + '</span><span class="sidebar-title">' + n.title + '</span></a></li>';
  }).join('');
})();
