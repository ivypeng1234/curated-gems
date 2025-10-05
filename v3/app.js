// 第3课：信息筛选与分类管理
// 主要功能：智能标签筛选、搜索、排序、数据源筛选
let raw = [], view = [], activeSource = 'all', activeTags = new Set(['all']);
let searchEl, sortEl;

const $ = sel => document.querySelector(sel);

// Store data globally for language switching
window.currentData = null;
window.renderWithLanguage = renderWithLanguage;

// Get current language from URL params or default to 'zh'
const urlParams = new URLSearchParams(location.search);
window.currentLang = urlParams.get('lang') || 'zh';

// 由于脚本是动态加载的，DOM 可能已经准备好了
if (document.readyState === 'loading') {
  document.addEventListener('DOMContentLoaded', init);
} else {
  init();
}

async function init() {
  console.log('Init started');

  // 检查必要的 DOM 元素
  const listEl = $('#list');
  const emptyEl = $('#empty');
  const controlsEl = $('#controls');

  console.log('DOM elements:', { listEl, emptyEl, controlsEl });

  if (!listEl || !emptyEl || !controlsEl) {
    console.error('Missing required DOM elements');
    return;
  }

  mountControls();

  try {
    console.log('Fetching data...');
    raw = await loadData();
    window.currentData = raw;
    console.log('Data loaded:', raw.length, 'items');
    console.log('First item:', raw[0]);
  } catch (e) {
    console.error('Data loading failed:', e);
    $('#list').innerHTML = '';
    const lang = window.currentLang || 'zh';
    const errorTexts = {
      zh: '数据加载失败: ',
      en: 'Data loading failed: '
    };
    $('#empty').innerHTML = `<p>${errorTexts[lang]}${e.message}</p>`;
    return;
  }

  // 初始化渲染
  applyAndRender();
  bind();
  
  // 显示新手引导提示
  showWelcomeGuide();
}

// async function loadData() {
//   try {
//     const response = await fetch('../data.json');
//     if (!response.ok) {
//       throw new Error(`HTTP ${response.status}: ${response.statusText}`);
//     }
//     const data = await response.json();
    
//     if (!Array.isArray(data)) {
//       throw new Error('Invalid data format: expected array');
//     }
    
//     return data;
//   } catch (error) {
//     console.error('Failed to load data:', error);
//     throw error;
//   }
// }

async function loadData() {
  try {
    // 环境检测：根据URL路径判断是否在GitHub Pages环境
    let dataUrl;
    if (window.location.pathname.includes('/curated-gems/')) {
      // GitHub Pages环境
      dataUrl = window.location.origin + '/curated-gems/data.json';
    } else {
      // 本地开发环境
      dataUrl = './data.json';
    }
    
    const response = await fetch(dataUrl);
    if (!response.ok) {
      throw new Error(`HTTP ${response.status}: ${response.statusText}`);
    }
    const data = await response.json();
    
    if (!Array.isArray(data)) {
      throw new Error('Invalid data format: expected array');
    }
    
    return data;
  } catch (error) {
    console.error('Failed to load data:', error);
    throw error;
  }
}

