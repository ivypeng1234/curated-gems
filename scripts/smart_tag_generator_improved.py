#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
智能标签生成器 - 基于内容价值和用户发现性的新一代标签系统

核心理念：标签不是为了分类内容，而是为了帮助用户发现价值
"""

import re
import json
import os
from typing import List, Dict, Tuple, Optional
from dataclasses import dataclass
from urllib.parse import urlparse

@dataclass
class TagResult:
    """标签生成结果"""
    tags: List[str]
    tags_zh: List[str]
    weights: List[float]
    confidence: float
    reasoning: str

class SmartTagGenerator:
    """智能标签生成器"""
    
    def __init__(self, scripts_dir: str = "scripts"):
        self.scripts_dir = scripts_dir
        self.value_types = self._init_value_types()
        self.domain_themes = self._init_domain_themes()
        self.feature_tags = self._init_feature_tags()
        self.domain_patterns = self._init_domain_patterns()
        
    def _init_value_types(self) -> Dict[str, Dict]:
        """初始化价值类型标签（第一层）"""
        return {
            'learn': {
                'zh': '学习',
                'indicators': [
                    'concept', 'understand', 'explain', 'introduction', 'basics',
                    'what is', 'how does', 'fundamentals', 'overview', 'guide to',
                    '概念', '理解', '解释', '介绍', '基础', '入门', '什么是'
                ],
                'weight': 1.0
            },
            'solve': {
                'zh': '解决',
                'indicators': [
                    'how to', 'solution', 'fix', 'problem', 'troubleshoot',
                    'resolve', 'debug', 'error', 'issue', 'workaround',
                    '如何', '解决方案', '修复', '问题', '故障排除', '调试'
                ],
                'weight': 1.0
            },
            'inspire': {
                'zh': '启发',
                'indicators': [
                    'vision', 'future', 'philosophy', 'mindset', 'perspective',
                    'thoughts on', 'reflection', 'opinion', 'essay', 'manifesto',
                    '愿景', '未来', '哲学', '思维', '观点', '思考', '反思', '随想'
                ],
                'weight': 1.0
            },
            'update': {
                'zh': '动态',
                'indicators': [
                    'news', 'announcement', 'release', 'latest', 'breaking',
                    'update', 'launched', 'introduces', 'unveils', 'reports',
                    '新闻', '公告', '发布', '最新', '更新', '推出', '报告'
                ],
                'weight': 1.0
            },
            'analyze': {
                'zh': '分析',
                'indicators': [
                    'analysis', 'research', 'study', 'investigation', 'deep dive',
                    'examination', 'review', 'survey', 'report', 'findings',
                    '分析', '研究', '调查', '深入', '审查', '报告', '发现'
                ],
                'weight': 1.0
            },
            'guide': {
                'zh': '指导',
                'indicators': [
                    'tutorial', 'guide', 'step by step', 'practice', 'implementation',
                    'walkthrough', 'hands-on', 'example', 'demo', 'workshop',
                    '教程', '指南', '步骤', '实践', '实现', '演示', '示例'
                ],
                'weight': 1.0
            }
        }
    
    def _init_domain_themes(self) -> Dict[str, Dict]:
        """初始化领域主题标签（第二层）- 通用化设计，适应不同内容源"""
        return {
            # === 科技类 ===
            'ai-research': {
                'zh': 'AI研究',
                'keywords': [
                    'artificial intelligence', 'machine learning', 'deep learning',
                    'neural network', 'transformer', 'llm', 'gpt', 'research',
                    'paper', 'arxiv', 'model', 'algorithm', 'training',
                    '人工智能', '机器学习', '深度学习', '神经网络', '研究', '论文', '模型'
                ],
                'domains': ['arxiv.org', 'openai.com', 'deepmind.com', 'anthropic.com']
            },
            'ai-product': {
                'zh': 'AI产品',
                'keywords': [
                    'chatgpt', 'claude', 'gemini', 'copilot', 'ai tool',
                    'ai application', 'ai service', 'ai platform', 'automation',
                    'ai assistant', 'ai feature', 'integration',
                    'AI工具', 'AI应用', 'AI服务', 'AI平台', '自动化', 'AI助手'
                ],
                'domains': ['openai.com', 'anthropic.com', 'google.com']
            },
            'programming': {
                'zh': '编程开发',
                'keywords': [
                    'programming', 'coding', 'development', 'software',
                    'framework', 'library', 'api', 'architecture', 'design pattern',
                    'best practice', 'code quality', 'testing', 'debugging',
                    '编程', '开发', '软件', '框架', '架构', '设计模式', '最佳实践', '调试'
                ],
                'domains': ['github.com', 'stackoverflow.com', 'dev.to']
            },
            'tech-trends': {
                'zh': '技术趋势',
                'keywords': [
                    'technology', 'tech trend', 'innovation', 'emerging',
                    'future tech', 'digital transformation', 'disruption',
                    'breakthrough', 'advancement', 'evolution', 'blockchain', 'web3',
                    '技术', '技术趋势', '创新', '新兴', '数字化转型', '突破', '区块链'
                ],
                'domains': ['wired.com', 'arstechnica.com', 'techcrunch.com']
            },
            'cybersecurity': {
                'zh': '网络安全',
                'keywords': [
                    'security', 'cybersecurity', 'privacy', 'encryption', 'vulnerability',
                    'hack', 'breach', 'protection', 'authentication', 'firewall',
                    '安全', '网络安全', '隐私', '加密', '漏洞', '黑客', '防护'
                ],
                'domains': ['krebsonsecurity.com', 'schneier.com']
            },
            'data-science': {
                'zh': '数据科学',
                'keywords': [
                    'data science', 'data analysis', 'big data', 'analytics',
                    'machine learning', 'statistics', 'data mining', 'visualization',
                    'database', 'sql', 'python', 'r', 'tableau', 'pandas',
                    '数据科学', '数据分析', '大数据', '统计', '数据挖掘', '可视化', '数据库'
                ],
                'domains': ['kaggle.com', 'towardsdatascience.com']
            },
            'gaming': {
                'zh': '游戏开发',
                'keywords': [
                    'game', 'gaming', 'game development', 'game design', 'unity',
                    'unreal engine', 'indie game', 'mobile game', 'esports',
                    'game industry', 'gamedev', 'game engine', 'graphics',
                    '游戏', '游戏开发', '游戏设计', '独立游戏', '手机游戏', '电竞', '游戏引擎'
                ],
                'domains': ['gamasutra.com', 'gamedev.net', 'itch.io']
            },
            
            # === 商业类 ===
            'startup-strategy': {
                'zh': '创业策略',
                'keywords': [
                    'startup', 'entrepreneur', 'business strategy', 'growth',
                    'scaling', 'product market fit', 'go to market', 'strategy',
                    'business model', 'competition', 'market',
                    '创业', '企业家', '商业策略', '增长', '扩展', '市场'
                ],
                'domains': ['paulgraham.com', 'a16z.com', 'firstround.com']
            },
            'startup-funding': {
                'zh': '创业融资',
                'keywords': [
                    'funding', 'investment', 'venture capital', 'vc', 'seed',
                    'series a', 'series b', 'ipo', 'valuation', 'investor',
                    'pitch', 'fundraising', 'equity',
                    '融资', '投资', '风险投资', '估值', '投资者', '股权'
                ],
                'domains': ['techcrunch.com', 'crunchbase.com']
            },
            'business-model': {
                'zh': '商业模式',
                'keywords': [
                    'business model', 'revenue', 'monetization', 'pricing',
                    'subscription', 'saas', 'marketplace', 'platform',
                    'economics', 'profit', 'cost structure', 'freemium',
                    '商业模式', '收入', '盈利', '定价', '订阅', '平台', '经济'
                ],
                'domains': ['stratechery.com', 'hbr.org']
            },
            'leadership': {
                'zh': '领导管理',
                'keywords': [
                    'leadership', 'management', 'team', 'culture', 'hiring',
                    'organization', 'ceo', 'founder', 'decision making',
                    'communication', 'motivation', 'performance', 'remote work',
                    '领导力', '管理', '团队', '文化', '招聘', '组织', '决策', '沟通', '远程工作'
                ],
                'domains': ['firstround.com', 'hbr.org']
            },
            'marketing': {
                'zh': '市场营销',
                'keywords': [
                    'marketing', 'branding', 'advertising', 'content marketing',
                    'social media', 'seo', 'growth hacking', 'customer acquisition',
                    'conversion', 'analytics', 'campaign',
                    '营销', '品牌', '广告', '内容营销', '社交媒体', '增长黑客', '客户获取'
                ],
                'domains': ['marketingland.com', 'contentmarketinginstitute.com']
            },
            'product-management': {
                'zh': '产品管理',
                'keywords': [
                    'product management', 'product manager', 'product strategy',
                    'user research', 'product roadmap', 'feature', 'user story',
                    'agile', 'scrum', 'mvp', 'product launch', 'metrics',
                    '产品管理', '产品经理', '产品策略', '用户研究', '产品路线图', '敏捷', '最小可行产品'
                ],
                'domains': ['productplan.com', 'mindtheproduct.com']
            },
            
            # === 学术研究类 ===
            'science': {
                'zh': '科学研究',
                'keywords': [
                    'science', 'research', 'study', 'experiment', 'discovery',
                    'breakthrough', 'publication', 'peer review', 'hypothesis',
                    'data', 'methodology', 'findings',
                    '科学', '研究', '实验', '发现', '突破', '数据', '方法论', '发现'
                ],
                'domains': ['nature.com', 'science.org', 'pnas.org']
            },
            'medicine': {
                'zh': '医学健康',
                'keywords': [
                    'medicine', 'health', 'medical', 'healthcare', 'treatment',
                    'therapy', 'drug', 'clinical trial', 'diagnosis', 'patient',
                    'disease', 'prevention', 'wellness',
                    '医学', '健康', '医疗', '治疗', '药物', '临床', '诊断', '疾病', '预防'
                ],
                'domains': ['nejm.org', 'thelancet.com', 'bmj.com']
            },
            'psychology': {
                'zh': '心理学',
                'keywords': [
                    'psychology', 'mental health', 'behavior', 'cognitive',
                    'emotion', 'therapy', 'mindfulness', 'stress', 'anxiety',
                    'depression', 'wellbeing', 'neuroscience',
                    '心理学', '心理健康', '行为', '认知', '情绪', '治疗', '正念', '压力'
                ],
                'domains': ['psychologytoday.com', 'apa.org']
            },
            'environment': {
                'zh': '环境科学',
                'keywords': [
                    'environment', 'climate change', 'sustainability', 'renewable energy',
                    'carbon', 'greenhouse gas', 'global warming', 'ecology',
                    'conservation', 'green technology', 'clean energy', 'pollution',
                    '环境', '气候变化', '可持续发展', '可再生能源', '碳排放', '生态', '环保技术'
                ],
                'domains': ['nature.com', 'ipcc.ch', 'epa.gov']
            },
            
            # === 社会文化类 ===
            'politics': {
                'zh': '政治时事',
                'keywords': [
                    'politics', 'government', 'policy', 'election', 'democracy',
                    'legislation', 'congress', 'senate', 'president', 'vote',
                    'campaign', 'political', 'public policy',
                    '政治', '政府', '政策', '选举', '民主', '立法', '投票', '竞选'
                ],
                'domains': ['politico.com', 'washingtonpost.com', 'nytimes.com']
            },
            'economics': {
                'zh': '经济金融',
                'keywords': [
                    'economics', 'economy', 'finance', 'market', 'stock',
                    'investment', 'banking', 'cryptocurrency', 'inflation',
                    'recession', 'gdp', 'trade', 'monetary policy',
                    '经济', '金融', '市场', '股票', '投资', '银行', '加密货币', '通胀'
                ],
                'domains': ['economist.com', 'ft.com', 'wsj.com', 'bloomberg.com']
            },
            'society': {
                'zh': '社会议题',
                'keywords': [
                    'society', 'social', 'community', 'culture', 'diversity',
                    'equality', 'justice', 'human rights', 'education',
                    'environment', 'climate change', 'sustainability',
                    '社会', '社区', '文化', '多样性', '平等', '正义', '人权', '教育', '环境'
                ],
                'domains': ['npr.org', 'bbc.com', 'theguardian.com']
            },
            'legal': {
                'zh': '法律法规',
                'keywords': [
                    'law', 'legal', 'regulation', 'legislation', 'court',
                    'judge', 'lawyer', 'attorney', 'lawsuit', 'compliance',
                    'contract', 'intellectual property', 'patent', 'copyright',
                    '法律', '法规', '立法', '法院', '法官', '律师', '诉讼', '合规', '知识产权'
                ],
                'domains': ['law.com', 'justia.com', 'findlaw.com']
            },
            
            # === 生活方式类 ===
            'lifestyle': {
                'zh': '生活方式',
                'keywords': [
                    'lifestyle', 'life', 'personal', 'habit', 'routine',
                    'productivity', 'time management', 'work life balance',
                    'self improvement', 'minimalism', 'travel', 'food',
                    '生活方式', '个人', '习惯', '日常', '生产力', '时间管理', '自我提升'
                ],
                'domains': ['medium.com', 'lifehacker.com']
            },
            'education': {
                'zh': '教育学习',
                'keywords': [
                    'education', 'learning', 'teaching', 'school', 'university',
                    'course', 'curriculum', 'student', 'teacher', 'online learning',
                    'skill development', 'training', 'knowledge',
                    '教育', '学习', '教学', '学校', '大学', '课程', '学生', '老师', '技能'
                ],
                'domains': ['edutopia.org', 'khanacademy.org']
            },
            'health-wellness': {
                'zh': '健康养生',
                'keywords': [
                    'health', 'wellness', 'fitness', 'nutrition', 'diet',
                    'exercise', 'workout', 'mental health', 'meditation',
                    'sleep', 'stress management', 'healthy lifestyle', 'yoga',
                    '健康', '养生', '健身', '营养', '饮食', '锻炼', '冥想', '睡眠', '瑜伽'
                ],
                'domains': ['healthline.com', 'webmd.com', 'mayoclinic.org']
            },
            'personal-finance': {
                'zh': '个人理财',
                'keywords': [
                    'personal finance', 'money', 'budget', 'saving', 'investment',
                    'retirement', 'insurance', 'debt', 'credit', 'financial planning',
                    'wealth', 'passive income', 'financial independence',
                    '个人理财', '金钱', '预算', '储蓄', '投资', '退休', '保险', '债务', '财务规划'
                ],
                'domains': ['mint.com', 'nerdwallet.com', 'investopedia.com']
            },
            
            # === 创意设计类 ===
            'design': {
                'zh': '设计创意',
                'keywords': [
                    'design', 'ui', 'ux', 'user experience', 'interface',
                    'graphic design', 'web design', 'product design',
                    'creative', 'art', 'visual', 'typography', 'color',
                    '设计', '用户体验', '界面', '图形设计', '网页设计', '创意', '艺术'
                ],
                'domains': ['dribbble.com', 'behance.net', 'designbetter.co']
            },
            'music-arts': {
                'zh': '音乐艺术',
                'keywords': [
                    'music', 'art', 'artist', 'musician', 'painting', 'sculpture',
                    'photography', 'film', 'cinema', 'theater', 'performance',
                    'creative process', 'inspiration', 'gallery', 'exhibition',
                    '音乐', '艺术', '艺术家', '音乐家', '绘画', '雕塑', '摄影', '电影', '戏剧'
                ],
                'domains': ['artsy.net', 'spotify.com', 'soundcloud.com']
            },
            'writing-content': {
                'zh': '写作内容',
                'keywords': [
                    'writing', 'content', 'blog', 'journalism', 'storytelling',
                    'copywriting', 'creative writing', 'author', 'book', 'novel',
                    'poetry', 'publishing', 'editing', 'narrative',
                    '写作', '内容', '博客', '新闻', '故事', '文案', '创意写作', '作者', '小说', '诗歌'
                ],
                'domains': ['medium.com', 'substack.com', 'goodreads.com']
            }
        }
    
    def _init_feature_tags(self) -> Dict[str, Dict]:
        """初始化特征标签（第三层）"""
        return {
            'beginner-friendly': {
                'zh': '新手友好',
                'indicators': [
                    'beginner', 'introduction', 'basics', 'getting started',
                    'simple', 'easy', 'step by step', 'for beginners',
                    '初学者', '入门', '基础', '简单', '容易', '新手'
                ]
            },
            'deep-dive': {
                'zh': '深度分析',
                'indicators': [
                    'deep dive', 'comprehensive', 'detailed', 'in-depth',
                    'thorough', 'extensive', 'complete guide', 'advanced',
                    '深入', '全面', '详细', '深度', '高级', '完整'
                ]
            },
            'controversial': {
                'zh': '争议观点',
                'indicators': [
                    'controversial', 'debate', 'opinion', 'criticism',
                    'against', 'why not', 'problem with', 'unpopular',
                    '争议', '辩论', '批评', '反对', '问题', '不受欢迎'
                ]
            },
            'data-driven': {
                'zh': '数据驱动',
                'indicators': [
                    'data', 'statistics', 'metrics', 'analysis', 'research',
                    'study', 'survey', 'numbers', 'evidence', 'findings',
                    '数据', '统计', '指标', '研究', '调查', '证据', '发现'
                ]
            },
            'case-study': {
                'zh': '案例研究',
                'indicators': [
                    'case study', 'example', 'real world', 'story', 'experience',
                    'lessons learned', 'what we learned', 'behind the scenes',
                    '案例', '例子', '真实', '故事', '经验', '教训', '幕后'
                ]
            },
            'future-prediction': {
                'zh': '未来预测',
                'indicators': [
                    'future', 'prediction', 'forecast', 'trend', 'what\'s next',
                    'coming', 'will be', 'expect', 'outlook', 'vision',
                    '未来', '预测', '趋势', '展望', '愿景', '即将', '期待'
                ]
            }
        }
    
    def _init_domain_patterns(self) -> Dict[str, List[str]]:
        """初始化域名模式映射"""
        return {
            'paulgraham.com': ['startup-strategy', 'inspire'],
            'stratechery.com': ['business-model', 'analyze'],
            'arxiv.org': ['ai-research', 'learn'],
            'openai.com': ['ai-research', 'ai-product'],
            'anthropic.com': ['ai-research', 'ai-product'],
            'techcrunch.com': ['startup-funding', 'update'],
            'wired.com': ['tech-trends', 'inspire'],
            'arstechnica.com': ['tech-trends', 'analyze'],
            'github.com': ['programming-practice', 'guide'],
            'firstround.com': ['startup-strategy', 'leadership']
        }
    
    def generate_tags(self, title: str, summary_en: str, summary_zh: str, 
                     url: str, source: str = "") -> TagResult:
        """生成智能标签"""
        try:
            # 合并所有文本内容用于分析
            content = f"{title} {summary_en} {summary_zh}".lower()
            
            # 1. 识别价值类型（第一层，必选1个）
            value_tag = self._identify_value_type(title, summary_en, summary_zh)
            
            # 2. 识别领域主题（第二层，1-2个）
            domain_tags = self._identify_domain_themes(content, url, source)
            
            # 3. 识别特征标签（第三层，0-1个）
            feature_tag = self._identify_feature_tag(content)
            
            # 4. 组合最终标签
            final_tags = [value_tag] + domain_tags
            if feature_tag:
                final_tags.append(feature_tag)
            # 防御性限制：当前标签体系最多 4 个标签，保证中英文一一对应。
            final_tags = final_tags[:4]
            
            # 5. 生成中文标签
            final_tags_zh = self._generate_chinese_tags(final_tags)
            
            # 6. 计算权重
            weights = self._calculate_weights(final_tags, content)
            
            # 7. 计算置信度
            confidence = self._calculate_confidence(final_tags, content, url)
            
            # 8. 生成推理说明
            reasoning = self._generate_reasoning(final_tags, value_tag, domain_tags, feature_tag)
            
            print(f"[SmartTagGenerator] Generated {len(final_tags)} tags: {final_tags}")
            print(f"[SmartTagGenerator] Confidence: {confidence:.2f}, Reasoning: {reasoning}")
            
            return TagResult(
                tags=final_tags,
                tags_zh=final_tags_zh,
                weights=weights,
                confidence=confidence,
                reasoning=reasoning
            )
            
        except Exception as e:
            print(f"[SmartTagGenerator] Error generating tags: {e}")
            # 返回默认标签
            return TagResult(
                tags=['update', 'general'],
                tags_zh=['动态', '综合'],
                weights=[1.0, 0.5],
                confidence=0.3,
                reasoning="Error occurred, using fallback tags"
            )
    
    def _identify_value_type(self, title: str, summary_en: str, summary_zh: str) -> str:
        """识别内容价值类型"""
        content = f"{title} {summary_en} {summary_zh}".lower()
        
        scores = {}
        for value_type, config in self.value_types.items():
            score = 0
            for indicator in config['indicators']:
                # 标题中的指标权重更高
                if indicator.lower() in title.lower():
                    score += 3
                elif indicator.lower() in content:
                    score += 1
            scores[value_type] = score
        
        # 返回得分最高的价值类型
        best_type = max(scores.items(), key=lambda x: x[1])
        return best_type[0] if best_type[1] > 0 else 'update'  # 默认为update
    
    def _identify_domain_themes(self, content: str, url: str, source: str) -> List[str]:
        """识别领域主题（1-2个），使用更严格的相关性门槛，降低关键词漂移。"""
        scores = {}

        domain = urlparse(url).netloc.lower()
        if domain.startswith('www.'):
            domain = domain[4:]

        domain_matched = set()
        if domain in self.domain_patterns:
            for theme in self.domain_patterns[domain]:
                if theme in self.domain_themes:
                    scores[theme] = scores.get(theme, 0) + 5
                    domain_matched.add(theme)

        for theme, config in self.domain_themes.items():
            score = scores.get(theme, 0)
            for keyword in config['keywords']:
                kw = keyword.lower()
                if kw in content:
                    # 长词/短语更有辨识度，避免泛词一票命中。
                    score += 2 if (len(kw) >= 12 or ' ' in kw or '-' in kw) else 1
            scores[theme] = score

        ranked = sorted(scores.items(), key=lambda x: x[1], reverse=True)
        if not ranked or ranked[0][1] <= 0:
            return ['general']

        primary, primary_score = ranked[0]
        if not self._domain_has_sufficient_evidence(primary, content, domain, primary_score):
            return ['general']

        result = [primary]

        # 第二领域必须同时满足绝对分数和相对分数门槛。
        for theme, score in ranked[1:]:
            if score < 3:
                continue
            if score < primary_score * 0.75:
                continue
            if not self._domain_has_sufficient_evidence(theme, content, domain, score):
                continue
            result.append(theme)
            break

        return result[:2]

    def _domain_has_sufficient_evidence(self, theme: str, content: str,
                                        domain: str, score: int) -> bool:
        """判断领域是否有足够的专属证据，而不是仅碰巧命中泛词。"""
        config = self.domain_themes.get(theme, {})
        keywords = [k.lower() for k in config.get('keywords', [])]
        matched = {k for k in keywords if k in content}

        # 官方/专门域名映射是强证据，但仍要求至少命中一个关键词。
        if domain in config.get('domains', []):
            return bool(matched)

        if theme == 'ai-research':
            ai_core = [
                'artificial intelligence', 'machine learning', 'deep learning',
                'neural network', 'transformer', 'llm', 'gpt',
                '人工智能', '机器学习', '深度学习', '神经网络'
            ]
            research_core = [
                'research', 'paper', 'arxiv', 'model', 'algorithm',
                'training', 'experiment', 'benchmark', '研究', '论文', '模型'
            ]
            return (any(k in content for k in ai_core) and
                    any(k in content for k in research_core))

        if theme == 'ai-product':
            ai_product = [
                'chatgpt', 'claude', 'gemini', 'copilot', 'ai tool',
                'ai application', 'ai service', 'ai platform',
                'ai assistant', 'ai feature', '人工智能', 'ai工具', 'ai应用'
            ]
            return any(k in content for k in ai_product)

        if theme == 'data-science':
            strong = [
                'data science', 'data analysis', 'big data', 'analytics',
                'machine learning', 'statistics', 'data mining',
                'database', 'sql', 'python', 'pandas', '数据科学', '数据分析'
            ]
            return sum(k in content for k in strong) >= 2

        if theme == 'science':
            strong = [
                'experiment', 'discovery', 'publication', 'peer review',
                'hypothesis', 'methodology', 'scientific', '实验',
                '发现', '论文', '同行评审', '假设', '方法论'
            ]
            return sum(k in content for k in strong) >= 1 and score >= 3

        long_match = any(len(k) >= 12 or ' ' in k for k in matched)
        return len(matched) >= 2 or long_match

    def _identify_feature_tag(self, content: str) -> Optional[str]:
        """识别特征标签（0-1个），避免通用词触发误判。"""
        scores = {}

        for feature, config in self.feature_tags.items():
            matched = [i.lower() for i in config['indicators'] if i.lower() in content]
            if matched:
                scores[feature] = len(matched)

        if not scores:
            return None

        # data-driven 需要更强证据，analysis/research/study 等泛词不能单独触发。
        if 'data-driven' in scores:
            data_strong = [
                'statistics', 'metrics', 'survey', 'numbers', 'dataset',
                'quantitative', 'statistical', 'data analysis',
                '数据', '统计', '指标', '调查', '数据分析'
            ]
            if sum(k in content for k in data_strong) < 2:
                scores.pop('data-driven', None)

        if not scores:
            return None

        best_feature, best_score = max(scores.items(), key=lambda x: x[1])
        threshold = 3 if best_feature == 'data-driven' else 2
        return best_feature if best_score >= threshold else None

    def _generate_chinese_tags(self, tags: List[str]) -> List[str]:
        """生成对应的中文标签"""
        zh_tags = []
        
        for tag in tags:
            if tag in self.value_types:
                zh_tags.append(self.value_types[tag]['zh'])
            elif tag in self.domain_themes:
                zh_tags.append(self.domain_themes[tag]['zh'])
            elif tag in self.feature_tags:
                zh_tags.append(self.feature_tags[tag]['zh'])
            else:
                zh_tags.append(tag)  # 如果没有中文对应，使用英文
        
        return zh_tags
    
    def _calculate_weights(self, tags: List[str], content: str) -> List[float]:
        """计算标签权重"""
        weights = []
        
        for i, tag in enumerate(tags):
            if i == 0:  # 价值类型标签权重最高
                weights.append(1.0)
            elif i <= 2:  # 领域主题标签
                weights.append(0.8 if i == 1 else 0.6)
            else:  # 特征标签
                weights.append(0.4)
        
        return weights
    
    def _calculate_confidence(self, tags: List[str], content: str, url: str) -> float:
        """计算标签生成的置信度"""
        confidence = 0.5  # 基础置信度
        
        # 域名匹配增加置信度
        domain = urlparse(url).netloc.lower()
        if domain.startswith('www.'):
            domain = domain[4:]
        
        if domain in self.domain_patterns:
            confidence += 0.2
        
        # 标签数量合理增加置信度
        if 2 <= len(tags) <= 4:
            confidence += 0.1
        elif len(tags) > 4:
            confidence -= 0.1
        
        # 内容长度足够增加置信度
        if len(content) > 500:
            confidence += 0.1
        
        return min(confidence, 1.0)
    
    def _generate_reasoning(self, final_tags: List[str], value_tag: str, 
                          domain_tags: List[str], feature_tag: Optional[str]) -> str:
        """生成标签推理说明"""
        reasoning_parts = []
        
        reasoning_parts.append(f"价值类型: {value_tag}")
        reasoning_parts.append(f"领域主题: {', '.join(domain_tags)}")
        
        if feature_tag:
            reasoning_parts.append(f"特征: {feature_tag}")
        
        return " | ".join(reasoning_parts)

# 使用示例
if __name__ == "__main__":
    generator = SmartTagGenerator()
    
    # 测试标签生成
    result = generator.generate_tags(
        title="The Gentle Singularity",
        summary_en="This article explores the accelerating march towards artificial superintelligence...",
        summary_zh="这篇文章对人工智能的飞速发展描绘出了一幅既宏伟又细腻的画卷...",
        url="https://blog.samaltman.com/the-gentle-singularity",
        source="Sam Altman"
    )
    
    print(f"Tags: {result.tags}")
    print(f"Tags ZH: {result.tags_zh}")
    print(f"Weights: {result.weights}")
    print(f"Confidence: {result.confidence}")
    print(f"Reasoning: {result.reasoning}")