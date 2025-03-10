import datetime
import aiosqlite
from typing import List, Tuple, Optional

from app.models import Team, TeamMember

# 数据库路径
DATABASE_PATH = "teams.db"

# 数据库初始化
async def init_db():
    async with aiosqlite.connect(DATABASE_PATH) as db:
        await db.execute("""
        CREATE TABLE IF NOT EXISTS teams (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            creator_id TEXT NOT NULL,
            creator_name TEXT NOT NULL,
            start_time TEXT NOT NULL,
            created_at TEXT NOT NULL,
            group_id TEXT,
            server TEXT CHECK(server IN ('日服', '台服', '国际服', '国服')) NOT NULL
        )
        """)
        
        await db.execute("""
        CREATE TABLE IF NOT EXISTS team_members (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            team_id INTEGER NOT NULL,
            qq_id TEXT NOT NULL,
            nickname TEXT NOT NULL,
            FOREIGN KEY (team_id) REFERENCES teams (id) ON DELETE CASCADE
        )
        """)
        
        await db.commit()

# 获取所有队伍
async def get_all_teams() -> List[Team]:
    async with aiosqlite.connect(DATABASE_PATH) as db:
        db.row_factory = aiosqlite.Row
        teams = []
        
        # 获取所有队伍
        cursor = await db.execute("SELECT * FROM teams ORDER BY id")
        team_rows = await cursor.fetchall()
        
        for team_row in team_rows:
            # 获取队伍成员
            member_cursor = await db.execute(
                "SELECT qq_id, nickname FROM team_members WHERE team_id = ?", 
                (team_row['id'],)
            )
            member_rows = await member_cursor.fetchall()
            members = [TeamMember(qq_id=m['qq_id'], nickname=m['nickname']) for m in member_rows]
            
            team = Team(
                id=team_row['id'],
                creator_id=team_row['creator_id'],
                creator_name=team_row['creator_name'],
                start_time=team_row['start_time'],
                created_at=team_row['created_at'],
                group_id=team_row['group_id'],
                server=team_row['server'],
                members=members
            )
            teams.append(team)
            
        return teams

# 获取指定队伍
async def get_team(team_id: int) -> Optional[Team]:
    async with aiosqlite.connect(DATABASE_PATH) as db:
        db.row_factory = aiosqlite.Row
        
        # 获取队伍信息
        cursor = await db.execute("SELECT * FROM teams WHERE id = ?", (team_id,))
        team_row = await cursor.fetchone()
        
        if not team_row:
            return None
        
        # 获取队伍成员
        member_cursor = await db.execute(
            "SELECT qq_id, nickname FROM team_members WHERE team_id = ?", 
            (team_id,)
        )
        member_rows = await member_cursor.fetchall()
        members = [TeamMember(qq_id=m['qq_id'], nickname=m['nickname']) for m in member_rows]
        
        team = Team(
            id=team_row['id'],
            creator_id=team_row['creator_id'],
            creator_name=team_row['creator_name'],
            start_time=team_row['start_time'],
            created_at=team_row['created_at'],
            group_id=team_row['group_id'],
            server=team_row['server'],
            members=members
        )
        
        return team

# 创建队伍
async def create_team(team: Team) -> int:
    current_time = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    
    async with aiosqlite.connect(DATABASE_PATH) as db:
        # 创建队伍
        cursor = await db.execute(
            "INSERT INTO teams (creator_id, creator_name, start_time, created_at, group_id, server) VALUES (?, ?, ?, ?, ?, ?)",
            (team.creator_id, team.creator_name, team.start_time, current_time, team.group_id, team.server)
        )
        # Ensure lastrowid is not None before returning
        if cursor.lastrowid is None:
            raise ValueError("Failed to create team: no ID was generated")
            
        team_id = cursor.lastrowid
        
        # 添加创建者作为第一个成员
        await db.execute(
            "INSERT INTO team_members (team_id, qq_id, nickname) VALUES (?, ?, ?)",
            (team_id, team.creator_id, team.creator_name)
        )
        
        await db.commit()
        return team_id