function mountControls() {
  const lang = window.currentLang || 'zh';
  const texts = {
    zh: {
      search: '搜索文章标题、摘要...',
      sort: '排序方式',

      newest: '最新',
      oldest: '最旧',
      clearFilters: '清除所有筛选',
      sources: '数据源',
      tags: '标签',
      searchHint: '💡 提示：输入关键词快速查找相关内容',
      tagHint: '💡 提示：点击标签筛选内容，可以选择多个标签组合筛选',

      totalItems: '共找到 {count} 条信息',
      tagStats: '标签统计',
      statsTitle: '标签使用统计分析',
      statsHint: '💡 分析这些统计数据，找出标签使用规律',
      closeStats: '关闭统计'
    },
    en: {
      search: 'Search articles, summaries...',
      sort: 'Sort by',

      newest: 'Newest',
      oldest: 'Oldest',
      clearFilters: 'Clear all filters',
      sources: 'Sources',
      tags: 'Tags',
      searchHint: '💡 Tip: Enter keywords to quickly find relevant content',
      tagHint: '💡 Tip: Click tags to filter content, you can select multiple tags',

      totalItems: 'Found {count} items',
      tagStats: 'Tag Statistics',
      statsTitle: 'Tag Usage Statistics Analysis',
      statsHint: '💡 Analyze this statistical data to find tag usage patterns',
      closeStats: 'Close Statistics'
    }
  };

  // 创建新手友好的控件结构
  $('#controls').innerHTML = `
    <div class="controls">
      <div class="search-section">
        <div class="search-container">
          <input id="search" placeholder="${texts[lang].search}" type="text" />
          <small class="hint">${texts[lang].searchHint}</small>
        </div>
        <div class="action-buttons">

          <button id="clear-filters" class="clear-btn">${texts[lang].clearFilters}</button>
          <button id="tag-stats" class="stats-btn">${texts[lang].tagStats}</button>
          <select id="sort">
            <option value="newest">${texts[lang].newest}</option>
            <option value="oldest">${texts[lang].oldest}</option>
          </select>
        </div>
      </div>
      <div class="results-info">
        <span id="item-count" class="item-count"></span>
      </div>
      <div class="filter-section">
        <div class="filter-group">
          <span class="filter-label">${texts[lang].sources}:</span>
          <div id="sources" class="tags"></div>
        </div>
        <div class="filter-group">
          <span class="filter-label">${texts[lang].tags}:</span>
          <div id="tags" class="tags"></div>
          <small class="hint">${texts[lang].tagHint}</small>
        </div>
      </div>
    </div>
    <div id="stats-modal" class="stats-modal hidden">
      <div class="stats-content">
        <div class="stats-header">
          <h3>${texts[lang].statsTitle}</h3>
          <button id="close-stats" class="close-stats-btn">${texts[lang].closeStats}</button>
        </div>
        <div class="stats-hint">${texts[lang].statsHint}</div>
        <div id="stats-body" class="stats-body"></div>
      </div>
    </div>
  `;

  // 获取元素引用
  searchEl = $('#search');
  sortEl = $('#sort');
}

function bind() {
  // 搜索功能
  if (searchEl) {
    searchEl.addEventListener('input', applyAndRender);
  }

  // 排序功能
  if (sortEl) {
    sortEl.addEventListener('change', applyAndRender);
  }



  // 清除所有筛选
  const clearBtn = $('#clear-filters');
  if (clearBtn) {
    clearBtn.addEventListener('click', clearAllFilters);
  }
  
  // 标签统计
  const statsBtn = $('#tag-stats');
  if (statsBtn) {
    statsBtn.addEventListener('click', showTagStatistics);
  }
  
  const closeStatsBtn = $('#close-stats');
  if (closeStatsBtn) {
    closeStatsBtn.addEventListener('click', hideTagStatistics);
  }

  // 标签点击事件（事件委托）
  const tagsContainer = $('#tags');
  if (tagsContainer) {
    tagsContainer.addEventListener('click', (e) => {
      if (e.target.closest('.tag')) {
        toggleMulti(e, 'tag');
      }
    });
  }

  // 数据源点击事件（事件委托）
  const sourcesContainer = $('#sources');
  if (sourcesContainer) {
    sourcesContainer.addEventListener('click', (e) => {
      if (e.target.closest('.filter-item')) {
        toggleMulti(e, 'source');
      }
    });
  }
}

// 清除所有筛选条件
function clearAllFilters() {
  // 重置搜索框
  if (searchEl) {
    searchEl.value = '';
  }
  
  // 重置排序
  if (sortEl) {
    sortEl.value = 'newest';
  }
  
  // 重置标签筛选
  activeTags.clear();
  activeTags.add('all');
  
  // 重置来源筛选
  activeSource = 'all';
  
  // 重新渲染
  applyAndRender();
}

