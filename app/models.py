from typing import List, Optional
from pydantic import BaseModel

# 定义数据模型
class TeamMember(BaseModel):
    qq_id: str
    nickname: str

class Team(BaseModel):
    id: Optional[int] = None
    creator_id: str
    creator_name: str
    start_time: str
    members: List[TeamMember] = []
    created_at: Optional[str] = None
    group_id: Optional[str] = None  # 添加群ID字段，用于后续通知
    server: str = "日服"  # 添加服务器字段，默认为日服

class QQMessage(BaseModel):
    group_id: str
    user_id: str
    message: str
    sender: dict