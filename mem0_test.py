from mem0 import Memory

config = {
     "vector_store": {
        "provider": "pgvector",
        "config": {
            "user": "pgvector",
            "password": "pgvector",
            "host": "192.168.30.144",
            "port": "5434",
            "embedding_model_dims":768,
            "dbname":"mem0_memory"
        }
    },
    "llm": {
        "provider": "ollama",
        "config": {
            "model": "qwen3:1.7b",
            "temperature": 0,
            "max_tokens": 2000,
            "ollama_base_url": "http://localhost:11434",  # Ensure this URL is correct
        },
    },
    "embedder": {
        "provider": "ollama",
        "config": {
            "model": "nomic-embed-text:v1.5",
            "ollama_base_url": "http://localhost:11434",
            "embedding_dims":768
    },
    },
}

print("初始化 Memory...")
m = Memory.from_config(config)

print("添加 Memory...")
messages = [
    {"role": "user", "content": "Hi, I'm Hollis. I love Coding and Gaming."},
    {"role": "assistant", "content": "Hey Hollis! I'll remember your interests."}
]

# 检查 add 是否返回结果或报错
result = m.add(messages, user_id="Hollis666")
print("Add result:", result)

print("查询 Memory...")
results = m.search("What do you know about me?", filters={"user_id": "Hollis666"})
print(results)