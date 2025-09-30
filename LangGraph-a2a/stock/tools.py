from langchain_core.tools import tool
import akshare as ak
from typing import Any, Literal
from pydantic import BaseModel
from llm import DeepSeek

class ResponseFormat(BaseModel):
    """Respond to the user in this format."""

    status: Literal['input_required', 'completed', 'error'] = 'input_required'
    message: str

@tool
def get_stock_info(code: str) -> str:
    """可以根据传入的股票代码获取股票信息
    Args:
        code: 股票代码
    """

    code_isempty = (code == "" or len(code) <= 2)

    if code_isempty:
        return []
    
    df = ak.stock_zh_a_spot_em() # 获取创业板股票列表

    ret = None
    if not code_isempty:
        ret = df[df['代码'].str.contains(code)]

    return ret.to_dict(orient='records')

tools = [get_stock_info, ResponseFormat]
llm = DeepSeek()
llm_with_tools = llm.bind_tools(tools)
