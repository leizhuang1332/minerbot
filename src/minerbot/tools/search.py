"""Tavily 搜索工具"""
from langchain_core.tools import tool
from tavily import TavilyClient


@tool
def search_web(query: str, max_results: int = 5) -> str:
    """搜索互联网信息
    
    Args:
        query: 搜索关键词
        max_results: 返回结果数量 (默认5)
    
    Returns:
        搜索结果摘要
    """
    client = TavilyClient(api_key="")
    results = client.search(
        query=query,
        max_results=max_results,
        include_answer=True,
        include_raw_content=False,
    )
    
    if not results.get("results"):
        return "未找到相关结果"
    
    output = []
    for i, item in enumerate(results["results"][:max_results], 1):
        output.append(f"{i}. {item.get('title', 'Untitled')}")
        output.append(f"   {item.get('url', '')}")
        content = item.get('content', '')
        output.append(f"   {content[:200]}..." if len(content) > 200 else f"   {content}")
        output.append("")
    
    return "\n".join(output)


def create_search_tool(api_key: str):
    """创建配置好 API key 的搜索工具
    
    Args:
        api_key: Tavily API key
        
    Returns:
        配置好的 search_web 工具
    """
    return search_web
