const b=document.querySelector('.menu'),n=document.querySelector('.nav nav');if(b&&n)b.addEventListener('click',()=>{const o=n.classList.toggle('open');b.setAttribute('aria-expanded',o?'true':'false');b.setAttribute('aria-label',o?'Chiudi menu':'Apri menu')});const y=document.getElementById('year');if(y)y.textContent=new Date().getFullYear();

(() => {
  const KEY='dm_cookie_consent_v1';
  const read=()=>{try{return JSON.parse(localStorage.getItem(KEY)||'null')}catch{return null}};
  const maps=[...document.querySelectorAll('[data-map-src]')];
  const loadMaps=()=>maps.forEach(el=>{if(!el.querySelector('iframe')){const f=document.createElement('iframe');f.src=el.dataset.mapSrc;f.title=el.dataset.mapTitle||'Mappa Google';f.loading='lazy';f.referrerPolicy='no-referrer-when-downgrade';f.allowFullscreen=true;el.replaceChildren(f)}});
  const blockMaps=()=>maps.forEach(el=>{if(!el.querySelector('.map-consent-placeholder')){const p=document.createElement('div');p.className='map-consent-placeholder';p.innerHTML='<span>Google Maps è un servizio esterno</span><p>Per visualizzare la mappa è necessario consentire il caricamento dei contenuti esterni.</p><button type="button" class="map-load-button">Carica la mappa</button>';p.querySelector('button').addEventListener('click',()=>{const current=read()||{necessary:true,external:false,updatedAt:new Date().toISOString()};current.external=true;current.updatedAt=new Date().toISOString();localStorage.setItem(KEY,JSON.stringify(current));loadMaps();closeBanner()});el.replaceChildren(p)}}); 
  let banner;
  function closeBanner(){if(banner)banner.remove();banner=null}
  function save(external){localStorage.setItem(KEY,JSON.stringify({necessary:true,external:!!external,updatedAt:new Date().toISOString()}));if(external)loadMaps();else blockMaps();closeBanner()}
  function openBanner(settings=false){
    closeBanner();
    banner=document.createElement('section');banner.className='cookie-banner';banner.setAttribute('role','dialog');banner.setAttribute('aria-modal','true');banner.setAttribute('aria-labelledby','cookie-title');
    banner.innerHTML='<div class="cookie-inner"><div class="cookie-copy"><span class="cookie-kicker">Le tue preferenze</span><h2 id="cookie-title">La tua privacy, con chiarezza.</h2><p>Utilizziamo solo le tecnologie necessarie al funzionamento del sito. Le mappe Google vengono caricate soltanto con il tuo consenso, perché possono trasmettere dati al fornitore esterno.</p><a href="cookie-policy.html">Leggi la Cookie Policy</a></div><div class="cookie-actions"><button type="button" class="cookie-accept">Accetta tutti</button><button type="button" class="cookie-reject">Solo necessari</button><button type="button" class="cookie-settings">Personalizza</button></div></div><div class="cookie-preferences" hidden><p><strong>Cookie e contenuti esterni</strong></p><label><input type="checkbox" checked disabled> Tecnici e necessari <small>Sempre attivi</small></label><label><input type="checkbox" class="external-choice"> Mappe e contenuti esterni <small>Google Maps nelle pagine delle sedi</small></label><button type="button" class="cookie-save">Salva le preferenze</button></div>';
    document.body.appendChild(banner);
    const pref=banner.querySelector('.cookie-preferences');
    banner.querySelector('.cookie-accept').addEventListener('click',()=>save(true));
    banner.querySelector('.cookie-reject').addEventListener('click',()=>save(false));
    banner.querySelector('.cookie-settings').addEventListener('click',()=>{pref.hidden=!pref.hidden;banner.querySelector('.external-choice').checked=!!read()?.external});
    banner.querySelector('.cookie-save').addEventListener('click',()=>save(banner.querySelector('.external-choice').checked));
  }
  const consent=read();
  if(consent?.external)loadMaps();else blockMaps();
  if(!consent)openBanner();
  const footer=document.querySelector('footer .foot');
  if(footer&&!footer.querySelector('.cookie-preferences-link')){const a=document.createElement('a');a.href='#cookie-preferences';a.className='cookie-preferences-link';a.textContent='Preferenze cookie';a.addEventListener('click',e=>{e.preventDefault();openBanner(true)});footer.appendChild(a)}
})();

// Caricamento degli approfondimenti pubblicati automaticamente dopo i controlli sulle fonti
(() => {
  const container = document.querySelector('#articoli .insights-empty');
  if (!container) return;
  fetch('approfondimenti/articoli.json', { cache: 'no-store' })
    .then(response => response.ok ? response.json() : [])
    .then(items => {
      if (!Array.isArray(items) || !items.length) return;
      const grid = document.createElement('div');
      grid.className = 'insights-published-grid';
      items.forEach(item => {
        const card = document.createElement('article');
        card.className = 'insights-published-card';
        const category = document.createElement('span');
        category.className = 'topic-label';
        category.textContent = item.category || 'Approfondimento';
        const title = document.createElement('h3');
        title.textContent = item.title || 'Approfondimento notarile';
        const desc = document.createElement('p');
        desc.textContent = item.description || '';
        const date = document.createElement('small');
        date.textContent = item.date || '';
        const link = document.createElement('a');
        link.href = item.url;
        link.textContent = 'Leggi l’approfondimento →';
        card.append(category, title, desc, date, link);
        grid.appendChild(card);
      });
      container.replaceWith(grid);
      const status = document.querySelector('.insights-status');
      if (status) status.textContent = 'APPROFONDIMENTI PUBBLICATI';
    })
    .catch(() => {});
})();

// Interazioni della pagina Approfondimenti
(() => {
  const topics = document.querySelectorAll('.insights-topic');
  topics.forEach((topic) => {
    topic.addEventListener('click', () => {
      const label = topic.querySelector('h3')?.textContent?.trim();
      const heading = document.querySelector('#articoli .insights-section-heading h2');
      if (heading && label) heading.textContent = 'Approfondimenti: ' + label;
    });
  });
})();
