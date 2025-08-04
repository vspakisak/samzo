import os
import threading
import asyncio
import random
import json
from datetime import datetime

import discord
from discord.ext import commands
from flask import Flask

# Flask app for uptime
app = Flask(__name__)

@app.route('/')
def home():
    return '✅ Bot is alive!', 200

def run_flask():
    port = int(os.environ.get("PORT", 8080))
    app.run(host='0.0.0.0', port=port)

# Discord bot setup
intents = discord.Intents.default()
intents.message_content = True
intents.members = True

bot = commands.Bot(command_prefix='!', intents=intents)
warnings = {}
economy = {}

@bot.event
async def on_ready():
    print(f"{bot.user} is now online!")
    await bot.change_presence(activity=discord.Game(name="!help for commands"))

@bot.event
async def on_command_error(ctx, error):
    if isinstance(error, commands.MissingPermissions):
        await ctx.send("❌ You don't have permission to use this command!")
    elif isinstance(error, commands.MissingRequiredArgument):
        await ctx.send("❌ Missing required arguments! Check `!help <command>` for usage.")
    elif isinstance(error, commands.CommandNotFound):
        await ctx.send("❌ Command not found! Use `!help` to see available commands.")

@bot.command(name='kick')
@commands.has_permissions(kick_members=True)
async def kick(ctx, member: discord.Member, *, reason="No reason provided"):
    await member.kick(reason=reason)
    embed = discord.Embed(title="Member Kicked", color=0xff6b6b)
    embed.add_field(name="Member", value=member.mention, inline=True)
    embed.add_field(name="Reason", value=reason, inline=True)
    embed.add_field(name="Moderator", value=ctx.author.mention, inline=True)
    await ctx.send(embed=embed)

@bot.command(name='ban')
@commands.has_permissions(ban_members=True)
async def ban(ctx, member: discord.Member, *, reason="No reason provided"):
    await member.ban(reason=reason)
    embed = discord.Embed(title="Member Banned", color=0xff4757)
    embed.add_field(name="Member", value=member.mention, inline=True)
    embed.add_field(name="Reason", value=reason, inline=True)
    embed.add_field(name="Moderator", value=ctx.author.mention, inline=True)
    await ctx.send(embed=embed)

@bot.command(name='mute')
@commands.has_permissions(manage_messages=True)
async def mute(ctx, member: discord.Member, time: int = 10, *, reason="No reason provided"):
    mute_role = discord.utils.get(ctx.guild.roles, name="Muted")
    if not mute_role:
        mute_role = await ctx.guild.create_role(name="Muted")
        for channel in ctx.guild.channels:
            await channel.set_permissions(mute_role, send_messages=False, speak=False)
    await member.add_roles(mute_role, reason=reason)
    embed = discord.Embed(title="Member Muted", color=0xffa502)
    embed.add_field(name="Member", value=member.mention, inline=True)
    embed.add_field(name="Duration", value=f"{time} minutes", inline=True)
    embed.add_field(name="Reason", value=reason, inline=True)
    await ctx.send(embed=embed)
    await asyncio.sleep(time * 60)
    await member.remove_roles(mute_role, reason="Mute expired")
    await ctx.send(f"🔊 {member.mention} has been unmuted!")

@bot.command(name='warn')
@commands.has_permissions(manage_messages=True)
async def warn(ctx, member: discord.Member, *, reason="No reason provided"):
    user_id = str(member.id)
    if user_id not in warnings:
        warnings[user_id] = []
    warnings[user_id].append({
        'reason': reason,
        'moderator': str(ctx.author),
        'date': datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    })
    embed = discord.Embed(title="Member Warned", color=0xf39c12)
    embed.add_field(name="Member", value=member.mention, inline=True)
    embed.add_field(name="Warning Count", value=len(warnings[user_id]), inline=True)
    embed.add_field(name="Reason", value=reason, inline=False)
    await ctx.send(embed=embed)

