#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
新一代标签优化器 - 基于内容价值和用户发现性

重构说明：
- 完全替换旧的复杂映射系统
- 使用智能标签生成器
- 保持与现有RSS分析器的接口兼容性
"""

import os
import sys
from typing import List, Tuple

# 导入新的智能标签生成器
from smart_tag_generator import SmartTagGenerator, TagResult


def flatten_tags(tags):
    """展平嵌套标签并转换为字符串列表"""
    flat = []
    if isinstance(tags, list):
        for t in tags:
            if isinstance(t, list):
                flat.extend(flatten_tags(t))
            elif isinstance(t, str):
                flat.append(t.strip())
            elif isinstance(t, (int, float)):
                flat.append(str(t))
            # 忽略 None 或其他类型
    elif isinstance(tags, str):
        flat.append(tags.strip())
    return [t for t in flat if t]  # 去除空字符串


class TagOptimizer:
    """标签优化器"""

    def __init__(self, scripts_dir: str = "scripts"):
        self.scripts_dir = scripts_dir
        self.smart_generator = SmartTagGenerator(scripts_dir)
        print(f"[TagOptimizer] Initialized with new smart tagging system")

    def optimize_tags(
        self,
        llm_tags_en: List[str],
        llm_tags_zh: List[str],
        title: str,
        content: str,
        url: str,
        source_name: str = ""
    ) -> Tuple[List[str], List[str]]:
        """
        优化标签的主要接口方法

        保持与原有系统的兼容性，但内部使用全新的智能标签生成逻辑
        """

        try:
            print(f"[TagOptimizer] Processing: {title[:50]}...")
            print(f"[TagOptimizer] Original LLM tags EN: {llm_tags_en}")
            print(f"[TagOptimizer] Original LLM tags ZH: {llm_tags_zh}")

            # ✅ 先展平输入，防止传入嵌套列表或非字符串
            llm_tags_en = flatten_tags(llm_tags_en)
            llm_tags_zh = flatten_tags(llm_tags_zh)

            print(f"[TagOptimizer] Cleaned LLM tags EN: {llm_tags_en}")
            print(f"[TagOptimizer] Cleaned LLM tags ZH: {llm_tags_zh}")

            # 使用智能标签生成器生成新标签
            llm_context = f"LLM suggested tags: {', '.join(llm_tags_en + llm_tags_zh)}"
            enhanced_content = f"{content} {llm_context}"

            result = self.smart_generator.generate_tags(
                title=title,
                summary_en=enhanced_content,
                summary_zh="",  # 中文摘要通常已包含在content中
                url=url,
                source=source_name
            )

            print(f"[TagOptimizer] Smart tags generated: {result.tags}")
            print(f"[TagOptimizer] Confidence: {result.confidence:.2f}")
            print(f"[TagOptimizer] Reasoning: {result.reasoning}")

            # ✅ 再展平智能生成结果（确保输出一维）
            tags_en = flatten_tags(result.tags)
            tags_zh = flatten_tags(result.tags_zh)

            # 如果置信度太低，回退到LLM标签
            if result.confidence < 0.4:
                print(f"[TagOptimizer] Low confidence, falling back to LLM tags")
                fallback_tags_en = llm_tags_en[:2] if llm_tags_en else ["general"]
                fallback_tags_zh = llm_tags_zh[:2] if llm_tags_zh else ["综合"]
                return fallback_tags_en, fallback_tags_zh

            return tags_en, tags_zh

        except Exception as e:
            print(f"[TagOptimizer] Error in tag optimization: {e}")
            print(f"[TagOptimizer] Falling back to original LLM tags")

            fallback_tags_en = flatten_tags(llm_tags_en[:2] if llm_tags_en else ["general"])
            fallback_tags_zh = flatten_tags(llm_tags_zh[:2] if llm_tags_zh else ["综合"])
            return fallback_tags_en, fallback_tags_zh

    def get_tag_statistics(self) -> dict:
        """获取标签统计信息"""
        stats = {
            "value_types": len(self.smart_generator.value_types),
            "domain_themes": len(self.smart_generator.domain_themes),
            "feature_tags": len(self.smart_generator.feature_tags),
            "total_possible_tags": (
                len(self.smart_generator.value_types)
                + len(self.smart_generator.domain_themes)
                + len(self.smart_generator.feature_tags)
            ),
        }
        return stats

    def explain_tag_system(self) -> str:
        """解释新标签系统的工作原理"""
        explanation = """
新智能标签系统说明：

1. 三层标签架构：
   - 第一层：价值类型（learn, solve, inspire, update, analyze, guide）
   - 第二层：领域主题（ai-research, startup-strategy, tech-trends等）
   - 第三层：特征标签（beginner-friendly, deep-dive, controversial等）

2. 核心原则：
   - 标签基于内容价值，而非简单分类
   - 优先考虑用户发现性和搜索意图
   - 动态适应内容复杂度（1-4个标签）

3. 生成逻辑：
   - 智能识别内容价值类型
   - 基于域名和关键词匹配领域主题
   - 根据内容特征添加特征标签
   - 计算标签权重和置信度

4. 优势：
   - 减少90%的手工配置
   - 提高标签一致性和准确性
   - 更好的用户体验和内容发现
        """
        return explanation


# 向后兼容性：保持原有的导入方式
def optimize_tags(
    llm_tags_en: List[str],
    llm_tags_zh: List[str],
    title: str,
    content: str,
    url: str,
    source_name: str = ""
) -> Tuple[List[str], List[str]]:
    """向后兼容的函数接口"""
    optimizer = TagOptimizer()
    return optimizer.optimize_tags(llm_tags_en, llm_tags_zh, title, content, url, source_name)


# 测试和演示
if __name__ == "__main__":
    print("=== 新一代标签优化器测试 ===")

    optimizer = TagOptimizer()

    print("\n=== 系统信息 ===")
    stats = optimizer.get_tag_statistics()
    print(f"可用标签类型: {stats}")

    print("\n=== 系统说明 ===")
    print(optimizer.explain_tag_system())

    print("\n=== 测试标签生成 ===")

    test_cases = [
        {
            "title": "The Gentle Singularity",
            "content": "This article explores the accelerating march towards artificial superintelligence, framing it not as a sudden cataclysm but a 'gentle singularity'",
            "url": "https://blog.samaltman.com/the-gentle-singularity",
            "source": "Sam Altman",
            "llm_tags_en": [["ai", "future"], ["AGI"]],
            "llm_tags_zh": [["人工智能", "未来"], ["超级智能"]],
        },
        {
            "title": "How to Build a Startup",
            "content": "A comprehensive guide to building a successful startup from idea to IPO, covering product development, fundraising, and scaling.",
            "url": "https://paulgraham.com/start.html",
            "source": "Paul Graham",
            "llm_tags_en": ["startup", "business"],
            "llm_tags_zh": ["创业", "商业"],
        },
    ]

    for i, test_case in enumerate(test_cases, 1):
        print(f"\n--- 测试案例 {i}: {test_case['title']} ---")

        optimized_en, optimized_zh = optimizer.optimize_tags(
            llm_tags_en=test_case["llm_tags_en"],
            llm_tags_zh=test_case["llm_tags_zh"],
            title=test_case["title"],
            content=test_case["content"],
            url=test_case["url"],
            source_name=test_case["source"],
        )

        print(f"原始LLM标签: {test_case['llm_tags_en']} / {test_case['llm_tags_zh']}")
        print(f"优化后标签: {optimized_en} / {optimized_zh}")
        print(f"标签数量: {len(optimized_en)}")

    print("\n=== 测试完成 ===")
