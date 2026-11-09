import os, json, re, threading, time
import discord
from discord.ext import commands
from discord import app_commands
from flask import Flask

app = Flask(__name__)
@app.route('/')
def home(): return "NEXUS REACT is online!"
threading.Thread(target=lambda: app.run(host='0.0.0.0', port=10000), daemon=True).start()

OWNER_ID = os.getenv('OWNER_ID', '')
OWNER_USERNAME = os.getenv('OWNER_USERNAME', '@owner')
RECOVERY_KEY = os.getenv('RECOVERY_KEY', 'change-me')

DB_FILE = 'db.json'
db = {"premium": {}, "autoreactChannel": {}, "autoreactUser": {}, "tagreact": {}, "presets": {}, "autoreactEnabled": True}
if os.path.exists(DB_FILE):
    try: db.update(json.load(open(DB_FILE)))
    except: pass
def save():
    json.dump(db, open(DB_FILE, 'w'), indent=2)

def is_owner(id): return str(id) == str(OWNER_ID)
def has_premium(id):
    return is_owner(id) or (str(id) in db.get("premium", {}) and db["premium"][str(id)] > time.time()*1000)
def premium_msg(): return f"❌ PREMIUM only! DM {OWNER_USERNAME} to buy 👑"
def owner_msg(): return f"❌ Only the Owner can do this. DM {OWNER_USERNAME} for coins / premium."

def parse_time(s):
    m = re.match(r"^(\d+)(s|mo|m|h|d|y)$", s.lower())
    if not m: return None
    mp = {"s":1000,"m":60000,"h":3600000,"d":86400000,"mo":2592000000,"y":31536000000}
    return int(m.group(1)) * mp[m.group(2)]

intents = discord.Intents.default()
intents.message_content = True
intents.guilds = True
intents.guild_messages = True
intents.guild_reactions = True

bot = commands.Bot(command_prefix="!", intents=intents)

@bot.event
async def on_ready():
    try: await bot.tree.sync()
    except Exception as e: print("SYNC FAIL:", e)
    print(f"✅ NEXUS REACT logged in as {bot.user}")

@bot.event
async def on_message(message):
    if message.author.bot: return
    if not db.get("autoreactEnabled", True): return
    for uid, emojis in db.get("tagreact", {}).items():
        if any(str(u.id) == uid for u in message.mentions.users):
            for e in emojis:
                try: await message.add_reaction(e)
                except: pass
    for e in db.get("autoreactChannel", {}).get(str(message.channel.id), []):
        try: await message.add_reaction(e)
        except: pass
    for e in db.get("autoreactUser", {}).get(str(message.author.id), []):
        try: await message.add_reaction(e)
        except: pass

@bot.tree.command(name="premium", description="Give premium to a user (Owner only)")
async def premium_cmd(interaction: discord.Interaction, user: discord.Member, time: str):
    if not is_owner(interaction.user.id): return await interaction.response.send_message(owner_msg(), ephemeral=True)
    ms = parse_time(time)
    if not ms: return await interaction.response.send_message("Bad time. Use 30s / 10m / 2h / 7d / 1mo / 1y", ephemeral=True)
    db["premium"][str(user.id)] = time.time()*1000 + ms
    save()
    await interaction.response.send_message(f"✅ {user.mention} got PREMIUM for {time} 👑")

@bot.tree.command(name="remove-premium", description="Remove premium (Owner only)")
async def remove_premium_cmd(interaction: discord.Interaction, user: discord.Member):
    if not is_owner(interaction.user.id): return await interaction.response.send_message(owner_msg(), ephemeral=True)
    db["premium"].pop(str(user.id), None); save()
    await interaction.response.send_message(f"✅ Removed PREMIUM from {user.mention}")

@bot.tree.command(name="premium-check", description="Check if user has premium")
async def premium_check_cmd(interaction: discord.Interaction, user: discord.Member = None):
    target = user or interaction.user
    await interaction.response.send_message(f"✅ {target.mention} has PREMIUM 👑" if has_premium(target.id) else f"❌ {target.mention} has NO premium", ephemeral=True)

@bot.tree.command(name="react", description="React to a message by link")
async def react_cmd(interaction: discord.Interaction, link: str, emojis: str):
    emoji_list = emojis.split()
    if not has_premium(interaction.user.id) and len(emoji_list) > 3: return await interaction.response.send_message(premium_msg(), ephemeral=True)
    if has_premium(interaction.user.id) and len(emoji_list) > 20: return await interaction.response.send_message("Max 20 emojis", ephemeral=True)
    m = re.search(r"channels\/\d+\/(\d+)\/(\d+)", link)
    if not m: return await interaction.response.send_message("Bad message link", ephemeral=True)
    try:
        ch = await bot.fetch_channel(int(m.group(1)))
        msg = await ch.fetch_message(int(m.group(2)))
        for e in emoji_list:
            try: await msg.add_reaction(e)
            except: pass
        await interaction.response.send_message(f"✅ Reacted with {len(emoji_list)} emojis")
    except: await interaction.response.send_message("❌ Could not find that message. Bot must be in that server.", ephemeral=True)