# 加入队伍
async def join_team(team_id: int, member: TeamMember) -> Tuple[bool, str]:
    async with aiosqlite.connect(DATABASE_PATH) as db:
        # 检查队伍是否存在
        cursor = await db.execute("SELECT id FROM teams WHERE id = ?", (team_id,))
        team = await cursor.fetchone()
        if not team:
            return False, "队伍不存在"
        
        # 检查成员是否已经在队伍中
        cursor = await db.execute(
            "SELECT id FROM team_members WHERE team_id = ? AND qq_id = ?", 
            (team_id, member.qq_id)
        )
        existing_member = await cursor.fetchone()
        if existing_member:
            return False, "你已经在队伍中了"
        
        # 检查队伍是否已满
        cursor = await db.execute(
            "SELECT COUNT(*) FROM team_members WHERE team_id = ?", 
            (team_id,)
        )
        count_row = await cursor.fetchone()
        # Check if count_row exists and has a valid value
        if count_row and count_row[0] >= 5:
            return False, "队伍已满"
        
        # 添加成员
        await db.execute(
            "INSERT INTO team_members (team_id, qq_id, nickname) VALUES (?, ?, ?)",
            (team_id, member.qq_id, member.nickname)
        )
        
        await db.commit()
        return True, "加入成功"

# 删除队伍
async def delete_team(team_id: int, user_id: str) -> Tuple[bool, str]:
    async with aiosqlite.connect(DATABASE_PATH) as db:
        # 检查队伍是否存在
        cursor = await db.execute("SELECT creator_id FROM teams WHERE id = ?", (team_id,))
        team = await cursor.fetchone()
        if not team:
            return False, "队伍不存在"
        
        # 检查是否是创建者
        if team[0] != user_id:
            return False, "只有创建者可以删除队伍"
        
        # 删除队伍
        await db.execute("DELETE FROM teams WHERE id = ?", (team_id,))
        await db.commit()
        return True, "删除成功"

# 删除过期队伍
async def delete_expired_teams():
    current_time = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    async with aiosqlite.connect(DATABASE_PATH) as db:
        await db.execute("DELETE FROM teams WHERE start_time < ?", (current_time,))
        await db.commit()
    print(f"[{current_time}] 已删除过期队伍")

# 获取即将开始的队伍
async def get_upcoming_teams(start_time: str, end_time: str) -> List[dict]:
    async with aiosqlite.connect(DATABASE_PATH) as db:
        db.row_factory = aiosqlite.Row
        
        # 获取即将开始的队伍
        cursor = await db.execute(
            "SELECT * FROM teams WHERE start_time BETWEEN ? AND ?", 
            (start_time, end_time)
        )
        team_rows = await cursor.fetchall()
        
        teams = []
        for team_row in team_rows:
            # 获取队伍成员
            member_cursor = await db.execute(
                "SELECT qq_id, nickname FROM team_members WHERE team_id = ?",
                (team_row['id'],)
            )
            member_rows = await member_cursor.fetchall()
            members = [{'qq_id': m['qq_id'], 'nickname': m['nickname']} for m in member_rows]
            
            team = {
                'id': team_row['id'],
                'creator_id': team_row['creator_id'],
                'creator_name': team_row['creator_name'],
                'start_time': team_row['start_time'],
                'created_at': team_row['created_at'],
                'group_id': team_row['group_id'],
                'server': team_row['server'],
                'members': members
            }
            teams.append(team)
            
        return teams

# 获取队伍成员
async def get_team_members(team_id: int) -> List[dict]:
    async with aiosqlite.connect(DATABASE_PATH) as db:
        db.row_factory = aiosqlite.Row
        
        cursor = await db.execute(
            "SELECT qq_id, nickname FROM team_members WHERE team_id = ?", 
            (team_id,)
        )
        members = await cursor.fetchall()
        return [dict(member) for member in members]

# 退出队伍
async def leave_team(team_id: int, user_id: str) -> Tuple[bool, str]:
    async with aiosqlite.connect(DATABASE_PATH) as db:
        # 检查队伍是否存在
        cursor = await db.execute("SELECT id FROM teams WHERE id = ?", (team_id,))
        team = await cursor.fetchone()
        if not team:
            return False, "队伍不存在"
        
        # 检查用户是否在队伍中
        cursor = await db.execute(
            "SELECT id FROM team_members WHERE team_id = ? AND qq_id = ?", 
            (team_id, user_id)
        )
        member = await cursor.fetchone()
        if not member:
            return False, "你不在这个队伍中"
        
        # 检查是否是创建者
        cursor = await db.execute("SELECT creator_id FROM teams WHERE id = ?", (team_id,))
        team_info = await cursor.fetchone()
        if team_info and team_info[0] == user_id:
            return False, "创建者不能退出队伍，请使用删除命令"
        
        # 删除成员
        await db.execute(
            "DELETE FROM team_members WHERE team_id = ? AND qq_id = ?",
            (team_id, user_id)
        )
        
        await db.commit()
        return True, "退出成功"

# 删除指定队伍
async def delete_team_by_id(team_id: int):
    async with aiosqlite.connect(DATABASE_PATH) as db:
        await db.execute("DELETE FROM teams WHERE id = ?", (team_id,))
        await db.commit()