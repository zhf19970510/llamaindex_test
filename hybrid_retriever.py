import os
import re
from llama_index.core import VectorStoreIndex, Document
from llama_index.core.retrievers import VectorIndexRetriever
from llama_index.core.retrievers.fusion_retriever import QueryFusionRetriever
from llama_index.embeddings.dashscope import DashScopeEmbedding
from llama_index.llms.dashscope import DashScope
from llama_index.core import Settings
from llama_index.core.node_parser import SentenceSplitter
from llama_index.core.schema import NodeWithScore
from llama_index.core.schema import QueryBundle
from rank_bm25 import BM25Okapi
import jieba

# 设置 DashScope API Key
DASHSCOPE_API_KEY = "sk-45fb8cf0a3a449d89ca8ce6551e798b0"  # 改成你自己的

# ===== 构造文档 - 科技公司产品和服务描述 =====
texts = [
    "花为CloudEngine 16800数据中心交换机采用自主研发的AI芯片，支持智能运维和预测性维护，适用于大型企业和云服务提供商。该产品在2023年获得全球数据中心网络设备市场份额第一。",
    "HuaWei Cloud提供包括弹性计算、存储、数据库平台在内的全栈云服务，特别在AI和大数据领域有深厚积累。华为云在亚太地区的市场份额持续增长。",
    "阿里巴巴的云计算平台阿里云是国内市场份额最大的云服务提供商，其核心产品包括ECS弹性计算、OSS对象存储和RDS关系数据库。阿里云在电商和大数据处理方面有独特优势。",
    "阿里巴巴达摩院在人工智能、量子计算和芯片设计等多个前沿领域进行基础研究，其开发的通义千问大语言模型在中文理解方面表现优异。",
    "腾讯云在游戏云、社交娱乐云服务方面具有领先地位，为《王者荣耀》《和平精英》等大型游戏提供稳定的云服务支持。腾讯云音视频解决方案在行业内广泛使用。",
    "腾讯的微信支付和支付宝是中国两大移动支付平台，其中微信支付依托微信社交生态，在个人转账和小额支付场景中占据优势。",
    "字节跳动的推荐算法是其核心竞争力，抖音和今日头条的内容推荐系统能够实现高度个性化，用户粘性极高。",
    "字节跳动火山引擎提供AI中台和数据中台解决方案，帮助企业构建智能化运营体系，其A/B测试平台在互联网行业广泛使用。",
    "百度的自动驾驶平台Apollo是国内最成熟的自动驾驶解决方案之一，已在多个城市开展Robotaxi商业化运营。",
    "百度的文心一言大模型在中文创作和逻辑推理方面表现突出，特别是在处理中国传统文化相关内容时具有优势。",
    "小米的IoT平台连接了超过5亿台智能设备，构建了全球最大的消费级AIoT生态，其小爱同学AI助手月活跃用户超过1亿。",
    "小米手机采用高通和联发科芯片，但在影像处理芯片和充电芯片方面有自研成果，澎湃系列芯片已应用于多款产品。",
]

docs = [Document(text=t) for t in texts]

# 分块
splitter = SentenceSplitter(chunk_size=120, chunk_overlap=20)
nodes = splitter.get_nodes_from_documents(docs)


# ===== 自定义 BM25 检索器 =====
def tokenize_zh(text: str):
    """中文文本分词 + 清理"""
    text = re.sub(r"[^\w\s]", "", text)  # 去除标点符号
    tokens = jieba.lcut(text)
    return [t.strip() for t in tokens if t.strip()]


# 构建 BM25 索引
corpus = [node.text for node in nodes]
tokenized_corpus = [tokenize_zh(doc) for doc in corpus]
bm25 = BM25Okapi(tokenized_corpus)


class CustomBM25Retriever:
    def __init__(self, nodes, bm25_model, similarity_top_k=3):
        self.nodes = nodes
        self.bm25 = bm25_model
        self.similarity_top_k = similarity_top_k

    def retrieve(self, str_or_query_bundle):
        # 兼容字符串和 QueryBundle
        if isinstance(str_or_query_bundle, QueryBundle):
            query_str = str_or_query_bundle.query_str
        else:
            query_str = str_or_query_bundle  # 假设是 str

        tokenized_query = tokenize_zh(query_str)
        scores = self.bm25.get_scores(tokenized_query)
        top_k_indices = sorted(
            range(len(scores)), key=lambda i: scores[i], reverse=True
        )[:self.similarity_top_k]
        results = []
        for idx in top_k_indices:
            results.append(NodeWithScore(node=self.nodes[idx], score=float(scores[idx])))
        return results

    async def aretrieve(self, str_or_query_bundle):
        return self.retrieve(str_or_query_bundle)


# ===== 稠密检索器 =====
embed_model = DashScopeEmbedding(
    model_name="text-embedding-v2",
    api_key=DASHSCOPE_API_KEY
)

Settings.llm = DashScope(
    model_name="qwen-max",
    api_key=DASHSCOPE_API_KEY
)

vector_index = VectorStoreIndex(nodes, embed_model=embed_model)
dense_retriever = VectorIndexRetriever(index=vector_index, similarity_top_k=4)

# ===== 替换稀疏检索器 =====
sparse_retriever = CustomBM25Retriever(nodes=nodes, bm25_model=bm25, similarity_top_k=4)

# ===== 混合检索器 =====
hybrid_retriever = QueryFusionRetriever(
    retrievers=[dense_retriever, sparse_retriever],
    similarity_top_k=4,
    num_queries=1,
    mode="reciprocal_rerank",
)

# ===== 查询：专门设计的问题 =====
query_str = "华为的人工智能芯片和云AI服务"

print("🔍 Query:", query_str)

print("\n=== 稠密检索结果 (语义理解) ===")
dense_nodes = dense_retriever.retrieve(query_str)
for i, node in enumerate(dense_nodes):
    print(f"{i + 1}. Score: {node.score:.4f}")
    print(f"   Text: {node.text[:80]}...")

print("\n=== 稀疏检索结果 (关键词匹配) ===")
sparse_nodes = sparse_retriever.retrieve(query_str)
for i, node in enumerate(sparse_nodes):
    print(f"{i + 1}. Score: {node.score:.4f}")
    print(f"   Text: {node.text[:80]}...")

print("\n=== 混合检索结果 (语义+关键词融合) ===")
hybrid_nodes = hybrid_retriever.retrieve(query_str)
for i, node in enumerate(hybrid_nodes):
    print(f"{i + 1}. Score: {node.score:.4f}")
    print(f"   Text: {node.text[:80]}...")

