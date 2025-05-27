"""文本处理工具"""

def split_text(text: str, max_length: int = 1000, overlap: int = 100):
    """
    将文本分割成重叠的块
    
    Args:
        text: 需要分割的文本
        max_length: 每个块的最大长度
        overlap: 块之间的重叠长度
    
    Returns:
        分割后的文本块列表
    """
    if not text or len(text) <= max_length:
        return [text] if text else []
    
    chunks = []
    start = 0
    
    while start < len(text):
        end = min(start + max_length, len(text))
        
        # 如果不是最后一块并且末尾不是句子结束，则尝试找到句子结束点
        if end < len(text):
            # 尝试在句子结尾处截断
            sentence_end_chars = ['.', '!', '?', '\n\n']
            for char in sentence_end_chars:
                last_pos = text[start:end].rfind(char)
                if last_pos > 0:  # 找到了句子结束点
                    end = start + last_pos + 1
                    break
        
        chunks.append(text[start:end])
        start = end - overlap if end - overlap > start else start + 1
    
    return chunks

def extract_code_blocks(markdown_text: str):
    """
    从Markdown文本中提取代码块
    
    Args:
        markdown_text: Markdown格式的文本
        
    Returns:
        提取的代码块列表，每个元素是(代码块内容, 语言)的元组
    """
    # 简单实现，实际可能需要更复杂的正则表达式
    code_blocks = []
    lines = markdown_text.split('\n')
    in_code_block = False
    current_block = []
    current_language = ""
    
    for line in lines:
        if line.startswith("```"):
            if in_code_block:
                # 结束代码块
                in_code_block = False
                if current_block:
                    code_blocks.append(('\n'.join(current_block), current_language))
                current_block = []
                current_language = ""
            else:
                # 开始代码块
                in_code_block = True
                current_language = line[3:].strip()
        elif in_code_block:
            current_block.append(line)
    
    return code_blocks

def clean_text(text: str):
    """
    清理文本，去除不必要的标记和空白
    
    Args:
        text: 需要清理的文本
        
    Returns:
        清理后的文本
    """
    # 简单实现，可以根据需要添加更多清理规则
    # 去除多余空白
    text = ' '.join(text.split())
    # 去除HTML标签（简单实现）
    # 实际项目中可能需要使用BeautifulSoup等库进行更完整的处理
    text = text.replace('<br>', ' ').replace('<p>', ' ').replace('</p>', ' ')
    
    return text 