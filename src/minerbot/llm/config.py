"""LLM 配置模型"""
from pydantic import BaseModel, Field, field_validator
from typing import Optional
import os


class LLMConfig(BaseModel):
    """LLM 配置模型"""
    
    model_name: str = Field(..., description="格式: provider/model-name")
    api_key: Optional[str] = Field(default=None, description="API Key")
    base_url: Optional[str] = Field(default=None, description="自定义端点")
    temperature: float = Field(default=0.7, ge=0.0, le=2.0)
    max_tokens: Optional[int] = Field(default=None, ge=1)
    timeout: Optional[int] = Field(default=60, ge=1)
    
    @field_validator("model_name")
    @classmethod
    def validate_model_name(cls, v: str) -> str:
        """验证 model_name 格式"""
        if "/" not in v:
            raise ValueError(
                f"model_name 格式错误，应为 'provider/model-name'，当前: {v}"
            )
        return v
    
    def get_provider(self) -> str:
        """从 model_name 自动解析提供商名称"""
        return self.model_name.split("/")[0].lower()
    
    def get_model(self) -> str:
        """从 model_name 提取模型名称"""
        return "/".join(self.model_name.split("/")[1:])
    
    def get_api_key(self, default_env_var: str) -> str:
        """获取 API Key，优先：配置文件值 > 环境变量"""
        if self.api_key:
            # 支持 $ENV_VAR 格式
            if self.api_key.startswith("$"):
                env_name = self.api_key[1:]
                key = os.getenv(env_name)
                if key:
                    return key
                raise ValueError(f"API Key 环境变量 {env_name} 未设置")
            return self.api_key
        # 回退到默认环境变量
        key = os.getenv(default_env_var)
        if key:
            return key
        raise ValueError(f"API Key 未配置，请设置环境变量 {default_env_var}")
    
    class Config:
        frozen = True