function toggleMulti(e, type) {
  e.preventDefault();
  const target = e.target.closest('[data-value], [data-tag]');
  if (!target) return;

  const value = target.dataset.value || target.dataset.tag;
  console.log(`Toggle ${type}:`, value);

  if (type === 'tag') {
    if (value === 'all') {
      // 点击"全部"时，清除其他选择
      activeTags.clear();
      activeTags.add('all');
    } else {
      // 点击具体标签时
      if (activeTags.has(value)) {
        // 如果已选中，则取消选择
        activeTags.delete(value);
        // 如果没有选中任何标签，自动选择"全部"
        if (activeTags.size === 0) {
          activeTags.add('all');
        }
      } else {
        // 如果未选中，则添加选择，并移除"全部"
        activeTags.delete('all');
        activeTags.add(value);
      }
    }
  } else if (type === 'source') {
    activeSource = value;
  }

  console.log('Active tags:', Array.from(activeTags));
  console.log('Active source:', activeSource);

  applyAndRender();
}

function applyAndRender() {
  console.log('Applying filters and rendering...');
  
  if (!raw || raw.length === 0) {
    console.log('No data to filter');
    render([]);
    return;
  }

  let filtered = [...raw];
  const lang = window.currentLang || 'zh';
  const tagsField = lang === 'zh' ? 'tags_zh' : 'tags';

  // 应用搜索筛选
  const searchTerm = searchEl?.value?.toLowerCase().trim();
  if (searchTerm) {
    filtered = filtered.filter(item => {
      const title = (item.title || '').toLowerCase();
      const summary = (item.summary || '').toLowerCase();
      return title.includes(searchTerm) || summary.includes(searchTerm);
    });
  }

  // 应用标签筛选
  if (!activeTags.has('all')) {
    filtered = filtered.filter(item => {
      const itemTags = item[tagsField] || item.tags || [];
      return Array.from(activeTags).some(tag => itemTags.includes(tag));
    });
  }

  // 应用来源筛选
  if (activeSource !== 'all') {
    filtered = filtered.filter(item => item.source === activeSource);
  }

  // 应用排序
  const sortValue = sortEl?.value || 'newest';
  if (sortValue === 'oldest') {
    filtered.sort((a, b) => new Date(a.date) - new Date(b.date));
  } else {
    filtered.sort((a, b) => new Date(b.date) - new Date(a.date));
  }

  view = filtered;
  console.log('Filtered results:', view.length, 'items');
  
  render(view);
  updateFilterStatus();
}

// 更新筛选状态显示
function updateFilterStatus() {
  const lang = window.currentLang || 'zh';
  const statusEl = $('#filter-status');
  if (!statusEl) return;

  const totalCount = raw.length;
  const filteredCount = view.length;
  const activeFiltersCount = (activeTags.size > 1 || !activeTags.has('all')) + 
                           (activeSource !== 'all' ? 1 : 0) + 
                           (searchEl?.value?.trim() ? 1 : 0);

  const texts = {
    zh: `显示 ${filteredCount} / ${totalCount} 篇文章${activeFiltersCount > 0 ? ` (${activeFiltersCount} 个筛选条件)` : ''}`,
    en: `Showing ${filteredCount} / ${totalCount} articles${activeFiltersCount > 0 ? ` (${activeFiltersCount} filters)` : ''}`
  };

  statusEl.textContent = texts[lang];
}



function renderSources(list) {
  const sources = [...new Set(list.map(item => item.source))].sort();
  const lang = window.currentLang || 'zh';
  const allText = lang === 'zh' ? '全部来源' : 'All Sources';
  
  const el = $('#sources');
  if (!el) return;
  
  // 计算每个数据源的文章数量
  const sourceCounts = {};
  list.forEach(item => {
    sourceCounts[item.source] = (sourceCounts[item.source] || 0) + 1;
  });
  
  el.innerHTML = `
    <div class="filter-item ${activeSource === 'all' ? 'active' : ''}" data-value="all" onclick="toggleMulti(event, 'source')">
      ${allText} (${list.length})
    </div>
    ${sources.map(source => {
      const count = sourceCounts[source] || 0;
      const statusText = lang === 'zh' ? `${source} - ${count}篇文章` : `${source} - ${count} articles`;
      return `
        <div class="filter-item ${activeSource === source ? 'active' : ''}" data-value="${source}" onclick="toggleMulti(event, 'source')" title="${statusText}">
          ${esc(source)} (${count})
        </div>
      `;
    }).join('')}
  `;
}

