from fastapi import FastAPI, HTTPException, Request
import json
import httpx
import asyncio

from app.models import QQMessage, TeamMember, Team
from app.database import get_all_teams, get_team, join_team, delete_team, create_team, delete_team_by_id, leave_team

# 创建FastAPI应用
app = FastAPI(title="QQ车队机器人")

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
    if not message.message.startswith("车队"):
        return {"status": "ignored", "reason": "not a team command"}
    
    # 去掉前缀
    command = message.message[2:].strip()
    
    # 处理命令
    response = ""
    
    # 帮助命令
    if not command:
        response = "车队命令帮助：\n"
        response += "- 车队 查询：列出所有发布的队伍\n"
        response += "- 车队 加入 [序号]：加入指定的队伍\n"
        response += "- 车队 查询 [序号]：列出这个队伍的当前加入人\n"
        response += "- 车队 删除 [序号]：删除该队伍\n"
        response += "- 车队 创建 [服务器] [开始时间]：创建一个新队伍，时间格式为'小时:分钟'\n"
        response += "- 车队 退出 [序号]：退出指定的队伍\n"
    
    # 查询所有队伍
    elif command == "查询":
        teams = await get_all_teams()
        if not teams:
            response = "当前没有队伍"
        else:
            response = "当前队伍列表：\n"
            for team in teams:
                response += f"[{team.id}] {team.creator_name} [{len(team.members)}/5] {team.start_time} [{team.server}]\n"
    
    # 查询指定队伍
    elif command.startswith("查询 "):
        try:
            team_id = int(command[3:].strip())
            team = await get_team(team_id)
            if not team:
                response = f"队伍 {team_id} 不存在"
            else:
                response = f"队伍 {team_id} 成员列表：\n"
                for i, member in enumerate(team.members, 1):
                    response += f"{i}. {member.nickname}\n"
                response += f"开始时间: {team.start_time}"
        except ValueError:
            response = "请输入正确的队伍序号"
    
    # 加入队伍
    elif command.startswith("加入 "):
        try:
            team_id = int(command[3:].strip())
            member = TeamMember(qq_id=message.user_id, nickname=message.sender.get("nickname", f"用户{message.user_id}"))
            success, msg = await join_team(team_id, member)
            response = msg
        except ValueError:
            response = "请输入正确的队伍序号"
    
    # 删除队伍
    elif command.startswith("删除 "):
        try:
            team_id = int(command[3:].strip())
            success, msg = await delete_team(team_id, message.user_id)
            response = msg
        except ValueError:
            response = "请输入正确的队伍序号"
    
    # 创建队伍
    elif command.startswith("创建 "):
        try:
            params = command[3:].strip().split()
            if len(params) < 2:
                response = "请输入正确的格式：车队 创建 [服务器] [开始时间]，例如：车队 创建 日服 20:30"
                return {"status": "error", "message": response, "group_id": message.group_id}
            
            server = params[0]
            time_input = params[1]
            
            # 验证服务器参数
            if server not in ["日服", "台服", "国际服", "国服"]:
                response = "服务器只能是'日服'、'台服'、'国际服'或'国服'"
                return {"status": "error", "message": response, "group_id": message.group_id}
            # 检查是否为简化的时间格式 (HH:MM)
            import datetime
            import re
            
            # 使用正则表达式匹配HH:MM格式
            if re.match(r'^([0-1]?[0-9]|2[0-3]):([0-5][0-9])$', time_input):
                # 如果是简化格式，添加当天日期
                today = datetime.datetime.now().strftime("%Y-%m-%d")
                start_time = f"{today} {time_input}:00"
            else:
                # 尝试完整格式解析
                start_time = time_input
                datetime.datetime.strptime(start_time, "%Y-%m-%d %H:%M:%S")
            
            # 创建队伍
            team = Team(
                creator_id=message.user_id,
                creator_name=message.sender.get("nickname", f"用户{message.user_id}"),
                start_time=start_time,
                members=[],  # 初始化空成员列表
                group_id=message.group_id,  # 存储群ID以便后续通知
                server=server  # 设置服务器信息
            )
            team_id = await create_team(team)
            response = f"队伍创建成功，序号为 {team_id}"
        except ValueError:
            response = "请输入正确的时间格式，例如：20:30 或 2023-11-01 20:00:00"
    
    # 退出队伍
    elif command.startswith("退出 "):
        try:
            team_id = int(command[3:].strip())
            success, msg = await leave_team(team_id, message.user_id)
            response = msg
        except ValueError:
            response = "请输入正确的队伍序号"
    
    # 未知命令
    else:
        response = "未知命令，请输入'车队'查看帮助"
    
    # 发送响应消息到群
    if response:
        await send_group_message(message.group_id, response)
    
    # 构建返回消息
    return {
        "status": "ok",
        "message": response,
        "group_id": message.group_id
    }

# 发送群消息的函数（调用go-cqhttp的API）
async def send_group_message(group_id: str, message: str) -> bool:
    # 使用异步HTTP客户端
    # 设置go-cqhttp的API基础URL
    base_send_url = "http://127.0.0.1:3000"  # 默认地址，可根据实际配置修改
    
    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            # 发送POST请求到go-cqhttp的API
            response = await client.post(
                f"{base_send_url}/send_group_msg", 
                json={
                    "group_id": int(group_id) if group_id.isdigit() else group_id,  # 确保group_id格式正确
                    "message": message
                }
            )
            
            # 检查响应状态
            response.raise_for_status()
            result = response.json()
            
            if result.get("status") == "ok" or result.get("retcode") == 0:
                print(f"成功发送群消息到 {group_id}: {message}")
                return True
            else:
                print(f"发送群消息失败: {result}")
                return False
    except (httpx.RequestError, httpx.HTTPStatusError) as e:
        print(f"发送群消息时发生错误: {str(e)}")
        return False
    except Exception as e:
        print(f"发送群消息时发生未知错误: {str(e)}")
        return False