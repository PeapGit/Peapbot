import os
import random
import csv
from datetime import datetime, timezone
from typing import Optional, Dict
import json
import discord
from discord import app_commands
from discord.ext import commands

BASEDIR = os.path.dirname(__file__)
TOKEN = os.path.join(BASEDIR, "token.txt")
intents = discord.Intents.default()
bot = commands.Bot(command_prefix="!", intents=intents)
intents.message_content = True
intents.members = True
intents.presences = True
saas_file = os.path.join(BASEDIR, "saas.txt")
stats_file = os.path.join(BASEDIR, "stats.json")
lastquote = None
UptimeBots = [
    1460403784709570753,
    1510504061630156800,
    1510407584161726554,
    1331837521725886534
]
uptime_data: Dict[int, Dict[str, float]] = {}
bot_last_change_time: Dict[int, float] = {}
bot_last_status: Dict[int, discord.Status] = {}
duckbotrolling = False



if os.path.exists(stats_file):
    with open(os.path.join(stats_file), "r", encoding="utf-8") as f:
        commands_run = json.loads(f.read())

else:
    with open(os.path.join(stats_file), "w", encoding="utf-8") as f:
        commands_run = {"peap": 0, "peapfeed": 0, "quote": 0, "add_quote": 0, "uptime": 0, "stats": 0, "duckroll": 0}
        json.dump(commands_run, f)

if os.path.exists(saas_file):
    with open(saas_file, "r", encoding="utf-8") as f:
        data = json.load(f)
    saas_switch = data.get("enabled", False)
    saas_user_ids = data.get("id", [])
    saas_users = data.get("name", [])
else:
    saas_switch = False
    saas_user_ids = []
    saas_users = []


def load_uptime_data():
    uptime_path = os.path.join(BASEDIR, "uptime.csv")
    if not os.path.isfile(uptime_path):
        return

    with open(uptime_path, "r", encoding="utf-8") as f:
        reader = csv.reader(f)
        file_mtime = os.path.getmtime(uptime_path)

        for row in reader:
            if len(row) == 3:
                bot_id = int(row[0])
                uptime_data[bot_id] = {"up": float(row[1]), "down": float(row[2])}
                bot_last_change_time[bot_id] = file_mtime
                bot_last_status[bot_id] = discord.Status.online

            elif len(row) >= 6:
                if row[0] == "bot_id":
                    continue

                bot_id_str, bot_name, event_type, timestamp_str, total_up_str, total_down_str = row[:6]

                bot_id = int(bot_id_str)
                dt = datetime.fromisoformat(timestamp_str)

                uptime_data[bot_id] = {"up": float(total_up_str), "down": float(total_down_str)}
                bot_last_change_time[bot_id] = dt.timestamp()
                bot_last_status[bot_id] = discord.Status.online if event_type == "ONLINE" else discord.Status.offline


with open(TOKEN, "r", encoding="utf-8") as f:
    TOKEN = f.read().strip()
if not TOKEN:
    raise RuntimeError("Discord token missing")


def format_duration(seconds: float) -> str:
    seconds = int(seconds)
    days, remainder = divmod(seconds, 86400)
    hours, remainder = divmod(remainder, 3600)
    minutes, seconds = divmod(remainder, 60)

    parts = []
    if days > 0: parts.append(f"{days}d")
    if hours > 0: parts.append(f"{hours}h")
    if minutes > 0: parts.append(f"{minutes}m")
    if seconds > 0 or not parts: parts.append(f"{seconds}s")
    return " ".join(parts)


@bot.event
async def on_ready():
    load_uptime_data()
    try:
        synced = await bot.tree.sync()
        print(f"commands synced: {len(synced)}")
        print(f"Logged in as {bot.user} id={bot.user.id}")
        await bot.change_presence(
            status=discord.Status.online,
            activity=discord.Game("exploits galore")
        )
        print("status changed")
    except Exception as e: 
        print(f"Sync failed: {e}")


