import datetime
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger

from team_submitter.database import delete_expired_teams, get_upcoming_teams, get_team_members, delete_team_by_id
from utils.sender import send_group_message

# 创建调度器
scheduler = AsyncIOScheduler()

# 检查队伍开始时间并通知


async def check_team_start_times():
    current_time = datetime.datetime.now()
    # 向前后5分钟的时间范围
    start_time = (current_time - datetime.timedelta(minutes=5)
                  ).strftime("%Y-%m-%d %H:%M:%S")
    end_time = (current_time + datetime.timedelta(minutes=5)
                ).strftime("%Y-%m-%d %H:%M:%S")

    # 获取即将开始的队伍
    teams = await get_upcoming_teams(start_time, end_time)

    for team in teams:
        # 获取队伍成员
        members = await get_team_members(team['id'])

        # 构建@所有成员的消息
        at_message = f"队伍 {team['id']} 即将开始！\n"
        for member in members:
            at_message += f"[CQ:at,qq={member['qq_id']}] "

        # 调用send_group_message函数发送群消息
        print(
            f"[{datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] 准备发送通知: {at_message}")
        # 假设team中有group_id字段，如果没有，需要从其他地方获取
        if 'group_id' in team:
            success = await send_group_message(team['group_id'], at_message)
            if success:
                print(
                    f"[{datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] 成功发送通知到群 {team['group_id']}")
            else:
                print(
                    f"[{datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] 发送通知到群 {team['group_id']} 失败")
        else:
            print(
                f"[{datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] 无法发送通知: 缺少群ID信息")

        # 删除已通知的队伍
        await delete_team_by_id(team['id'])

# 初始化调度任务


def init_scheduler():
    # 每天凌晨4点删除过期队伍
    scheduler.add_job(
        delete_expired_teams,
        CronTrigger(hour=4, minute=0),
        id="delete_expired_teams"
    )

    # 每分钟检查一次队伍开始时间
    scheduler.add_job(
        check_team_start_times,
        'interval',
        minutes=1,
        id="check_team_start_times"
    )

    # 启动调度器
    scheduler.start()
