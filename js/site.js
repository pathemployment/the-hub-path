// theHUB @PATH — site interactions
(function () {
  'use strict';

  // ---- Mobile nav toggle ----
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

  // ---- Active nav link based on current page ----
  const path = location.pathname.split('/').pop() || 'index.html';
  document.querySelectorAll('.nav__links a').forEach(a => {
    const href = a.getAttribute('href');
    if (href === path || (path === '' && href === 'index.html')) {
      a.classList.add('is-active');
    }
  });

  // ---- Footer year ----
  const yearEl = document.querySelector('#year');
  if (yearEl) yearEl.textContent = new Date().getFullYear();

  // ---- Cookie / analytics consent ----
  const banner = document.querySelector('#cookie-banner');
  const CONSENT_KEY = 'hub-analytics-consent';

  function loadAnalytics() {
    // TODO: Replace G-XXXXXXXXXX with the Hub's Google Analytics 4 Measurement ID
    const GA_ID = 'G-XXXXXXXXXX';
    if (!GA_ID || GA_ID.includes('XXXX')) return; // safety: don't load placeholder

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
  if (consent === 'accepted') {
    loadAnalytics();
  } else if (!consent && banner) {
    banner.classList.add('is-visible');
  }

  document.querySelectorAll('[data-consent]').forEach(btn => {
    btn.addEventListener('click', () => {
      const choice = btn.getAttribute('data-consent');
      localStorage.setItem(CONSENT_KEY, choice);
      if (banner) banner.classList.remove('is-visible');
      if (choice === 'accepted') loadAnalytics();
    });
  });
})();

// ---- Job board (runs only on jobs page) ----
(function () {
  const list = document.querySelector('#job-list');
  if (!list) return;

  const search = document.querySelector('#job-search');
  const cat = document.querySelector('#job-category');
  const type = document.querySelector('#job-type');
  const empty = document.querySelector('#job-empty');

  const jobs = (window.HUB_JOBS || []).slice();
  if (!jobs.length) {
    list.innerHTML = '<p>No jobs posted yet. Check back soon.</p>';
    return;
  }
  populateFilters();
  render();

  function populateFilters() {
    const cats = [...new Set(jobs.map(j => j.category).filter(Boolean))].sort();
    const types = [...new Set(jobs.map(j => j.type).filter(Boolean))].sort();
    cats.forEach(c => cat.appendChild(opt(c)));
    types.forEach(t => type.appendChild(opt(t)));
  }
  function opt(v) { const o = document.createElement('option'); o.value = v; o.textContent = v; return o; }

  function render() {
    const q = (search.value || '').toLowerCase();
    const c = cat.value;
    const t = type.value;
    const filtered = jobs.filter(j => {
      if (c && j.category !== c) return false;
      if (t && j.type !== t) return false;
      if (q && !(j.title + ' ' + j.employer + ' ' + (j.location||'')).toLowerCase().includes(q)) return false;
      return true;
    });
    list.innerHTML = '';
    empty.classList.toggle('hidden', filtered.length > 0);
    filtered.forEach(j => list.appendChild(card(j)));
  }

  function card(j) {
    const el = document.createElement('article');
    el.className = 'job';
    el.innerHTML = `
      <div>
        <h3>${escape(j.title)}</h3>
        <div class="job__meta">${escape(j.employer)} &middot; ${escape(j.location||'')}</div>
        <div class="mt-1">
          ${j.type ? `<span class="job__tag">${escape(j.type)}</span>` : ''}
          ${j.category ? `<span class="job__tag">${escape(j.category)}</span>` : ''}
          ${j.posted ? `<span class="job__meta">Posted ${escape(j.posted)}</span>` : ''}
        </div>
      </div>
      <div>
        ${j.url ? `<a class="btn btn--primary" href="${escape(j.url)}" target="_blank" rel="noopener">View &amp; Apply</a>` : ''}
      </div>
    `;
    return el;
  }
  function escape(s) {
    return String(s == null ? '' : s).replace(/[&<>"']/g, c => (
      {'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]
    ));
  }

  [search, cat, type].forEach(el => el && el.addEventListener('input', render));
})();

// ---- Events loader ----
(function () {
  const featured = document.querySelector('#event-featured');
  const upcoming = document.querySelector('#event-upcoming');
  if (!featured && !upcoming) return;
  const data = window.HUB_EVENTS || [];
  const now = new Date();
  const sorted = data
    .map(e => ({ ...e, _d: new Date(e.date) }))
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
  if (upcoming) {
    upcoming.innerHTML = rest.length
      ? rest.map(eventCardHTML).join('')
      : '<p>No additional events scheduled. Check back soon.</p>';
  }

  function fmt(d) {
    return new Date(d).toLocaleDateString('en-CA', { weekday: 'long', month: 'long', day: 'numeric', year: 'numeric' });
  }
  function featuredHTML(e) {
    return `
      <div class="event__image" style="${e.image ? `background-image:url('${e.image}')` : ''}"></div>
      <div class="event__body">
        <span class="event__date">${fmt(e.date)}</span>
        <h2>${e.title}</h2>
        <p class="lead">${e.description || ''}</p>
        ${e.location ? `<p><strong>Where:</strong> ${e.location}</p>` : ''}
        ${e.time ? `<p><strong>Time:</strong> ${e.time}</p>` : ''}
        ${e.registerUrl ? `<a class="btn btn--accent" href="${e.registerUrl}" target="_blank" rel="noopener">Register</a>` : ''}
      </div>
    `;
  }
  function eventCardHTML(e) {
    const ext = e.registerUrl && /^https?:/.test(e.registerUrl);
    return `
      <article class="card">
        <span class="event__date">${fmt(e.date)}</span>
        <h3>${e.title}</h3>
        ${e.time ? `<p class="card__meta">${e.time}${e.location ? ' · ' + e.location : ''}</p>` : ''}
        <p>${e.description || ''}</p>
        <div class="card__footer">
          ${e.registerUrl ? `<a class="btn btn--outline" href="${e.registerUrl}"${ext ? ' target="_blank" rel="noopener"' : ''}>Register</a>` : ''}
        </div>
      </article>
    `;
  }
})();

// ---- Newsletter loader ----
(function () {
  const list = document.querySelector('#newsletter-list');
  if (!list) return;
  const data = window.HUB_NEWSLETTERS || [];
  if (!data.length) {
    list.innerHTML = '<p>Newsletter archive coming soon.</p>';
    return;
  }
  const sorted = data.slice().sort((a,b) => new Date(b.date) - new Date(a.date));
  list.innerHTML = sorted.map(n => {
        const d = new Date(n.date);
        const month = d.toLocaleDateString('en-CA', { month: 'short' });
        const year = d.getFullYear();
        const primaryLink = n.page
          ? `<a class="btn btn--primary" href="${n.page}">Read</a>`
          : (n.file ? `<a class="btn btn--outline" href="${n.file}" target="_blank" rel="noopener">Open PDF</a>` : '');
        const pdfLink = (n.page && n.file)
          ? `<a class="btn btn--outline" href="${n.file}" target="_blank" rel="noopener">PDF</a>`
          : '';
        const initials = n.author && n.author.name
          ? n.author.name.split(/\s+/).map(s => s[0]).slice(0,2).join('').toUpperCase()
          : '';
        const authorBlock = n.author
          ? `<div class="newsletter__author">
               ${n.author.photo
                 ? `<span class="newsletter__avatar" style="background-image:url('${n.author.photo}')" aria-hidden="true"></span>`
                 : `<span class="newsletter__avatar newsletter__avatar--initials" aria-hidden="true">${initials}</span>`}
               <span class="newsletter__author-name">${n.author.name}</span>
             </div>`
          : '';
        return `
          <article class="newsletter">
            <div class="newsletter__date">
              <span class="month">${month}</span>
              <span class="year">${year}</span>
            </div>
            <div>
              <h3>${n.title}</h3>
              ${authorBlock}
              <p>${n.summary || ''}</p>
            </div>
            <div style="display:flex; gap:.5rem; flex-wrap:wrap;">${primaryLink}${pdfLink}</div>
          </article>
        `;
  }).join('');
})();
