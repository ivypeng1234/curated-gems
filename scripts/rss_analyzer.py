import os
import json
import time
import requests
import feedparser
from datetime import datetime
from bs4 import BeautifulSoup
import re
import json
from tag_optimizer import TagOptimizer

# Load .env file for local development
try:
    from dotenv import load_dotenv
    load_dotenv()  # Load .env file if it exists
except ImportError:
    # python-dotenv not installed, skip .env loading
    # This is fine for GitHub Actions which uses environment variables directly
    pass

# ========== Basic Configuration ==========
OPENROUTER_API_KEY = os.getenv("OPENROUTER_API_KEY")
if not OPENROUTER_API_KEY:
    print("WARNING: OPENROUTER_API_KEY not found in environment variables. Script will exit gracefully.")
    print("For local development: Create a .env file with OPENROUTER_API_KEY=your_key")
    print("For GitHub Actions: Set OPENROUTER_API_KEY in repository secrets")
    print("No new valid records this time, no write needed.")
    print("\nAll processes completed: Successfully added 0 items; Model called 0 times.")
    exit(0)  # Exit gracefully instead of raising error

# Validate API key format
if OPENROUTER_API_KEY and not OPENROUTER_API_KEY.startswith('sk-or-v1-'):
    print("WARNING: OPENROUTER_API_KEY format appears incorrect. Should start with 'sk-or-v1-'")
    print("Please check your API key at https://openrouter.ai/keys")
    print("No new valid records this time, no write needed.")
    print("\nAll processes completed: Successfully added 0 items; Model called 0 times.")
    exit(0)

# Model name fallback (don't use || concatenation in YAML)
MODEL = os.getenv("OPENROUTER_MODEL") or "mistralai/mistral-small-3.1-24b-instruct:free"
OPENROUTER_URL = "https://openrouter.ai/api/v1/chat/completions"

# Model parameters for better output quality
TEMPERATURE = float(os.getenv("OPENROUTER_TEMPERATURE", "0.7"))  # Creativity vs consistency balance
TOP_P = float(os.getenv("OPENROUTER_TOP_P", "0.9"))  # Nucleus sampling
TOP_K = int(os.getenv("OPENROUTER_TOP_K", "40"))  # Top-k sampling
MAX_TOKENS = int(os.getenv("OPENROUTER_MAX_TOKENS") or "2048")  # Response length limit

def env_flag(name, default=False):
    """Read a boolean environment variable; an unset or blank value uses default."""
    value = os.getenv(name)
    if value is None or not value.strip():
        return default
    return value.strip().lower() in ("1", "true", "yes", "on")

def optional_env_flag(name):
    """Read an optional boolean; return None when no explicit override exists."""
    value = os.getenv(name)
    if value is None or not value.strip():
        return None
    return env_flag(name)

# Keep structured output on by default for models that support it. Models such
# as inclusionai/ling-3.0-tiny can opt out without changing the code.
USE_STRUCTURED_OUTPUT = env_flag("OPENROUTER_USE_STRUCTURED_OUTPUT", default=True)
# Set this only while investigating provider responses; it can expose article
# text in the GitHub Actions log.
DEBUG_OPENROUTER_RESPONSES = env_flag("OPENROUTER_DEBUG_RESPONSES", default=False)
# Unset means "use the model/provider default". Set false for a reasoning
# model that spends too much of its response budget before producing JSON.
REASONING_ENABLED = optional_env_flag("OPENROUTER_REASONING_ENABLED")
# Comma-separated OpenRouter model IDs. These are tried automatically when the
# primary model is unavailable, rate-limited, or rejected by a provider.
FALLBACK_MODELS = [
    model_id.strip()
    for model_id in (os.getenv("OPENROUTER_FALLBACK_MODELS") or "").split(",")
    if model_id.strip() and model_id.strip() != MODEL
]

PROCESSED_LINKS_FILE = "scripts/processed_links.json"
OUTPUT_FILE = "data.json"
SOURCE_FILE = "scripts/source.json"
SOURCE_CURSOR_FILE = "scripts/source_cursor.json"

# Output and API call control
MAX_NEW_ITEMS = 5         # Maximum successful output items for this run (max 5 items you want)
MAX_API_CALLS = 8         # Maximum model API calls for this run (failures also count)
MAX_PER_SOURCE = 5        # Maximum candidate items sampled per source (candidates only, not final success count)
SOURCES_PER_RUN = 5       # Check this many consecutive sources, then advance the cursor
HTTP_TIMEOUT = 20         # Timeout seconds for web scraping/model calls
REQUEST_SLEEP = 0.2       # Light sleep to reduce rate limiting probability

# CSS selector list for extracting main content (优先尝试的内容选择器)
CONTENT_SELECTORS = [
    'article', 'div.article-content', 'div#article-content', 'div.post-content',
    'div.entry-content', 'section.article-body', 'div.content__article-body',
    'div.prose', 'div.rich-text', 'div#content', 'main', 'section#content',
    'div[itemprop="articleBody"]', 'div#main-content',
]

# 噪音过滤关键词
NOISE_KEYWORDS = ['subscribe', 'newsletter', 'related', 'advert', 'recommend', 'copyright']
MIN_LINE_LENGTH = 30  # 最小行长度阈值

