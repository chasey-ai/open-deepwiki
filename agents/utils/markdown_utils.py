"""Markdown处理工具"""

import re
from typing import List, Dict, Any, Tuple

def extract_headings(markdown_text: str) -> List[Tuple[int, str, str]]:
    """
    提取Markdown中的标题
    
    Args:
        markdown_text: Markdown文本
        
    Returns:
        标题列表，每个元素是(级别, 标题文本, ID)的元组
    """
    heading_pattern = r'^(#{1,6})\s+(.+?)(?:\s+\{#([^}]+)\})?$'
    headings = []
    
    for line in markdown_text.split('\n'):
        match = re.match(heading_pattern, line)
        if match:
            level = len(match.group(1))  # #的数量表示标题级别
            text = match.group(2).strip()
            # 使用指定的ID或从文本生成ID
            heading_id = match.group(3) if match.group(3) else generate_id(text)
            headings.append((level, text, heading_id))
    
    return headings

def generate_id(text: str) -> str:
    """
    从文本生成ID
    
    Args:
        text: 文本
        
    Returns:
        生成的ID
    """
    # 转换为小写
    id_text = text.lower()
    # 移除特殊字符和标点，替换为短横线
    id_text = re.sub(r'[^\w\s-]', '', id_text)
    # 替换空格为短横线
    id_text = re.sub(r'\s+', '-', id_text)
    # 移除多余的短横线
    id_text = re.sub(r'-+', '-', id_text)
    # 移除开头和结尾的短横线
    return id_text.strip('-')

def generate_toc(markdown_text: str, max_level: int = 3) -> str:
    """
    生成目录
    
    Args:
        markdown_text: Markdown文本
        max_level: 最大标题级别
        
    Returns:
        目录Markdown文本
    """
    headings = extract_headings(markdown_text)
    toc_lines = ["# 目录\n"]
    
    for level, text, heading_id in headings:
        if level <= max_level:
            indent = "  " * (level - 1)
            toc_lines.append(f"{indent}- [{text}](#{heading_id})")
    
    return "\n".join(toc_lines)

def generate_navigation(markdown_text: str, max_level: int = 3) -> List[Dict[str, Any]]:
    """
    生成导航数据
    
    Args:
        markdown_text: Markdown文本
        max_level: 最大标题级别
        
    Returns:
        导航数据
    """
    headings = extract_headings(markdown_text)
    navigation = []
    stack = [navigation]  # 用于构建嵌套结构
    
    for level, text, heading_id in headings:
        if level <= max_level:
            # 创建导航项
            nav_item = {
                "title": text,
                "id": heading_id,
                "children": []
            }
            
            # 确保stack足够长以支持当前级别
            while len(stack) <= level:
                if not stack[-1]:  # 如果最后一级是空列表
                    stack[-1].append({"title": "未命名", "id": "unnamed", "children": []})
                stack.append(stack[-1][-1]["children"])
            
            # 移除超出当前级别的栈项
            stack = stack[:level+1]
            
            # 添加到当前级别
            stack[level].append(nav_item)
    
    return navigation

def add_heading_ids(markdown_text: str) -> str:
    """
    为Markdown标题添加ID
    
    Args:
        markdown_text: Markdown文本
        
    Returns:
        添加了ID的Markdown文本
    """
    heading_pattern = r'^(#{1,6})\s+(.+?)(?:\s+\{#([^}]+)\})?$'
    lines = markdown_text.split('\n')
    
    for i, line in enumerate(lines):
        match = re.match(heading_pattern, line)
        if match and not match.group(3):  # 如果是标题且没有ID
            level, text = match.group(1), match.group(2).strip()
            heading_id = generate_id(text)
            lines[i] = f"{level} {text} {{#{heading_id}}}"
    
    return '\n'.join(lines) 