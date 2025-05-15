"""向量操作工具"""

import os
import numpy as np
try:
    import faiss
except ImportError:
    print("FAISS库未安装，请运行: pip install faiss-cpu 或 faiss-gpu")

class VectorStore:
    """简单的向量数据库实现"""
    
    def __init__(self, dimension: int = 768, index_type: str = "Flat"):
        """
        初始化向量存储
        
        Args:
            dimension: 向量维度
            index_type: FAISS索引类型
        """
        self.dimension = dimension
        self.index_type = index_type
        self.index = None
        self.texts = []
        self.metadata = []
    
    def create_index(self):
        """创建FAISS索引"""
        if self.index_type == "Flat":
            self.index = faiss.IndexFlatL2(self.dimension)
        elif self.index_type == "IVF":
            # IVF索引需要训练
            quantizer = faiss.IndexFlatL2(self.dimension)
            self.index = faiss.IndexIVFFlat(quantizer, self.dimension, 100)
        else:
            raise ValueError(f"不支持的索引类型: {self.index_type}")
    
    def add_texts(self, texts, vectors, metadata=None):
        """
        添加文本和向量到存储
        
        Args:
            texts: 文本列表
            vectors: 向量数组
            metadata: 元数据列表
        """
        if self.index is None:
            self.create_index()
        
        if metadata is None:
            metadata = [{} for _ in texts]
            
        # 将向量转换为numpy数组
        vectors_np = np.array(vectors).astype('float32')
        
        # 如果是IVF索引，需要先训练
        if self.index_type == "IVF" and not self.index.is_trained:
            self.index.train(vectors_np)
        
        # 添加向量到索引
        self.index.add(vectors_np)
        
        # 存储文本和元数据
        self.texts.extend(texts)
        self.metadata.extend(metadata)
    
    def search(self, query_vector, top_k=5):
        """
        搜索最相似的向量
        
        Args:
            query_vector: 查询向量
            top_k: 返回最相似的数量
            
        Returns:
            (距离列表, 索引列表)
        """
        if self.index is None or len(self.texts) == 0:
            return [], []
        
        # 将查询向量转换为numpy数组
        query_np = np.array([query_vector]).astype('float32')
        
        # 搜索
        distances, indices = self.index.search(query_np, min(top_k, len(self.texts)))
        
        # 获取结果
        results = []
        for i, idx in enumerate(indices[0]):
            if idx < len(self.texts):
                results.append({
                    "text": self.texts[idx],
                    "distance": float(distances[0][i]),
                    "metadata": self.metadata[idx]
                })
        
        return results
    
    def save(self, path: str):
        """保存索引到文件"""
        if self.index is None:
            return
        
        os.makedirs(os.path.dirname(path), exist_ok=True)
        
        # 保存FAISS索引
        faiss.write_index(self.index, f"{path}.index")
        
        # 保存文本和元数据
        import pickle
        with open(f"{path}.pkl", "wb") as f:
            pickle.dump((self.texts, self.metadata), f)
    
    def load(self, path: str):
        """从文件加载索引"""
        # 加载FAISS索引
        self.index = faiss.read_index(f"{path}.index")
        
        # 加载文本和元数据
        import pickle
        with open(f"{path}.pkl", "rb") as f:
            self.texts, self.metadata = pickle.load(f) 