# Dynamic MAX_CONTENT_CHARS based on model capabilities
def get_max_content_chars(model_name):
    """Get maximum content characters based on model specifications"""
    model_configs = {
        # Mistral models
        "mistralai/mistral-small-3.2-24b-instruct:free": 50000,  # 128k tokens
        "mistralai/mistral-small": 50000,
        "mistralai/mistral-medium": 50000,
        "mistralai/mistral-large": 50000,
        
        # Google Gemini models
        "google/gemini-2.5-flash": 200000,  # 1M tokens
        "google/gemini-2.5-pro": 200000,    # 1M tokens
        "google/gemini-2.5-flash-lite": 200000,  # 1M tokens
        "google/gemini-2.0-flash": 200000,  # 1M tokens
        "google/gemini-1.5-pro": 100000,    # 2M tokens but conservative
        "google/gemini-1.5-flash": 100000,  # 1M tokens
        
        # OpenAI models
        "openai/gpt-4o": 80000,     # 128k tokens
        "openai/gpt-4o-mini": 80000, # 128k tokens
        "openai/gpt-4-turbo": 80000, # 128k tokens
        "openai/gpt-3.5-turbo": 10000, # 16k tokens
        
        # Anthropic models
        "anthropic/claude-3.5-sonnet": 150000,  # 200k tokens
        "anthropic/claude-3-opus": 150000,      # 200k tokens
        "anthropic/claude-3-haiku": 150000,     # 200k tokens
        
        # Default fallback
        "default": 15000  # Conservative default
    }
    
    # Try exact match first
    if model_name in model_configs:
        return model_configs[model_name]
    
    # Try partial matches for model families
    for model_key, chars in model_configs.items():
        if model_key != "default" and any(part in model_name.lower() for part in model_key.lower().split("/")[-1].split("-")[:2]):
            return chars
    
    # Return default if no match found
    return model_configs["default"]

MAX_CONTENT_CHARS = get_max_content_chars(MODEL)

# Debug output for model configuration
print(f"Using model: {MODEL}")
print(f"MAX_CONTENT_CHARS: {MAX_CONTENT_CHARS:,}")
print(f"Model parameters: temperature={TEMPERATURE}, top_p={TOP_P}, top_k={TOP_K}, max_tokens={MAX_TOKENS}")

# ========== Initialize File Read/Write ==========
# Load processed links
try:
    with open(PROCESSED_LINKS_FILE, 'r', encoding='utf-8') as f:
        processed_links = set(json.load(f))
except (FileNotFoundError, json.JSONDecodeError):
    processed_links = set()
print(f"Loaded {len(processed_links)} processed links.")

# Ensure data.json exists and is a valid JSON array
if not os.path.exists(OUTPUT_FILE) or os.path.getsize(OUTPUT_FILE) == 0:
    with open(OUTPUT_FILE, 'w', encoding='utf-8') as f:
        f.write('[]')

# Calculate next ID
with open(OUTPUT_FILE, 'r', encoding='utf-8') as f:
    try:
        results = json.load(f)
        counter = (results[-1]['id'] + 1) if results else 1
    except (json.JSONDecodeError, IndexError, KeyError, TypeError):
        counter = 1
print(f"Next new entry ID will start from {counter}.")

# Load sources
try:
    with open(SOURCE_FILE, 'r', encoding='utf-8') as f:
        sources = json.load(f)
except (FileNotFoundError, json.JSONDecodeError) as e:
    print(f"WARNING: Failed to load source file {SOURCE_FILE}: {e}")
    print("No new valid records this time, no write needed.")
    print("\nAll processes completed: Successfully added 0 items; Model called 0 times.")
    exit(0)  # Exit gracefully if source file is missing or invalid

# Select a different consecutive group of sources on each run. The cursor is
# committed with the results so the next scheduled run continues where this one
# stopped, including wrap-around at the end of the source list.
if not isinstance(sources, list) or not sources:
    print(f"WARNING: Source file {SOURCE_FILE} must contain a non-empty JSON array.")
    exit(0)

try:
    with open(SOURCE_CURSOR_FILE, 'r', encoding='utf-8') as f:
        source_cursor = json.load(f).get('next_source_index', 0)
    source_cursor = int(source_cursor) % len(sources)
except (FileNotFoundError, json.JSONDecodeError, AttributeError, TypeError, ValueError):
    source_cursor = 0

sources_this_run = [
    sources[(source_cursor + offset) % len(sources)]
    for offset in range(min(SOURCES_PER_RUN, len(sources)))
]
next_source_cursor = (source_cursor + SOURCES_PER_RUN) % len(sources)
selected_source_names = [source.get('name', '(unnamed source)') for source in sources_this_run]
print(f"Source rotation: starting at {source_cursor}; checking {selected_source_names}; next start: {next_source_cursor}.")

# ========== Utility Functions ==========
def entry_pubdate(entry):
    """Get the publication time (datetime) of an entry. Return datetime.min if none exists for sorting to the end."""
    pp = entry.get('published_parsed')
    if pp:
        return datetime.fromtimestamp(time.mktime(pp))
    return datetime.min

