import os
import asyncio
import subprocess

# 從環境變數取得 GCP 與 GKE 相關設定（請根據環境調整）
PROJECT_ID = os.getenv("GCP_PROJECT_ID", "your-project-id")
CLUSTER_NAME = os.getenv("GKE_CLUSTER_NAME", "your-gke-cluster")
ZONE = os.getenv("GKE_ZONE", "us-central1-a")

async def build_run_gke(request) -> dict:
    """
    依序完成：
      1. 寫入程式碼至檔案
      2. 建置並推送 Docker 映像檔
      3. 取得 GKE 認證並建立 Kubernetes Job
      4. 等待 Job 完成並取得 Pod 日誌
    回傳執行輸出與相關資訊。
    """
    # 1. 將程式碼寫入檔案（依語言決定副檔名）
    ext = ".java" if request.language.lower() == "java" else ".py"
    code_file_name = f"{request.deployment_name}{ext}"
    with open(code_file_name, "w", encoding="utf-8") as f:
        f.write(request.code)
    
    # 2. 建置 Docker 映像檔與推送到 GCR
    new_image_tag = f"gcr.io/{PROJECT_ID}/{request.deployment_name}:latest"
    build_cmd = [
        "docker", "build",
        "-f", request.dockerfile_path,
        "-t", new_image_tag,
        request.context_path
    ]
    build_result = subprocess.run(build_cmd, capture_output=True, text=True)
    if build_result.returncode != 0:
        raise Exception(f"Docker build failed: {build_result.stderr}")
    
    push_cmd = ["docker", "push", new_image_tag]
    push_result = subprocess.run(push_cmd, capture_output=True, text=True)
    if push_result.returncode != 0:
        raise Exception(f"Docker push failed: {push_result.stderr}")
    
    # 3. 取得 GKE 叢集認證
    get_creds_cmd = [
        "gcloud", "container", "clusters", "get-credentials", CLUSTER_NAME,
        "--zone", ZONE,
        "--project", PROJECT_ID
    ]
    creds_result = subprocess.run(get_creds_cmd, capture_output=True, text=True)
    if creds_result.returncode != 0:
        raise Exception(f"gcloud get-credentials failed: {creds_result.stderr}")
    
    # 4. 建立 Kubernetes Job（使用 Job 可在執行完畢後自動結束，便於取得輸出）
    job_name = f"{request.deployment_name}-job"
    job_yaml = f"""
apiVersion: batch/v1
kind: Job
metadata:
  name: {job_name}
spec:
  template:
    spec:
      containers:
      - name: {request.deployment_name}
        image: {new_image_tag}
      restartPolicy: Never
  backoffLimit: 0
    """
    # 將 YAML 寫入暫存檔
    yaml_file = f"{job_name}.yaml"
    with open(yaml_file, "w", encoding="utf-8") as f:
        f.write(job_yaml)
    
    # 4.1 使用 kubectl 建立 Job
    apply_cmd = ["kubectl", "apply", "-f", yaml_file]
    apply_result = subprocess.run(apply_cmd, capture_output=True, text=True)
    if apply_result.returncode != 0:
        raise Exception(f"kubectl apply failed: {apply_result.stderr}")
    
    # 4.2 等待 Job 執行完成（這裡設定 timeout 為 120 秒，可依需求調整）
    wait_cmd = ["kubectl", "wait", "--for=condition=complete", f"job/{job_name}", "--timeout=120s"]
    wait_result = subprocess.run(wait_cmd, capture_output=True, text=True)
    if wait_result.returncode != 0:
        raise Exception(f"kubectl wait failed: {wait_result.stderr}")
    
    # 4.3 取得執行此 Job 的 Pod 名稱（假設 Job 只有一個 Pod）
    get_pod_cmd = [
        "kubectl", "get", "pods",
        "-l", f"job-name={job_name}",
        "-o", "jsonpath={.items[0].metadata.name}"
    ]
    pod_result = subprocess.run(get_pod_cmd, capture_output=True, text=True)
    if pod_result.returncode != 0:
        raise Exception(f"kubectl get pods failed: {pod_result.stderr}")
    pod_name = pod_result.stdout.strip()
    
    # 4.4 取得該 Pod 的日誌，也就是程式的輸出
    logs_cmd = ["kubectl", "logs", pod_name]
    logs_result = subprocess.run(logs_cmd, capture_output=True, text=True)
    if logs_result.returncode != 0:
        raise Exception(f"kubectl logs failed: {logs_result.stderr}")
    logs = logs_result.stdout
    
    # 4.5 清理：刪除 Job 以釋放資源（根據需求可保留或自動刪除）
    delete_cmd = ["kubectl", "delete", "job", job_name]
    subprocess.run(delete_cmd, capture_output=True, text=True)
    
    return {
        "job_name": job_name,
        "pod_name": pod_name,
        "logs": logs,
        "message": "Container built, job executed, and output retrieved successfully"
    }