@bot.command(name='warnings')
async def check_warnings(ctx, member: discord.Member = None):
    if member is None:
        member = ctx.author
    user_id = str(member.id)
    user_warnings = warnings.get(user_id, [])
    if not user_warnings:
        await ctx.send(f"{member.mention} has no warnings!")
        return
    embed = discord.Embed(title=f"Warnings for {member.display_name}", color=0xe74c3c)
    for i, warning in enumerate(user_warnings, 1):
        embed.add_field(
            name=f"Warning {i}",
            value=f"**Reason:** {warning['reason']}\n**Moderator:** {warning['moderator']}\n**Date:** {warning['date']}",
            inline=False
        )
    await ctx.send(embed=embed)

@bot.command(name='clear')
@commands.has_permissions(manage_messages=True)
async def clear(ctx, amount: int = 10):
    if amount > 100:
        await ctx.send("❌ Cannot delete more than 100 messages at once!")
        return
    deleted = await ctx.channel.purge(limit=amount + 1)
    await ctx.send(f"🗑️ Deleted {len(deleted) - 1} messages!", delete_after=3)

@bot.command(name='userinfo')
async def userinfo(ctx, member: discord.Member = None):
    if member is None:
        member = ctx.author
    embed = discord.Embed(title=f"User Info: {member.display_name}", color=0x3498db)
    embed.set_thumbnail(url=member.avatar.url if member.avatar else member.default_avatar.url)
    embed.add_field(name="Username", value=f"{member.name}#{member.discriminator}", inline=True)
    embed.add_field(name="ID", value=member.id, inline=True)
    embed.add_field(name="Status", value=str(member.status).title(), inline=True)
    embed.add_field(name="Joined Server", value=member.joined_at.strftime('%Y-%m-%d'), inline=True)
    embed.add_field(name="Account Created", value=member.created_at.strftime('%Y-%m-%d'), inline=True)
    embed.add_field(name="Roles", value=len(member.roles) - 1, inline=True)
    await ctx.send(embed=embed)

@bot.command(name='serverinfo')
async def serverinfo(ctx):
    guild = ctx.guild
    embed = discord.Embed(title=f"Server Info: {guild.name}", color=0x2ecc71)
    embed.set_thumbnail(url=guild.icon.url if guild.icon else None)
    embed.add_field(name="Owner", value=guild.owner.mention, inline=True)
    embed.add_field(name="Members", value=guild.member_count, inline=True)
    embed.add_field(name="Channels", value=len(guild.channels), inline=True)
    embed.add_field(name="Roles", value=len(guild.roles), inline=True)
    embed.add_field(name="Created", value=guild.created_at.strftime('%Y-%m-%d'), inline=True)
    embed.add_field(name="Verification Level", value=str(guild.verification_level).title(), inline=True)
    await ctx.send(embed=embed)

@bot.command(name='avatar')
async def avatar(ctx, member: discord.Member = None):
    if member is None:
        member = ctx.author
    embed = discord.Embed(title=f"{member.display_name}'s Avatar", color=0x9b59b6)
    embed.set_image(url=member.avatar.url if member.avatar else member.default_avatar.url)
    await ctx.send(embed=embed)

@bot.command(name='ping')
async def ping(ctx):
    latency = round(bot.latency * 1000)
    embed = discord.Embed(title="🏓 Pong!", description=f"Latency: {latency}ms", color=0x1abc9c)
    await ctx.send(embed=embed)

@bot.command(name='roll')
async def roll_dice(ctx, dice: str = "1d6"):
    try:
        rolls, limit = map(int, dice.split('d'))
        if rolls > 10 or limit > 100:
            await ctx.send("❌ Too many rolls or dice size too large!")
            return
        results = [random.randint(1, limit) for _ in range(rolls)]
        total = sum(results)
        embed = discord.Embed(title="🎲 Dice Roll", color=0xe67e22)
        embed.add_field(name="Dice", value=dice, inline=True)
        embed.add_field(name="Results", value=', '.join(map(str, results)), inline=True)
        embed.add_field(name="Total", value=total, inline=True)
        await ctx.send(embed=embed)
    except ValueError:
        await ctx.send("❌ Invalid dice format! Use format like `2d20` or `1d6`")

@bot.command(name='coinflip')
async def coinflip(ctx):
    result = random.choice(['Heads', 'Tails'])
    embed = discord.Embed(title="🪙 Coin Flip", description=f"Result: **{result}**", color=0xf1c40f)
    await ctx.send(embed=embed)