def is_valid_content_link(link):
    """Check if the link points to actual content rather than platform homepages."""
    if not link:
        return False
    
    # Filter out generic platform links that don't point to specific content
    invalid_patterns = [
        r'^https?://www\.siriusxm\.com/?$',  # SiriusXM homepage
        r'^https?://[^/]+/?$',  # Any domain homepage without path
        r'^https?://[^/]+/?(#.*)?$',  # Domain with only fragment
        r'^https?://[^/]+/?(\?.*)?$',  # Domain with only query params
    ]
    
    for pattern in invalid_patterns:
        if re.match(pattern, link):
            return False
    
    return True

def clean_text_lines(text):
    """清洗文本行，移除噪音内容"""
    if not text:
        return ""
    
    lines = text.split('\n')
    cleaned_lines = []
    
    for line in lines:
        line = line.strip()
        if not line:
            continue
            
        # 检查是否包含噪音关键词且长度过短
        line_lower = line.lower()
        has_noise = any(keyword in line_lower for keyword in NOISE_KEYWORDS)
        is_short = len(line) < MIN_LINE_LENGTH
        
        # 丢弃含有噪音关键词且长度过短的行
        if has_noise and is_short:
            continue
            
        cleaned_lines.append(line)
    
    return '\n'.join(cleaned_lines)

def optimize_content_length(text):
    """内容长度优化：文本过长时采用头75%+尾25%拼接策略"""
    if not text:
        return text
    
    # 如果文本长度在限制范围内，直接返回
    if len(text) <= MAX_CONTENT_CHARS:
        return text
    
    # 文本过长，采用头75%+尾25%的切片策略
    # 先按段落分割，保持段落完整性
    paragraphs = [p.strip() for p in text.split('\n\n') if p.strip()]
    
    if not paragraphs:
        # 如果没有段落分割，按行分割
        lines = [line.strip() for line in text.split('\n') if line.strip()]
        if not lines:
            return text[:MAX_CONTENT_CHARS]
        
        total_lines = len(lines)
        head_lines = int(total_lines * 0.75)
        tail_lines = total_lines - head_lines
        
        head_content = '\n'.join(lines[:head_lines])
        tail_content = '\n'.join(lines[-tail_lines:]) if tail_lines > 0 else ''
        
        combined = head_content
        if tail_content:
            combined += '\n\n[... 中间内容已省略 ...]\n\n' + tail_content
        
        # 如果合并后仍然过长，进行字符级截断
        if len(combined) > MAX_CONTENT_CHARS:
            head_chars = int(MAX_CONTENT_CHARS * 0.75)
            tail_chars = MAX_CONTENT_CHARS - head_chars - 50  # 预留省略标记空间
            if tail_chars > 0:
                combined = text[:head_chars] + '\n\n[... 内容已截断 ...]\n\n' + text[-tail_chars:]
            else:
                combined = text[:MAX_CONTENT_CHARS]
        
        return combined
    
    # 按段落处理
    total_paragraphs = len(paragraphs)
    head_paragraphs = int(total_paragraphs * 0.75)
    tail_paragraphs = total_paragraphs - head_paragraphs
    
    head_content = '\n\n'.join(paragraphs[:head_paragraphs])
    tail_content = '\n\n'.join(paragraphs[-tail_paragraphs:]) if tail_paragraphs > 0 else ''
    
    combined = head_content
    if tail_content:
        combined += '\n\n[... 中间段落已省略 ...]\n\n' + tail_content
    
    # 如果合并后仍然过长，进行字符级截断
    if len(combined) > MAX_CONTENT_CHARS:
        head_chars = int(MAX_CONTENT_CHARS * 0.75)
        tail_chars = MAX_CONTENT_CHARS - head_chars - 50  # 预留省略标记空间
        if tail_chars > 0:
            combined = text[:head_chars] + '\n\n[... 内容已截断 ...]\n\n' + text[-tail_chars:]
        else:
            combined = text[:MAX_CONTENT_CHARS]
    
    return combined

