import os

from langchain_openai import ChatOpenAI

def DeepSeekV3():
    return ChatOpenAI(
        model= "deepseek-chat",
        api_key= os.environ.get("deepseek"),
        base_url="https://api.deepseek.com",
    )

def Tongyi():
    return ChatOpenAI(
        model="qwen-max",
        api_key=os.environ.get("dashscope"),  # 自行搞定  你的秘钥
        base_url="https://dashscope.aliyuncs.com/compatible-mode/v1"
    )

def DeepSeekR1():
    return ChatOpenAI(
        model= "deepseek-reasoner",
        api_key= os.environ.get("deepseek"),
        base_url="https://api.deepseek.com",
    )