import os

from langchain_openai import ChatOpenAI

def DeepSeek():
    return ChatOpenAI(
        model= "deepseek-chat",
        api_key= os.environ.get("deepseek"),
        base_url="https://api.deepseek.com",
    )

def Tongyi():
    return ChatOpenAI(
        model= "qwen-max",
        api_key= os.environ.get("AliDeep"),
        base_url="https://dashscope.aliyuncs.com/compatible-mode/v1",
    )