@bot.tree.command(name="autoreact-add-channel", description="Auto-react in a channel (Premium)")
async def ar_add_ch(interaction: discord.Interaction, channel: discord.TextChannel, emojis: str):
    if not has_premium(interaction.user.id): return await interaction.response.send_message(premium_msg(), ephemeral=True)
    db["autoreactChannel"][str(channel.id)] = emojis.split(); save()
    await interaction.response.send_message(f"✅ Autoreact added for {channel.mention}: {emojis}")

@bot.tree.command(name="autoreact-add-user", description="Auto-react to a user (Premium)")
async def ar_add_user(interaction: discord.Interaction, user: discord.Member, emojis: str):
    if not has_premium(interaction.user.id): return await interaction.response.send_message(premium_msg(), ephemeral=True)
    db["autoreactUser"][str(user.id)] = emojis.split(); save()
    await interaction.response.send_message(f"✅ Autoreact added for {user.mention}: {emojis}")

@bot.tree.command(name="autoreact-remove", description="Remove autoreact")
async def ar_remove(interaction: discord.Interaction, channel: discord.TextChannel = None, user: discord.Member = None):
    if channel: db["autoreactChannel"].pop(str(channel.id), None)
    if user: db["autoreactUser"].pop(str(user.id), None)
    save(); await interaction.response.send_message("✅ Autoreact removed")

@bot.tree.command(name="autoreact-list", description="List your autoreact")
async def ar_list(interaction: discord.Interaction):
    await interaction.response.send_message(f"**Autoreact:**\nChannels: {db.get('autoreactChannel')}\nUsers: {db.get('autoreactUser')}", ephemeral=True)

@bot.tree.command(name="autoreact-toggle", description="Turn autoreact on/off")
@app_commands.choices(state=[app_commands.Choice(name="on", value="on"), app_commands.Choice(name="off", value="off")])
async def ar_toggle(interaction: discord.Interaction, state: app_commands.Choice[str]):
    db["autoreactEnabled"] = state.value == "on"; save()
    await interaction.response.send_message(f"✅ Autoreact {state.value}")

@bot.tree.command(name="react-all", description="React to last 10 messages (Premium)")
async def react_all(interaction: discord.Interaction, emojis: str):
    if not has_premium(interaction.user.id): return await interaction.response.send_message(premium_msg(), ephemeral=True)
    await interaction.response.defer()
    msgs = [m async for m in interaction.channel.history(limit=10)]
    for m in msgs:
        for e in emojis.split():
            try: await m.add_reaction(e)
            except: pass
    await interaction.followup.send("✅ Reacted to last 10 messages")

@bot.tree.command(name="react-boost", description="Boost your last message (Premium)")
async def react_boost(interaction: discord.Interaction):
    if not has_premium(interaction.user.id): return await interaction.response.send_message(premium_msg(), ephemeral=True)
    emojis = db.get("tagreact", {}).get(str(interaction.user.id), ["🔥","👑","💎"])
    await interaction.response.defer()
    msgs = [m async for m in interaction.channel.history(limit=20)]
    last = next((m for m in msgs if m.author.id == interaction.user.id), None)
    if last:
        for e in emojis:
            try: await last.add_reaction(e)
            except: pass
    await interaction.followup.send("✅ Boosted your last message")

@bot.tree.command(name="tagreact-on", description="Turn tag react on (Premium)")
async def tag_on(interaction: discord.Interaction, emojis: str):
    if not has_premium(interaction.user.id): return await interaction.response.send_message(premium_msg(), ephemeral=True)
    db["tagreact"][str(interaction.user.id)] = emojis.split(); save()
    await interaction.response.send_message(f"✅ TAG REACT ON: {emojis} - When anyone tags you, bot will react 👑")

@bot.tree.command(name="tagreact-set", description="Update tag react emojis")
async def tag_set(interaction: discord.Interaction, emojis: str):
    db["tagreact"][str(interaction.user.id)] = emojis.split(); save()
    await interaction.response.send_message(f"✅ Tag react updated: {emojis}")

@bot.tree.command(name="tagreact-off", description="Turn tag react off")
async def tag_off(interaction: discord.Interaction):
    db["tagreact"].pop(str(interaction.user.id), None); save()
    await interaction.response.send_message("✅ Tag react OFF")

@bot.tree.command(name="tagreact-list", description="See your tag react")
async def tag_list(interaction: discord.Interaction):
    e = db.get("tagreact", {}).get(str(interaction.user.id))
    await interaction.response.send_message(f"Your tag react: {' '.join(e)}" if e else "No tag react set. Use /tagreact-on 👑 🔥 💎", ephemeral=True)

@bot.tree.command(name="claim-owner", description="Claim owner with recovery key")
async def claim_owner(interaction: discord.Interaction, key: str):
    global OWNER_ID
    if key == RECOVERY_KEY:
        OWNER_ID = str(interaction.user.id)
        await interaction.response.send_message("✅ You are now the Owner! Update OWNER_ID in Render too.", ephemeral=True)
    else: await interaction.response.send_message("❌ Wrong key", ephemeral=True)

TOKEN = os.getenv('DISCORD_TOKEN')
print('TOKEN CHECK - length:', len(TOKEN) if TOKEN else 'MISSING')
bot.run(TOKEN.strip() if TOKEN else '')