// 标签统计功能
function getTagStats(list) {
  const stats = {};
  const lang = window.currentLang || 'zh';
  const tagsField = lang === 'zh' ? 'tags_zh' : 'tags';
  
  // 统计每个标签的使用次数
  list.forEach(item => {
    const itemTags = item[tagsField] || item.tags || [];
    itemTags.forEach(tag => {
      stats[tag] = (stats[tag] || 0) + 1;
    });
  });
  
  return stats;
}

// 渲染标签（优化版）
function renderTags(list) {
  const lang = window.currentLang || 'zh';
  const tagsField = lang === 'zh' ? 'tags_zh' : 'tags';
  const allTags = [...new Set(list.flatMap(item => item[tagsField] || item.tags || []))];
  
  // 统计每个标签的使用次数
  // TODO: 学员任务 - 实现标签统计功能
  // 提示：需要统计每个标签在当前列表中的使用次数
  // 参考格式：const tagCounts = {};
  const tagCounts = {};
  
  // 添加"全部"选项
  const allText = lang === 'zh' ? '全部' : 'All';
  const tags = [allText, ...allTags];
  
  // TODO: 学员任务 - 实现标签数量显示功能
  // 提示：需要在标签后面显示使用次数，格式如 "AI (15)"
  $('#tags').innerHTML = tags.map(t => {
    const isAll = t === allText;
    const tagValue = isAll ? 'all' : t;
    const isActive = activeTags.has(tagValue);
    // TODO: 在这里添加标签数量显示逻辑
    return `<span class="tag ${isActive ? 'active' : ''}" data-tag="${esc(tagValue)}">${esc(t)}</span>`;
  }).join('');
}

// 清除所有标签筛选
function clearAllTags() {
  activeTags.clear();
  activeTags.add('all');
  applyAndRender();
}

// 导出清除函数供全局使用
window.clearAllTags = clearAllTags;

function render(items) {
  console.log('Rendering items:', items.length);
  
  const lang = window.currentLang || 'zh';
  const listEl = $('#list');
  const emptyEl = $('#empty');
  
  if (!listEl || !emptyEl) {
    console.error('Required DOM elements not found');
    return;
  }
  
  // 更新信息数量显示
  updateItemCount(items.length);
  
  if (items.length === 0) {
    listEl.innerHTML = '';
    const emptyTexts = {
      zh: '没有找到匹配的文章，试试调整筛选条件？',
      en: 'No articles found. Try adjusting your filters?'
    };
    emptyEl.innerHTML = `<p>${emptyTexts[lang]}</p>`;
    emptyEl.style.display = 'block';
  } else {
    emptyEl.style.display = 'none';
    listEl.innerHTML = items.map(item => card(item, lang)).join('');
  }
  
  // 渲染筛选器
  renderSources(raw);
  renderTags(raw);
}

function updateItemCount(count) {
  const lang = window.currentLang || 'zh';
  const texts = {
    zh: { totalItems: '共找到 {count} 条信息' },
    en: { totalItems: 'Found {count} items' }
  };
  
  const countEl = $('#item-count');
  if (countEl) {
    countEl.textContent = texts[lang].totalItems.replace('{count}', count);
  }
}

