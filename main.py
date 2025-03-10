import uvicorn

from routes import app
from team_submitter.database import init_db
from team_submitter.scheduler import init_scheduler

# 主函数
if __name__ == "__main__":
    # 在应用启动时初始化数据库和调度器
    @app.on_event("startup")
    async def startup_event():
        # 初始化数据库
        await init_db()
        
        # 初始化并启动调度器
        init_scheduler()
    
    # 启动FastAPI应用
    uvicorn.run(app, host="0.0.0.0", port=5120)