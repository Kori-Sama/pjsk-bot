import httpx

# 发送群消息的函数（调用go-cqhttp的API


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
                    # 确保group_id格式正确
                    "group_id": int(group_id) if group_id.isdigit() else group_id,
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