function showWelcomeGuide() {
  const lang = window.currentLang || 'zh';
  
  // 检查是否是首次访问
  const hasVisited = localStorage.getItem('v3_visited');
  if (hasVisited) return;
  
  const welcomeTexts = {
    zh: {
      title: '🎉 欢迎来到第三课：信息筛选与分类管理',
      content: '这里有 {count} 条精选内容等你探索！<br><br>💡 <strong>快速上手指南：</strong><br>• 使用搜索框快速查找内容<br>• 点击标签进行筛选（可多选）<br>• 试试随机推荐发现新内容<br>• 完成任务文档中的4个学习任务',
      button: '开始探索',
      taskLink: '查看学习任务'
    },
    en: {
      title: '🎉 Welcome to Lesson 3: Information Filtering & Classification',
      content: 'There are {count} curated items waiting for you to explore!<br><br>💡 <strong>Quick Start Guide:</strong><br>• Use search box to find content quickly<br>• Click tags to filter (multiple selection)<br>• Try random recommendation to discover new content<br>• Complete 4 learning tasks in the task document',
      button: 'Start Exploring',
      taskLink: 'View Learning Tasks'
    }
  };
  
  const totalCount = raw.length;
  const content = welcomeTexts[lang].content.replace('{count}', totalCount);
  
  // 创建欢迎弹窗
  const modal = document.createElement('div');
  modal.className = 'welcome-modal';
  modal.innerHTML = `
    <div class="welcome-content">
      <h3>${welcomeTexts[lang].title}</h3>
      <div class="welcome-body">${content}</div>
      <div class="welcome-actions">
        <a href="task.md" target="_blank" class="task-link">${welcomeTexts[lang].taskLink}</a>
        <button class="welcome-btn" onclick="closeWelcomeGuide()">${welcomeTexts[lang].button}</button>
      </div>
    </div>
  `;
  
  document.body.appendChild(modal);
  
  // 标记已访问
  localStorage.setItem('v3_visited', 'true');
}

function closeWelcomeGuide() {
  const modal = document.querySelector('.welcome-modal');
  if (modal) {
    modal.remove();
  }
}

// 全局函数，供HTML调用
window.closeWelcomeGuide = closeWelcomeGuide;

function showTagStatistics() {
  const lang = window.currentLang || 'zh';
  const statsModal = $('#stats-modal');
  const statsBody = $('#stats-body');
  
  if (!statsModal || !statsBody) return;
  
  // 统计所有标签
  const tagStats = {};
  const tagCombinations = {};
  let totalItems = 0;
  
  raw.forEach(item => {
    // 根据当前语言选择正确的标签字段
    const tagsField = lang === 'zh' ? 'tags_zh' : 'tags';
    const itemTags = item[tagsField];
    
    if (itemTags && Array.isArray(itemTags)) {
      totalItems++;
      
      // 统计单个标签
      itemTags.forEach(tag => {
        tagStats[tag] = (tagStats[tag] || 0) + 1;
      });
      
      // 统计标签组合（2个标签的组合）
      for (let i = 0; i < itemTags.length; i++) {
        for (let j = i + 1; j < itemTags.length; j++) {
          const combo = [itemTags[i], itemTags[j]].sort().join(' + ');
          tagCombinations[combo] = (tagCombinations[combo] || 0) + 1;
        }
      }
    }
  });
  
  // 排序标签（按使用频率）
  const sortedTags = Object.entries(tagStats)
    .sort(([,a], [,b]) => b - a)
    .map(([tag, count]) => ({ tag, count, percentage: ((count / totalItems) * 100).toFixed(1) }));
  
  // 排序标签组合
  const sortedCombos = Object.entries(tagCombinations)
    .sort(([,a], [,b]) => b - a)
    .slice(0, 10) // 只显示前10个组合
    .map(([combo, count]) => ({ combo, count, percentage: ((count / totalItems) * 100).toFixed(1) }));
  
  const texts = {
    zh: {
      totalTags: '标签总数',
      totalItems: '内容总数',
      avgTagsPerItem: '平均每条内容的标签数',
      topTags: '使用频率最高的标签',
      topCombos: '常见标签组合',
      tag: '标签',
      count: '使用次数',
      percentage: '占比',
      combination: '标签组合'
    },
    en: {
      totalTags: 'Total Tags',
      totalItems: 'Total Items',
      avgTagsPerItem: 'Average Tags per Item',
      topTags: 'Most Frequently Used Tags',
      topCombos: 'Common Tag Combinations',
      tag: 'Tag',
      count: 'Count',
      percentage: 'Percentage',
      combination: 'Tag Combination'
    }
  };
  
  const totalTags = Object.keys(tagStats).length;
  const avgTags = (Object.values(tagStats).reduce((a, b) => a + b, 0) / totalItems).toFixed(1);
  
  statsBody.innerHTML = `
    <div class="stats-overview">
      <div class="stat-item">
        <span class="stat-label">${texts[lang].totalTags}:</span>
        <span class="stat-value">${totalTags}</span>
      </div>
      <div class="stat-item">
        <span class="stat-label">${texts[lang].totalItems}:</span>
        <span class="stat-value">${totalItems}</span>
      </div>
      <div class="stat-item">
        <span class="stat-label">${texts[lang].avgTagsPerItem}:</span>
        <span class="stat-value">${avgTags}</span>
      </div>
    </div>
    
    <div class="stats-section">
      <h4>${texts[lang].topTags}</h4>
      <div class="stats-table">
        <div class="stats-header-row">
          <span>${texts[lang].tag}</span>
          <span>${texts[lang].count}</span>
          <span>${texts[lang].percentage}</span>
        </div>
        ${sortedTags.map(item => `
          <div class="stats-row">
            <span class="tag-name">${item.tag}</span>
            <span class="tag-count">${item.count}</span>
            <span class="tag-percentage">${item.percentage}%</span>
          </div>
        `).join('')}
      </div>
    </div>
    
    ${sortedCombos.length > 0 ? `
      <div class="stats-section">
        <h4>${texts[lang].topCombos}</h4>
        <div class="stats-table">
          <div class="stats-header-row">
            <span>${texts[lang].combination}</span>
            <span>${texts[lang].count}</span>
            <span>${texts[lang].percentage}</span>
          </div>
          ${sortedCombos.map(item => `
            <div class="stats-row">
              <span class="combo-name">${item.combo}</span>
              <span class="combo-count">${item.count}</span>
              <span class="combo-percentage">${item.percentage}%</span>
            </div>
          `).join('')}
        </div>
      </div>
    ` : ''}
  `;
  
  statsModal.classList.remove('hidden');
}