@bot.tree.command(name="saas", description="Toggle SaaS mode, Peap only")
@app_commands.describe(
    enabled="Enable or disable saas",
    user="User to apply SaaS to"
)
async def saas(interaction: discord.Interaction, enabled: bool, user: Optional[discord.User] = None, ):
    if interaction.user.id != 769374081991835659:
        await interaction.response.send_message(
            "Your not allowed to use this. You'd better pray to god peap doesn't activate this. dw about it I won't activate this, unless I have an extremely valid reason.",
            ephemeral=True)
        return

    global saas_switch, saas_users, saas_user_ids

    if user is None:
        await interaction.response.send_message("Choose a user to apply saas", ephemeral=True)
        return

    saas_switch = enabled
    if user.id not in saas_user_ids:
        saas_user_ids.append(user.id)
        saas_users.append(user.name)

    data = {
        "enabled": saas_switch,
        "id": saas_user_ids,
        "name": saas_users,
    }
    with open(os.path.join(BASEDIR, "saas.txt"), "w", encoding="utf-8") as f:
        json.dump(data, f)
        
    await interaction.response.send_message(f"SaaS mode {'enabled' if enabled else 'disabled'}. Added {user.name}.", ephemeral=True)


async def saas_check(interaction: discord.Interaction):
    global saas_switch, saas_user_ids
    if saas_switch:
        if interaction.user.id in saas_user_ids:
            await error(interaction, "SAAS - " + interaction.user.id)
            return True
    return False


@bot.tree.command(name="peap", description="Peaper")
async def peap(interaction: discord.Interaction):
    if await saas_check(interaction):
        return
    await interaction.response.send_message(content="peap")
    await stats_insert("peap")


@bot.tree.command(name="peapfeed", description="Feed Peap")
async def peapfeed(interaction: discord.Interaction):
    global duckbotrolling

    if await saas_check(interaction):
        return

    if duckbotrolling:
        duckbotrolling = False

        await interaction.response.send_message(
            content="haha fuck you duck bot im better I got fed first!!!! LOL also tasty oil")

    else:
        await interaction.response.send_message(content="mmmm tasty oil")

    await stats_insert("peapfeed")


@bot.tree.command(name="quote", description="Send a random quote from the server!")
@app_commands.describe(user="User to get the quote from", include_id="Snowflake ID not implemented as of this moment")
async def quote(
        interaction: discord.Interaction,
        user: Optional[discord.User] = None,
        include_id: Optional[bool] = False,
):
    if await saas_check(interaction):
        return

    with open(os.path.join(BASEDIR, "quotes.json"), "r", encoding="utf-8") as f:
        quotes = json.loads(f.read())

    if user is not None:
        author_messages = [msg for msg in quotes if user.id in msg["authors"]]
        if len(author_messages) < 1:
            await interaction.response.send_message(f"No quotes found for {user.name}", ephemeral=True)
            return

        randommsg = random.choice(author_messages)
        text = randommsg["text"]
        if isinstance(text, list):
            text = " ".join(text)
        if len(text) > 4080:
            text = text[:4080] + "..."
        id = randommsg["message_id"]
        timestamp = randommsg["timestamp"]

        quoteEmbed = discord.Embed(
            description=f"## **{text}**",
            color=discord.Color.random(),
            timestamp=datetime.fromtimestamp(timestamp, tz=timezone.utc),
        )

        quoteEmbed.set_author(name=f"Quote from {user.name}", icon_url=user.display_avatar.url)
        quoteEmbed.set_footer(text=f"ID: {id}")
        await interaction.response.send_message(embed=quoteEmbed)
        return

    randommsg = random.choice(quotes)
    text = randommsg["text"]
    if isinstance(text, list):
        text = " ".join(text)
    if len(text) > 4080:
        text = text[:4080] + "..."
    id = randommsg["message_id"]
    timestamp = randommsg["timestamp"]
    author_id = randommsg["authors"][0]

    quoteEmbed = discord.Embed(
        description=f"## **{text}**",
        color=discord.Color.random(),
        timestamp=datetime.fromtimestamp(timestamp, tz=timezone.utc),
    )

    member = await bot.fetch_user(author_id)

    if member:
        quoteEmbed.set_author(name=f"Quote from {member.name}", icon_url=member.display_avatar.url)
    else:
        quoteEmbed.set_author(name="Quote from Unknown User")

    quoteEmbed.set_footer(text=f"ID: {id}")
    await stats_insert("quote")
    await interaction.response.send_message(embed=quoteEmbed)
    return