def extract_full_content(link, rss_content_html):
    """Extract webpage content; if RSS already contains long content, use it directly; otherwise scrape webpage and extract content."""
    # First try RSS content (some sources have complete content)
    content_from_rss = ""
    if isinstance(rss_content_html, list) and rss_content_html:
        content_from_rss = rss_content_html[0].get('value', '') or ''
    elif isinstance(rss_content_html, str):
        content_from_rss = rss_content_html

    if len(content_from_rss) > 1000:
        cleaned_rss = clean_text_lines(content_from_rss)
        optimized_rss = optimize_content_length(cleaned_rss)
        return optimized_rss, "Content fully retrieved from RSS Feed."

    # RSS content is short, try to scrape webpage
    headers = {'User-Agent': 'Mozilla/5.0'}
    try:
        resp = requests.get(link, headers=headers, timeout=HTTP_TIMEOUT)
        resp.raise_for_status()
    except Exception as e:
        cleaned_rss = clean_text_lines(content_from_rss)
        optimized_rss = optimize_content_length(cleaned_rss)
        return optimized_rss, f"RSS content is summary, webpage scraping failed: {e}, fallback to RSS summary."

    soup = BeautifulSoup(resp.text, 'html.parser')

    # 优先尝试内容选择器
    article_body = None
    for selector in CONTENT_SELECTORS:
        node = soup.select_one(selector)
        if node:
            article_body = node
            break

    # 兜底策略：从 article/div/section/main 中选文本最长的容器
    if not article_body:
        fallback_candidates = []
        for tag_name in ['article', 'div', 'section', 'main']:
            elements = soup.find_all(tag_name)
            for element in elements:
                # 移除导航、页脚、侧边栏等噪音元素
                temp_element = element.__copy__()
                for noise_tag in temp_element.find_all(['nav', 'footer', 'header', 'aside', 'script', 'style']):
                    noise_tag.decompose()
                
                text_content = temp_element.get_text(separator='\n', strip=True)
                if text_content:
                    fallback_candidates.append((element, len(text_content)))
        
        # 选择文本最长的容器
        if fallback_candidates:
            article_body = max(fallback_candidates, key=lambda x: x[1])[0]

    # 最后的兜底：清理后的body
    if not article_body:
        body = soup.find('body')
        if body:
            for tag in body.find_all(['nav', 'footer', 'header', 'aside', 'script', 'style']):
                tag.decompose()
            article_body = body

    if article_body:
        text = article_body.get_text(separator='\n', strip=True)
        cleaned_text = clean_text_lines(text)
        optimized_text = optimize_content_length(cleaned_text)
        return optimized_text, "Content extraction successful!"
    else:
        cleaned_rss = clean_text_lines(content_from_rss)
        optimized_rss = optimize_content_length(cleaned_rss)
        return optimized_rss, "Warning: Failed to extract main content, will use RSS summary."


def parse_json_safely(text):
    """
    Compatible with the following returns:
    - Pure JSON
    - ```json ... ``` or ``` ... ``` wrapped
    - Leading/trailing prompts/blank lines/spaces
    - Multiple text segments containing one or more {...} JSON blocks (take the first complete block)
    """
    # 1) Direct attempt
    try:
        return json.loads(text)
    except Exception:
        pass

    # 2) Remove ```json ... ``` / ``` ... ``` code fences
    fenced = re.search(r"```(?:json)?\s*(.+?)\s*```", text, flags=re.DOTALL | re.IGNORECASE)
    if fenced:
        inner = fenced.group(1).strip()
        try:
            return json.loads(inner)
        except Exception:
            text = inner  # Continue with subsequent steps

    # 3) Extract the first complete brace JSON block from the full text
    #    Use stack matching to avoid misjudgment caused by regex greediness
    start = text.find('{')
    while start != -1:
        stack = 0
        for i in range(start, len(text)):
            if text[i] == '{':
                stack += 1
            elif text[i] == '}':
                stack -= 1
                if stack == 0:
                    candidate = text[start:i+1]
                    try:
                        return json.loads(candidate)
                    except Exception:
                        break  # Try another starting point
        # Find next '{'
        start = text.find('{', start + 1)

    # 4) If all else fails, throw error and let upper layer record original text
    raise json.JSONDecodeError("No valid JSON object found", text, 0)


def missing_required_analysis_fields(analysis_data):
    """Return required output fields that are missing or empty."""
    required_text_fields = [
        'title_zh', 'summary_en', 'summary_zh',
        'best_quote_en', 'best_quote_zh'
    ]
    missing = [
        field for field in required_text_fields
        if not isinstance(analysis_data.get(field), str) or not analysis_data[field].strip()
    ]
    for field in ('tags', 'tags_zh'):
        tags = analysis_data.get(field)
        if not isinstance(tags, list) or not any(isinstance(tag, str) and tag.strip() for tag in tags):
            missing.append(field)
    return missing


