from fastapi import FastAPI
from routes.llm_routes import router as llm_router
from routes.k8s_routes import router as k8s_router

app = FastAPI(title="Python Code Version Converter API")

app.include_router(llm_router, prefix="/llm", tags=["LLM"])
app.include_router(k8s_router, prefix="/k8s", tags=["K8s"])

@app.get("/")
def home():
    return {"message": "Welcome to the API"}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="127.0.0.1", port=8000, reload=True)
