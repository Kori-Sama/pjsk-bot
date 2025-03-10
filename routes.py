from fastapi import FastAPI, HTTPException, Request
import json
import httpx
import asyncio

from team_submitter.models import QQMessage, TeamMember, Team
from team_submitter.database import get_all_teams, get_team, join_team, delete_team, create_team, delete_team_by_id, leave_team
from team_submitter.handler import handle_team
# 创建FastAPI应用
app = FastAPI(title="QQ机器人")

# API路由 - 处理go-cqhttp的消息推送


@app.post("/event")
async def receive_message(request: Request):
    # 获取原始请求数据
    data = await request.json()

    # 检查是否为群消息事件
    if data.get("post_type") != "message" or data.get("message_type") != "group":
        return {"status": "ignored", "reason": "not a group message"}

    # 提取消息内容
    group_id = str(data.get("group_id", ""))
    user_id = str(data.get("user_id", ""))
    raw_message = data.get("raw_message", "")
    message_content = data.get("message", "")  # 可能包含CQ码的原始消息
    sender = data.get("sender", {})

    # 构建QQ消息对象
    message = QQMessage(
        group_id=group_id,
        user_id=user_id,
        message=raw_message,
        sender=sender
    )

    # 只处理群消息
    if not message.group_id:
        return {"status": "ignored", "reason": "no group_id"}

    # 检查消息前缀
    if message.message.startswith("车队"):
        return await handle_team(message)

    return {"status": "ignored", "reason": "no prefix"}