def call_openrouter(model, title, full_content):
    # Updated prompt for smart tagging system
    prompt_content = f"""
# TASK: Intelligent Content Analysis & Value-Based Tagging

You are an expert content analyst specializing in extracting meaningful insights and generating intelligent tags based on content value and user discoverability.

## ANALYSIS FRAMEWORK:

### 1. CONTENT VALUE IDENTIFICATION
- Assess information novelty and uniqueness
- Evaluate practical applicability and actionability
- Identify thought leadership and expert insights
- Determine educational and learning value

### 2. USER INTENT PREDICTION
- Consider what users would search for to find this content
- Identify the primary problems this content solves
- Determine the target audience and their needs
- Predict discovery patterns and search behaviors

### 3. THREE-LAYER TAG GENERATION
- Layer 1 (Value Type): Identify user reading intent (learn/solve/inspire/update/analyze/guide)
- Layer 2 (Domain Theme): Determine content domain and thematic focus
- Layer 3 (Feature Tags): Add 1-3 descriptive characteristics (actionable, advanced, etc.)
- Ensure hierarchical consistency and user discoverability across all layers

## TAG STRATEGY:

**Layer 1 - Value Types (用户意图):** learn, solve, inspire, update, analyze, guide
**Layer 2 - Domain Themes (领域主题):** ai-research, ai-product, startup-strategy, startup-funding, tech-trends, programming, cybersecurity, business-model, marketing, leadership, science, medicine, psychology, politics, economics, society, lifestyle, education, design
**Layer 3 - Feature Tags (内容特征):** actionable, beginner-friendly, advanced, controversial, data-driven, future-focused, problem-solving, case-study, tutorial, expert-insight

## OUTPUT SPECIFICATION:

Return a JSON object with exactly these fields:

```json
{{
  "title_zh": "Chinese translation of title (keep original if already Chinese)",
  "summary_en": "150-200 word English analysis focusing on core insights, implications, and critical evaluation. Write with intellectual curiosity and personal engagement.",
  "summary_zh": "150-200 character Chinese analysis that reads like thoughtful commentary, not mere summary. Include personal reflection and broader significance.",
  "best_quote_en": "Most insightful English quote from article (translate if originally Chinese)",
  "best_quote_zh": "Most insightful Chinese quote from article (translate if originally English)",
  "tags": ["value-based", "discoverable", "English", "tags"],
  "tags_zh": ["基于价值", "可发现的", "中文", "标签"]
}}
```

## TAGGING QUALITY STANDARDS:

**DO:**
- Apply the three-layer tag hierarchy: Value Type + Domain Theme + Feature Tags
- Layer 1: Identify user intent (learn/solve/inspire/update/analyze/guide)
- Layer 2: Determine domain theme based on content focus
- Layer 3: Add 1-3 feature tags that describe content characteristics
- Ensure tags reflect actual content value and user discoverability
- Generate 3-6 high-quality tags per language following the hierarchy

**AVOID:**
- Mixing tags from different layers without clear hierarchy
- Generic topic tags without value context
- Overly specific tags that limit discoverability
- Redundant tags within the same layer
- More than 6 tags per language or ignoring the three-layer structure

## INPUT:

**Title:** {title}

**Content:**
{full_content}

---

Provide your analysis as a clean JSON object only.""".strip()

    # Used only when a provider cannot return a complete JSON response to the
    # full prompt. Shorter summaries make it much less likely that generation
    # reaches the output-token limit before closing the JSON object.
    compact_retry_prompt = f"""
Return ONLY one valid JSON object. Do not use Markdown or code fences.

Required fields:
{{
  "title_zh": "Chinese title",
  "summary_en": "80-120 word English summary",
  "summary_zh": "80-120 Chinese character summary",
  "best_quote_en": "short English quote, at most 25 words",
  "best_quote_zh": "Chinese translation of the quote",
  "tags": ["3-5 English tags"],
  "tags_zh": ["3-5 Chinese tags"]
}}

Title: {title}

Content:
{full_content}
""".strip()

    headers = {
        "Authorization": f"Bearer {OPENROUTER_API_KEY}",
        "Content-Type": "application/json"
    }

    # APE-optimized system prompt for better instruction following
    system_prompt = """
You are a world-class content analyst with expertise in:
- Deep textual analysis and critical thinking
- Cross-cultural communication and translation
- Insight extraction and synthesis
- Structured data output

Core competencies:
1. ANALYTICAL PRECISION: Extract meaningful insights beyond surface content
2. LINGUISTIC EXCELLENCE: Provide nuanced translations and culturally appropriate summaries
3. FORMAT COMPLIANCE: Generate clean, valid JSON without extraneous text
4. INTELLECTUAL ENGAGEMENT: Write with genuine curiosity and thoughtful perspective

Output requirements:
- Return ONLY valid JSON objects
- No code blocks, explanations, or additional text
- Maintain strict language separation in tag arrays
- Focus on insight over summary""".strip()

    base_payload = {
        "model": model,
        "temperature": TEMPERATURE,
        "top_p": TOP_P,
        "top_k": TOP_K,
        "max_tokens": MAX_TOKENS,
        "messages": [
            {
                "role": "system",
                "content": system_prompt
            },
            {"role": "user", "content": prompt_content}
        ],
    }
    if FALLBACK_MODELS:
        base_payload["models"] = FALLBACK_MODELS
        print(f"[OpenRouter] Model fallback chain: {model} -> {', '.join(FALLBACK_MODELS)}")

    def log_empty_choice_diagnostics(api_response, choice, raw_response):
        """Log safe response metadata when HTTP 200 contains no generated text."""
        message = choice.get('message') if isinstance(choice, dict) else None
        content = message.get('content') if isinstance(message, dict) else None
        reasoning = message.get('reasoning') if isinstance(message, dict) else None
        diagnostics = {
            "model": api_response.get('model'),
            "provider": api_response.get('provider'),
            "finish_reason": choice.get('finish_reason') if isinstance(choice, dict) else None,
            "native_finish_reason": choice.get('native_finish_reason') if isinstance(choice, dict) else None,
            "choice_keys": sorted(choice.keys()) if isinstance(choice, dict) else [],
            "message_keys": sorted(message.keys()) if isinstance(message, dict) else [],
            "content_type": type(content).__name__,
            "content_length": len(content) if isinstance(content, str) else None,
            "has_refusal": bool(message.get('refusal')) if isinstance(message, dict) else False,
            "reasoning_length": len(reasoning) if isinstance(reasoning, str) else None,
            "usage": api_response.get('usage'),
        }
        print("[OpenRouter] Empty-content diagnostics: " + json.dumps(diagnostics, ensure_ascii=False, default=str))
        if DEBUG_OPENROUTER_RESPONSES:
            print(f"[OpenRouter] Debug raw response (first 2000 chars): {raw_response[:2000]}")

    compact_system_prompt = """
Return the final JSON object immediately. Do not provide explanations, code
fences, or extended reasoning. Keep every field concise and valid JSON.
""".strip()

    # Try each prompt first with the requested reasoning setting. If the
    # provider rejects that setting, retry the same prompt without a reasoning
    # parameter before moving to the next fallback.
    reasoning_variants = [True, False] if REASONING_ENABLED is not None else [False]
    attempts = []
    if USE_STRUCTURED_OUTPUT:
        attempts.extend(("structured JSON", prompt_content, system_prompt, True, use_reasoning)
                        for use_reasoning in reasoning_variants)
    attempts.extend(("standard JSON", prompt_content, system_prompt, False, use_reasoning)
                    for use_reasoning in reasoning_variants)
    attempts.extend(("compact JSON", compact_retry_prompt, compact_system_prompt, False, use_reasoning)
                    for use_reasoning in reasoning_variants)

    for attempt_index, (attempt_name, user_prompt, active_system_prompt, use_response_format, use_reasoning) in enumerate(attempts):
        is_last_attempt = attempt_index == len(attempts) - 1
        data = dict(base_payload)  # Shallow copy
        data["messages"] = [
            {"role": "system", "content": active_system_prompt},
            {"role": "user", "content": user_prompt}
        ]
        if use_response_format:
            data["response_format"] = {"type": "json_object"}
            print("[OpenRouter] Attempting to use response_format=json_object")
        elif attempt_name == "standard JSON":
            if USE_STRUCTURED_OUTPUT:
                print("[OpenRouter] Fallback retry without response_format")
            else:
                print("[OpenRouter] Structured output disabled; using standard JSON prompt")
        else:
            print("[OpenRouter] Final retry with compact JSON-only prompt")

        if use_reasoning:
            data["reasoning"] = {"enabled": REASONING_ENABLED}
            print(f"[OpenRouter] Using configured reasoning.enabled={REASONING_ENABLED}")
        elif REASONING_ENABLED is not None:
            print("[OpenRouter] Retrying without a reasoning parameter")

        try:
            resp = requests.post(OPENROUTER_URL, headers=headers, json=data, timeout=HTTP_TIMEOUT)
            status = resp.status_code
            text = resp.text
            print(f"[OpenRouter] HTTP {status}")
            if status >= 400:
                print(f"[OpenRouter] Body: {text[:1000]}")
                if not is_last_attempt:
                    continue
                resp.raise_for_status()
            # Parse response
            api_response = resp.json()
            
            # Check if response is valid format
            if not isinstance(api_response, dict):
                if not is_last_attempt:
                    print(f"[OpenRouter] Invalid response format (not dict), will retry. Type: {type(api_response)}")
                    continue
                return None, f"Invalid response format: expected dict, got {type(api_response)}"
            
            if api_response.get("error"):
                if not is_last_attempt:
                    print(f"[OpenRouter] API Error during {attempt_name}, will retry: {api_response['error']}")
                    continue
                return None, f"API Error: {api_response['error']}"

            # Check if choices exist and have expected structure
            if not api_response.get('choices') or not isinstance(api_response['choices'], list) or len(api_response['choices']) == 0:
                if not is_last_attempt:
                    print(f"[OpenRouter] Missing or invalid choices in response, will retry")
                    continue
                return None, f"Invalid response structure: missing or empty choices"
            
            choice = api_response['choices'][0]
            if not isinstance(choice, dict) or not choice.get('message') or not choice['message'].get('content'):
                log_empty_choice_diagnostics(api_response, choice, text)
                if not is_last_attempt:
                    print(f"[OpenRouter] Invalid choice structure, will retry")
                    continue
                return None, f"Invalid choice structure: missing message or content"
            
            content = choice['message']['content']
            try:
                analysis_data = parse_json_safely(content)
                # When OpenRouter routes to a fallback, this normally contains
                # the resolved model ID rather than the requested primary.
                analysis_data['_model_used'] = api_response.get('model') or model
                return analysis_data, content
            except json.JSONDecodeError as e:
                if not is_last_attempt:
                    print(f"[Parse failed during {attempt_name}] {e}; will retry. First 500 chars: {content[:500]}")
                    continue
                return None, f"JSONDecodeError(after compact retry): {e}; content: {content[:1000]}"

        except requests.HTTPError:
            if not is_last_attempt:
                continue
            return None, f"HTTPError: {resp.status_code}; body: {resp.text[:1000]}"
        except Exception as e:
            if not is_last_attempt:
                continue
            return None, f"RequestError: {e}"

    # Should theoretically never reach here
    return None, "Unknown error"