@app_commands.checks.cooldown(1, 3.0)
@bot.tree.context_menu(name="Add a quote")
async def add_quote(interaction: discord.Interaction, message: discord.Message):
    global lastquote

    if await saas_check(interaction):
        return

    if lastquote == message.content:
        print("Repeat detected")
        await interaction.response.send_message(content="You can't add the same quote", ephemeral=True)
        return

    if message.author.bot:
        print("Bot detected")
        await interaction.response.send_message(content="Bots are not allowed")
        return


    try:
        messageuser = await interaction.channel.fetch_message(message.id)
    except Exception as e:
        await error(interaction, e)
        return

    servers = [
        1502143252143276042,
        1276099166522572832
    ]

    if messageuser.guild.id not in servers:
        print(f"Interaction User: {messageuser.author} (ID: {messageuser.author.id})")
        print(f"Interaction User Display Name: {messageuser.author.display_name}")
        print(f"Interaction Guild: {messageuser.guild} (ID: {messageuser.guild.id})")
        print(f"Interaction Channel: {messageuser.channel} (ID: {messageuser.channel.id})")
        print(f"Target Message Content: {messageuser.content}")
        print(f"Target Message Author: {messageuser.author} (ID: {messageuser.author.id})")
        print(f"Target Message Author Display Name: {messageuser.author.display_name}")
        print(f"Target Message ID: {messageuser.id}")
        print(f"Target Message Timestamp: {messageuser.created_at}")
        await error(interaction, "SERVER NOT ALLOWED")
        return

    with open(os.path.join(BASEDIR, "quotes.json"), "r", encoding="utf-8") as f:
        quotes = json.loads(f.read())

    quotes.append({
        "text": [messageuser.content],
        "authors": [messageuser.author.id],
        "timestamp": discord.utils.snowflake_time(messageuser.id).timestamp(),
        "message_id": messageuser.id,
    })

    with open(os.path.join(BASEDIR, "quotes.json"), "w", encoding="utf-8") as f:
        json.dump(quotes, f, indent=4)

    lastquote = message.content



    # Heck ton of logging for exploitation logging
    print(f"Interaction User: {messageuser.author} (ID: {messageuser.author.id})")
    print(f"Interaction User Display Name: {messageuser.author.display_name}")
    print(f"Interaction Guild: {messageuser.guild} (ID: {messageuser.guild.id})")
    print(f"Interaction Channel: {messageuser.channel} (ID: {messageuser.channel.id})")
    print(f"Target Message Content: {messageuser.content}")
    print(f"Target Message Author: {messageuser.author} (ID: {messageuser.author.id})")
    print(f"Target Message Author Display Name: {messageuser.author.display_name}")
    print(f"Target Message ID: {messageuser.id}")
    print(f"Target Message Timestamp: {messageuser.created_at}")

    await stats_insert("add_quote")

    await interaction.response.send_message("Quote added", ephemeral=True)


@bot.tree.command(name="uptime", description="Bot's uptime stats")
@app_commands.describe(user="Bot to fetch uptime for", detailed="Show detailed stats")
async def uptime(
        interaction: discord.Interaction,
        user: Optional[discord.User] = None,
        detailed: bool = False,
):
    if await saas_check(interaction):
        return

    await interaction.response.defer()

    if user is None:
        embed = discord.Embed(title="Uptime", color=discord.Color.blue())
        for bot_id in UptimeBots:

            up_seconds, down_seconds, percent = get_bot_uptime_stats(bot_id)

            val = f"{percent:g}%"
            if detailed:
                val += f"\n**Up:** {format_duration(up_seconds)}\n**Down:** {format_duration(down_seconds)}"
            bot_user = await bot.fetch_user(bot_id)
            name = bot_user.name
            embed.add_field(name=name, value=val, inline=False)

        await interaction.followup.send(embed=embed)
        return

    if user.id not in UptimeBots:
        await interaction.followup.send("Not tracking that bot.", ephemeral=True)
        return

    up_seconds, down_seconds, percent = get_bot_uptime_stats(user.id)

    val = f"{percent:g}%"
    if detailed:
        val += f"\n**Up:** {format_duration(up_seconds)}\n**Down:** {format_duration(down_seconds)}"

    embed = discord.Embed(title=f"Uptime for {user.name}", color=discord.Color.green())
    embed.add_field(name="Stats", value=val, inline=False)

    await stats_insert("uptime")

    await interaction.followup.send(embed=embed)


