const listEl = document.querySelector('#list');
const emptyEl = document.querySelector('#empty');

// Store data globally for language switching
window.currentData = null;
window.renderWithLanguage = renderWithLanguage;

// Get current language from URL params or default to 'zh'
const urlParams = new URLSearchParams(location.search);
window.currentLang = urlParams.get('lang') || 'zh';

init();
async function init() {
  try {
    // 构建data.json的URL，确保在GitHub Pages环境下正确工作
let dataUrl;
if (window.location.pathname.includes('/curated-gems/')) {
    // GitHub Pages环境
    dataUrl = window.location.origin + '/curated-gems/data.json';
} else {
    // 本地开发环境
    dataUrl = './data.json';
}
const res = await fetch(dataUrl + '?_=' + Date.now(), { cache: 'no-store' });
    if (!res.ok) throw new Error('load fail');
    const items = await res.json();
    window.currentData = items;
    render(items);
  } catch (e) {
    listEl.innerHTML = '';
    const errorTexts = {
      zh: '数据加载失败',
      en: 'Failed to load data'
    };
    emptyEl.textContent = errorTexts[window.currentLang || 'zh'];
    emptyEl.classList.remove('hidden');
  }
}

function render(items) {
  if (!items?.length) { 
    const emptyTexts = {
      zh: '暂无内容',
      en: 'No content available'
    };
    emptyEl.textContent = emptyTexts[window.currentLang || 'zh'];
    emptyEl.classList.remove('hidden'); 
    return; 
  }
  emptyEl.classList.add('hidden');
  listEl.innerHTML = items.map(item => card(item, window.currentLang || 'zh')).join('');
}

function renderWithLanguage(items, lang) {
  if (!items?.length) { 
    const emptyTexts = {
      zh: '暂无内容',
      en: 'No content available'
    };
    emptyEl.textContent = emptyTexts[lang];
    emptyEl.classList.remove('hidden'); 
    return; 
  }
  emptyEl.classList.add('hidden');
  listEl.innerHTML = items.map(item => card(item, lang)).join('');
}
function card(item, lang = 'zh'){
  const tagsArray = lang === 'zh' ? (item.tags_zh || item.tags || []) : (item.tags || []);
  const tags = tagsArray.join(', ');
  const title = lang === 'zh' ? (item.title_zh || item.title) : (item.title_en || item.title);
  const desc = lang === 'zh' ? (item.summary_zh || '') : (item.summary_en || '');
  const quote = lang === 'zh' ? (item.best_quote_zh || '') : (item.best_quote_en || '');
  const quoteWrapper = lang === 'zh' ? '「」' : '""';
  const aiSummaryLabel = lang === 'zh' ? 'AI总结：' : 'AI Summary: ';
  
  return `
    <article class="card">
      <h3><a href="${item.link}" target="_blank" rel="noopener">${esc(title)}</a></h3>
      ${desc ? `<p><span class="ai-label">${aiSummaryLabel}</span>${esc(desc)}</p>` : ''}
      ${quote ? `<blockquote>${quoteWrapper[0]}${esc(quote)}${quoteWrapper[1]}</blockquote>` : ''}
      <div class="meta">${esc(item.source)} · ${esc(tags)} · ${esc(item.date||'')}</div>
    </article>
  `;
}

function esc(s) { return String(s || '').replace(/[&<>"']/g, m => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' }[m])); }