# ========== Stage 1: Collect candidates by source buckets ==========
candidates_by_source = {}  # { source_name: [entry, entry, ...] }
for source in sources_this_run:
    source_name = source.get('name', '')
    rss_url = source.get('url', '')
    if not rss_url:
        continue

    print(f"--- Collecting candidates: {source_name} ---")
    try:
        feed = feedparser.parse(rss_url)
        if not feed.entries:
            print("  No content found.")
            continue

        # Sort this source by time in descending order
        sorted_entries = sorted(feed.entries, key=entry_pubdate, reverse=True)

        # Sample to candidate pool (unprocessed only)
        bucket = []
        for e in sorted_entries:
            if len(bucket) >= MAX_PER_SOURCE:
                break
            link = e.get('link') or ''
            if not link or link in processed_links:
                continue
            bucket.append(e)

        if bucket:
            candidates_by_source[source_name] = bucket
            print(f"  {len(bucket)} candidates.")
        else:
            print("  No new candidates available (all processed or no links).")

    except Exception as e:
        print(f"[Collecting candidates] Source '{source_name}' parsing error: {e}")

source_names = list(candidates_by_source.keys())
candidates_info = ', '.join([f'{k}:{len(v)}' for k,v in candidates_by_source.items()])
print(f"Available sources: {len(source_names)}; Candidates per source: {{{candidates_info}}}")

