import os
import asyncio
from aiohttp import web
import discord
from discord import app_commands
from openai import OpenAI

# ==================== 1. 环境变量读取 ====================
DISCORD_BOT_TOKEN = os.environ.get("DISCORD_BOT_TOKEN")
DEEPSEEK_API_KEY = os.environ.get("DEEPSEEK_API_KEY")

if not DISCORD_BOT_TOKEN or not DEEPSEEK_API_KEY:
    print("❌ 错误：未找到 DISCORD_BOT_TOKEN 或 DEEPSEEK_API_KEY 环境变量！")
    exit(1)

# ==================== 2. 初始化客户端 ====================
ai_client = OpenAI(
    api_key=DEEPSEEK_API_KEY,
    base_url="https://api.deepseek.com"
)

intents = discord.Intents.default()
bot_client = discord.Client(intents=intents)
tree = app_commands.CommandTree(bot_client)

# ==================== 3. 伪造 Web 服务（Render 保持活跃） ====================
async def handle_ping(request):
    return web.Response(text="Sender Bot is live!")

async def start_dummy_web_server():
    app = web.Application()
    app.router.add_get("/", handle_ping)
    runner = web.AppRunner(app)
    await runner.setup()
    
    port = int(os.environ.get("PORT", 10000))
    site = web.TCPSite(runner, "0.0.0.0", port)
    await site.start()
    print(f"🌐 伪造 Web 服务已启动，端口: {port}")

# ==================== 4. 注册 /send 发送指令 ====================
@tree.command(name="send", description="输入中文（含网络俚语），翻译为指定语言并发送")
@app_commands.describe(
    target_lang="选择目标语种",
    text="输入中文内容（支持游戏黑话、拼音缩写及网络梗）",
    show_original="是否附带中文原文（默认不附带）"
)
@app_commands.choices(target_lang=[
    app_commands.Choice(name="🇻🇳 越南语 (Vietnamese)", value="越南语"),
    app_commands.Choice(name="🇺🇸 英语 (English)", value="英语"),
    app_commands.Choice(name="🇯🇵 日语 (Japanese)", value="日语"),
    app_commands.Choice(name="🇰🇷 韩语 (Korean)", value="韩语"),
    app_commands.Choice(name="🇹🇭 泰语 (Thai)", value="泰语"),
    app_commands.Choice(name="🇷🇺 俄语 (Russian)", value="俄语"),
    app_commands.Choice(name="🇪🇸 西班牙语 (Spanish)", value="西班牙语")
])
@app_commands.allowed_contexts(guilds=True, dms=True, private_channels=True)
@app_commands.allowed_installs(guilds=True, users=True)
async def send_translated(
    interaction: discord.Interaction, 
    target_lang: app_commands.Choice[str], 
    text: str,
    show_original: bool = False
):
    await interaction.response.defer(ephemeral=False)

    try:
        system_prompt = (
            f"你是一名精通中文互联网文化、游戏黑话及各国外语口语的同传专家。\n"
            f"【输入源语言设定】：用户输入的内容一律视为【现代中文】（包含但不限于游戏黑话、拼音缩写、网络梗、俚语、贴吧/抽象话或口头方言）。\n"
            f"【核心任务】：透彻理解中文背后的真实情绪、暗语及实际语义，将其意译并转换为【{target_lang.value}】中本土玩家/网民日常最地道、最常用的对应表达，切忌生硬直译。\n"
            f"【输出规范】：仅输出最终的【{target_lang.value}】译文，严禁包含任何中文解释、注音、括号说明或多余符号。"
        )

        response = ai_client.chat.completions.create(
            model="deepseek-v4-flash",
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": text}
            ],
            temperature=0.3
        )

        translated_text = response.choices[0].message.content.strip()

        if show_original:
            final_message = f"{translated_text}\n*(原文: {text})*"
        else:
            final_message = translated_text

        await interaction.followup.send(final_message)

    except Exception as e:
        await interaction.followup.send(f"❌ 发送失败：`{str(e)}`", ephemeral=True)

# ==================== 5. 启动事件 ====================
@bot_client.event
async def on_ready():
    bot_client.loop.create_task(start_dummy_web_server())
    await tree.sync()
    print(f"🚀 发送机器人登录成功：{bot_client.user}，指令同步完成！")

# ==================== 6. 运行 ====================
if __name__ == "__main__":
    bot_client.run(DISCORD_BOT_TOKEN)