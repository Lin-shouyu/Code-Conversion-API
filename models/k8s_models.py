from pydantic import BaseModel
from typing import Optional

class K8sBuildRunRequest(BaseModel):
    language: str                   # 例如 "java" 或 "python"
    code: str                       # 傳入完整的程式碼內容
    deployment_name: str            # 用於命名 Docker 映像與 Kubernetes Job
    dockerfile_path: Optional[str] = "./Dockerfile"  # Dockerfile 路徑
    context_path: Optional[str] = "."               # Docker build 的上下文路徑