function hideTagStatistics() {
  const statsModal = $('#stats-modal');
  if (statsModal) {
    statsModal.classList.add('hidden');
  }
}

function renderWithLanguage(items, lang) {
  window.currentLang = lang;
  mountControls(); // 重新挂载控件以更新语言
  render(items);
}

function card(item, lang = 'zh') {
  const tagsArray = lang === 'zh' ? (item.tags_zh || item.tags || []) : (item.tags || []);
  const tags = tagsArray.join(' ');
  const title = lang === 'zh' ? (item.title_zh || item.title) : item.title;
  const summaryField = lang === 'zh' ? 'summary_zh' : 'summary_en';
  const quoteField = lang === 'zh' ? 'best_quote_zh' : 'best_quote_en';
  const desc = item[summaryField] || '';
  const quote = item[quoteField] || '';
  const quoteSymbols = lang === 'zh' ? ['「', '」'] : ['"', '"'];
  const aiSummaryLabel = lang === 'zh' ? 'AI总结：' : 'AI Summary: ';
  
  return `
    <article class="card" data-id="${item.id}">
      <h3><a href="${item.link}" target="_blank" rel="noopener">${esc(title)}</a></h3>
      ${desc ? `<p><span class="ai-label">${aiSummaryLabel}</span>${esc(desc)}</p>` : ''}
      ${quote ? `<blockquote>${quoteSymbols[0]}${esc(quote)}${quoteSymbols[1]}</blockquote>` : ''}
      <div class="meta">
        <span class="source">${esc(item.source)}</span>
        <span class="card-tags">${esc(tags)}</span>
        <span class="date">${esc(item.date || '')}</span>
      </div>
    </article>
  `;
}

function esc(s) {
  if (typeof s !== 'string') return '';
  return s.replace(/[&<>"']/g, m => ({
    '&': '&amp;',
    '<': '&lt;',
    '>': '&gt;',
    '"': '&quot;',
    "'": '&#39;'
  })[m]);
}