def get_bot_uptime_stats(bot_id: int) -> tuple[float, float, float]:
    totals = uptime_data.get(bot_id, {"up": 0.0, "down": 0.0})
    up_seconds = totals["up"]
    down_seconds = totals["down"]

    last_change = bot_last_change_time.get(bot_id)
    last_status = bot_last_status.get(bot_id)
    now_ts = datetime.now(tz=timezone.utc).timestamp()

    if last_change and last_status:
        duration_last_event = now_ts - last_change
        if last_status == discord.Status.offline:
            down_seconds += duration_last_event
        else:
            up_seconds += duration_last_event

    total_seconds = up_seconds + down_seconds
    if total_seconds > 0:
        percent = (up_seconds / total_seconds) * 100.0
    else:
        percent = 100.0 if down_seconds == 0 else 0.0

    return up_seconds, down_seconds, percent


@bot.event
async def on_presence_update(before: discord.Member, after: discord.Member):
    if after.id in UptimeBots:
        now_ts = datetime.now(tz=timezone.utc).timestamp()

        if before.status != after.status:
            last_change = bot_last_change_time.get(after.id)

            if after.id not in uptime_data:
                uptime_data[after.id] = {"up": 0.0, "down": 0.0}

            if last_change:
                duration_spent = now_ts - last_change
                if before.status == discord.Status.online:
                    uptime_data[after.id]["up"] += duration_spent
                else:
                    uptime_data[after.id]["down"] += duration_spent

            bot_last_change_time[after.id] = now_ts
            bot_last_status[after.id] = after.status
            event_type = "ONLINE" if after.status == discord.Status.online else "OFFLINE"
            uptime_path = os.path.join(BASEDIR, "uptime.csv")
            file_status = os.path.isfile(uptime_path)

            with open(uptime_path, "a", encoding="utf-8", newline="") as f:
                writer = csv.writer(f)
                if not file_status:
                    writer.writerow(["bot_id", "bot_name", "event_type", "timestamp_utc", "total_up", "total_down"])

                writer.writerow([
                    str(after.id),
                    after.name,
                    event_type,
                    datetime.now(tz=timezone.utc).isoformat(),
                    uptime_data[after.id]["up"],
                    uptime_data[after.id]["down"]
                ])


@bot.event
async def on_message(message: discord.Message):
    global duckbotrolling

    if message.author.id == 1510407584161726554:
        if "im hungry... feed me with /duckfeed" in message.content.lower():
            duckbotrolling = True
    await bot.process_commands(message)


async def stats_insert(command):
    global commands_run
    commands_run[command] += 1
    with open(stats_file, "w") as file:
        json.dump(commands_run, file, indent=4)


@bot.tree.command(name="stats", description="peap bot stats!")
async def stats(interaction: discord.Interaction):
    global commands_run

    quoteEmbed = discord.Embed(
        description=f"## **Stats for the Peap Bot**",
        color=discord.Color.random(),
    )

    total = commands_run["peap"] + commands_run["quote"] + commands_run["stats"] + commands_run["duckroll"] + commands_run["uptime"] + commands_run["peapfeed"]

    quoteEmbed.add_field(name="Total number of commands Run on Peap bot", value=total, inline=False)
    quoteEmbed.add_field(name="Peap", value=commands_run["peap"], inline=False)
    quoteEmbed.add_field(name="Quotes Added", value=commands_run["add_quote"], inline=False)
    quoteEmbed.add_field(name="Ducks Rolled", value=commands_run["duckroll"], inline=False)
    quoteEmbed.add_field(name="Uptime", value=commands_run["uptime"], inline=False)
    quoteEmbed.add_field(name="Quote", value=commands_run["quote"], inline=False)
    quoteEmbed.add_field(name="Peapfeed", value=commands_run["peapfeed"], inline=False)
    quoteEmbed.add_field(name="Stats", value=commands_run["stats"], inline=False)

    await interaction.response.send_message(embed=quoteEmbed)

    await stats_insert("stats")


@bot.tree.command(name="duckroll", description="ducking")
async def duckroll(interaction: discord.Interaction):
    await interaction.response.send_message(file=discord.File("/var/www/html/duck.png")) # https://peap.me/duck.png
    await stats_insert("duckroll")

async def error(interaction: discord.Interaction, code):

    print("Error code: " + code)
    await interaction.response.send_message(content="Peap bot is working fine! Your not worthy tho.")



bot.run(TOKEN)