# ========== Stage 2: Round-robin processing of candidates from each source (ensure balance) ==========
newly_processed_items = []
new_items_count = 0
api_calls = 0

# Round-robin pointer
idx = 0
while source_names and new_items_count < MAX_NEW_ITEMS and api_calls < MAX_API_CALLS:
    source_name = source_names[idx % len(source_names)]
    bucket = candidates_by_source.get(source_name, [])
    if not bucket:
        # Source is empty, remove and don't increment idx (shrink the ring)
        candidates_by_source.pop(source_name, None)
        source_names.remove(source_name)
        continue

    # Take one item from this source (head of queue)
    latest_entry = bucket.pop(0)
    if not bucket:
        # If this source is now empty, it will be removed in next loop
        candidates_by_source[source_name] = []

    title = latest_entry.get('title', 'No Title')
    link = latest_entry.get('link', '')
    if not link or link in processed_links or not is_valid_content_link(link):
        # Skip invalid links, already processed links, or generic platform links
        idx += 1
        continue

    # Date
    published_parsed = latest_entry.get('published_parsed')
    if published_parsed:
        dt_object = datetime.fromtimestamp(time.mktime(published_parsed))
        date_str = dt_object.strftime('%Y-%m-%d')
    else:
        date_str = datetime.now().strftime('%Y-%m-%d')

    print(f"\nProcessing entry (balanced mode): {title}")
    print(f"Source: {source_name}")
    print(f"Link: {link}")

    # Extract content
    full_content, extract_msg = extract_full_content(
        link, latest_entry.get('content', [{'value': ''}])
    )
    print(f"Content extraction: {extract_msg}")

    # Skip if content is too short (don't consume model calls)
    if len(full_content.strip()) < 200:
        print("Content too short, skipping this entry (no model call).")
        idx += 1
        continue

    # Truncate if too long
    if len(full_content) > MAX_CONTENT_CHARS:
        print(f"Content too long ({len(full_content)}), truncating to {MAX_CONTENT_CHARS} characters.")
        full_content = full_content[:MAX_CONTENT_CHARS]

    # Call model (failures also count towards API calls)
    api_calls += 1
    time.sleep(REQUEST_SLEEP)
    analysis_data, raw_debug = call_openrouter(MODEL, title, full_content)

    if analysis_data is None:
        print(f"[Failed] Model call/parsing failed: {raw_debug}")
        print(f"[Progress] Success {new_items_count}/{MAX_NEW_ITEMS}, Calls {api_calls}/{MAX_API_CALLS}")
        # Failures also advance to next source (maintain balanced rhythm)
        idx += 1
        continue

    # Check if analysis_data is valid dictionary format
    if not isinstance(analysis_data, dict):
        print(f"[Failed] Invalid analysis_data format (expected dict, got {type(analysis_data).__name__}): {analysis_data}")
        print(f"[Progress] Success {new_items_count}/{MAX_NEW_ITEMS}, Calls {api_calls}/{MAX_API_CALLS}")
        # Skip this entry and continue to next
        idx += 1
        continue

    missing_fields = missing_required_analysis_fields(analysis_data)
    if missing_fields:
        print(f"[Failed] AI response is missing required fields: {', '.join(missing_fields)}. Link will remain eligible for a future retry.")
        print(f"[Progress] Success {new_items_count}/{MAX_NEW_ITEMS}, Calls {api_calls}/{MAX_API_CALLS}")
        # Do not add this link to processed_links, so a future run can retry it
        # with the primary model or a different OpenRouter fallback.
        idx += 1
        continue
    
    # Use TagOptimizer to optimize tags from AI analysis
    try:
        if 'tag_optimizer' not in globals():
            global tag_optimizer
            tag_optimizer = TagOptimizer()
        
        # Get LLM tags as candidates
        llm_tags_en = analysis_data.get('tags', [])
        llm_tags_zh = analysis_data.get('tags_zh', [])
        
        # Optimize tags using multi-stage process
        tags_en, tags_zh = tag_optimizer.optimize_tags(
            llm_tags_en=llm_tags_en,
            llm_tags_zh=llm_tags_zh,
            title=title,
            content=full_content,
            url=link,
            source_name=source_name
        )
        
        print(f"Tag optimization: {len(llm_tags_en + llm_tags_zh)} candidates -> {len(tags_en + tags_zh)} final tags")
        
    except Exception as e:
        print(f"Tag optimization failed, using LLM tags directly: {e}")
        # Fallback to original LLM tags with safe access
        tags_en = analysis_data.get('tags', []) if isinstance(analysis_data, dict) else []
        tags_zh = analysis_data.get('tags_zh', []) if isinstance(analysis_data, dict) else []
    
    # Assemble result with safe dictionary access
    try:
        final_item = {
            "id": counter,
            "title": title,
            "title_zh": analysis_data.get('title_zh', '') if isinstance(analysis_data, dict) else '',
            "model_used": analysis_data.get('_model_used', MODEL),
            "source": source_name,
            "link": link,
            "tags": tags_en,
            "tags_zh": tags_zh,
            "date": date_str,
            "summary_en": analysis_data.get('summary_en', '') if isinstance(analysis_data, dict) else '',
            "summary_zh": analysis_data.get('summary_zh', '') if isinstance(analysis_data, dict) else '',
            "best_quote_en": analysis_data.get('best_quote_en', '') if isinstance(analysis_data, dict) else '',
            "best_quote_zh": analysis_data.get('best_quote_zh', '') if isinstance(analysis_data, dict) else ''
        }
    except Exception as e:
        print(f"[Failed] Error assembling final item: {e}")
        print(f"[Progress] Success {new_items_count}/{MAX_NEW_ITEMS}, Calls {api_calls}/{MAX_API_CALLS}")
        # Skip this entry and continue to next
        idx += 1
        continue

    newly_processed_items.append(final_item)
    processed_links.add(link)
    counter += 1
    new_items_count += 1
    print(f"[Success] Generated {new_items_count}/{MAX_NEW_ITEMS} items; Total calls {api_calls}/{MAX_API_CALLS}")

    # Both success and failure advance to next source
    idx += 1

