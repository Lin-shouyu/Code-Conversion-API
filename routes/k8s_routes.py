from fastapi import APIRouter, HTTPException
from fastapi.responses import JSONResponse
from models.k8s_models import K8sBuildRunRequest
from services.k8s_service import build_run_gke

router = APIRouter()

@router.post("/build_run")
async def build_run_endpoint(request: K8sBuildRunRequest):
    """
    傳入程式碼與建置參數後，透過 GKE 建構容器並執行，最後回傳程式輸出（Pod 日誌）。
    """
    try:
        result = await build_run_gke(request)
        response = JSONResponse(content=result)
        response.headers["Cache-Control"] = "no-cache, no-store, must-revalidate"
        return response
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