@bot.command(name='8ball')
async def magic_8ball(ctx, *, question):
    responses = [
        "It is certain", "Without a doubt", "Yes definitely", "You may rely on it",
        "As I see it, yes", "Most likely", "Outlook good", "Yes", "Signs point to yes",
        "Reply hazy, try again", "Ask again later", "Better not tell you now",
        "Cannot predict now", "Concentrate and ask again", "Don't count on it",
        "My reply is no", "My sources say no", "Outlook not so good", "Very doubtful"
    ]
    embed = discord.Embed(title="🎱 Magic 8 Ball", color=0x9b59b6)
    embed.add_field(name="Question", value=question, inline=False)
    embed.add_field(name="Answer", value=random.choice(responses), inline=False)
    await ctx.send(embed=embed)

@bot.command(name='choose')
async def choose(ctx, *, choices):
    options = [choice.strip() for choice in choices.split(',')]
    if len(options) < 2:
        await ctx.send("❌ Please provide at least 2 choices separated by commas!")
        return
    chosen = random.choice(options)
    embed = discord.Embed(title="🤔 Choice Made", color=0x3498db)
    embed.add_field(name="Options", value=', '.join(options), inline=False)
    embed.add_field(name="I Choose", value=f"**{chosen}**", inline=False)
    await ctx.send(embed=embed)

@bot.command(name='balance')
async def balance(ctx, member: discord.Member = None):
    if member is None:
        member = ctx.author
    user_id = str(member.id)
    coins = economy.get(user_id, 0)
    embed = discord.Embed(title="💰 Balance", color=0xf1c40f)
    embed.add_field(name="User", value=member.display_name, inline=True)
    embed.add_field(name="Coins", value=f"{coins} 🪙", inline=True)
    await ctx.send(embed=embed)

@bot.command(name='daily')
async def daily(ctx):
    user_id = str(ctx.author.id)
    daily_amount = random.randint(50, 200)
    if user_id not in economy:
        economy[user_id] = 0
    economy[user_id] += daily_amount
    embed = discord.Embed(title="🏷 Daily Reward", color=0x2ecc71)
    embed.add_field(name="Reward", value=f"{daily_amount} 🪙", inline=True)
    embed.add_field(name="New Balance", value=f"{economy[user_id]} 🪙", inline=True)
    await ctx.send(embed=embed)

@bot.command(name='give')
async def give_coins(ctx, member: discord.Member, amount: int):
    if amount <= 0:
        await ctx.send("❌ Amount must be positive!")
        return
    giver_id = str(ctx.author.id)
    receiver_id = str(member.id)
    if giver_id not in economy:
        economy[giver_id] = 0
    if receiver_id not in economy:
        economy[receiver_id] = 0
    if economy[giver_id] < amount:
        await ctx.send("❌ You don't have enough coins!")
        return
    economy[giver_id] -= amount
    economy[receiver_id] += amount
    embed = discord.Embed(title="💸 Coins Transferred", color=0x3498db)
    embed.add_field(name="From", value=ctx.author.mention, inline=True)
    embed.add_field(name="To", value=member.mention, inline=True)
    embed.add_field(name="Amount", value=f"{amount} 🪙", inline=True)
    await ctx.send(embed=embed)

@bot.command(name='join')
async def join_voice(ctx):
    if ctx.author.voice:
        channel = ctx.author.voice.channel
        await channel.connect()
        await ctx.send(f"🎵 Joined {channel.name}!")
    else:
        await ctx.send("❌ You need to be in a voice channel!")

@bot.command(name='leave')
async def leave_voice(ctx):
    if ctx.voice_client:
        await ctx.voice_client.disconnect()
        await ctx.send("👋 Left the voice channel!")
    else:
        await ctx.send("❌ I'm not in a voice channel!")

if __name__ == '__main__':
    threading.Thread(target=run_flask).start()
    TOKEN = os.environ.get("DISCORD_BOT_TOKEN")
    if not TOKEN:
        print("❌ ERROR: DISCORD_BOT_TOKEN environment variable not set.")
    else:
        bot.run(TOKEN)