# ========== Write Results ==========
# Incremental write to data.json (append new objects at the end)
if newly_processed_items:
    print(f"\nWriting {len(newly_processed_items)} new records to {OUTPUT_FILE} incrementally...")
    with open(OUTPUT_FILE, 'rb+') as f:
        f.seek(0, os.SEEK_END)
        size = f.tell()
        if size == 0:
            f.write(b'[]')
            f.flush()
            f.seek(0, os.SEEK_END)

        # Move to the last character and check if it's ']'
        f.seek(-1, os.SEEK_END)
        last_char = f.read(1)
        if last_char != b']':
            print("Warning: data.json is not a valid JSON array, will overwrite completely.")
            with open(OUTPUT_FILE, 'w', encoding='utf-8') as wf:
                all_items = results + newly_processed_items if 'results' in locals() and isinstance(results, list) else newly_processed_items
                json.dump(all_items, wf, indent=2, ensure_ascii=False)
        else:
            # Check if it's a non-empty array to decide whether to add comma
            non_empty_array = False
            try:
                with open(OUTPUT_FILE, 'r', encoding='utf-8') as rf:
                    existing = json.load(rf)
                    non_empty_array = len(existing) > 0
            except Exception:
                pass

            # Go back before the ending ']', prepare to append
            f.seek(-1, os.SEEK_END)
            if non_empty_array:
                f.write(b',')
            new_data_string = json.dumps(newly_processed_items, indent=2, ensure_ascii=False)
            new_data_string = new_data_string[1:-1].strip()  # Remove list brackets
            f.write(new_data_string.encode('utf-8'))
            f.write(b']')
    print("Incremental write completed.")
    
    # Check if we need to limit to 100 records
    try:
        with open(OUTPUT_FILE, 'r', encoding='utf-8') as f:
            all_data = json.load(f)
        
        if len(all_data) > 100:
            print(f"\nData contains {len(all_data)} records, limiting to 100 most recent...")
            # Keep only the last 100 records (most recent)
            limited_data = all_data[-100:]
            
            with open(OUTPUT_FILE, 'w', encoding='utf-8') as f:
                json.dump(limited_data, f, indent=2, ensure_ascii=False)
            
            print(f"Successfully limited data to {len(limited_data)} records.")
        else:
            print(f"Data contains {len(all_data)} records, no limiting needed.")
    except Exception as e:
        print(f"Warning: Failed to check/limit data size: {e}")
else:
    print("\nNo new valid records this time, no write needed.")

# Overwrite processed_links.json
with open(PROCESSED_LINKS_FILE, 'w', encoding='utf-8') as f:
    json.dump(sorted(list(processed_links)), f, indent=2, ensure_ascii=False)

# Persist the next starting point even when this batch had no new items, so a
# quiet or broken source cannot prevent the rotation from reaching later ones.
with open(SOURCE_CURSOR_FILE, 'w', encoding='utf-8') as f:
    json.dump({"next_source_index": next_source_cursor}, f, indent=2, ensure_ascii=False)

print(f"\nAll processes completed: Successfully added {new_items_count} items; Model called {api_calls} times. Output file: {OUTPUT_FILE}, Link cache: {PROCESSED_LINKS_FILE}")
