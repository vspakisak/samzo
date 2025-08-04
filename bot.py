import discord
from discord.ext import commands
import random
import asyncio
import json
import os
from datetime import datetime, timedelta
import aiohttp
import re

from flask import Flask
from threading import Thread
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Flask app for UptimeRobot
app = Flask('')

@app.route('/')
def home():
    return "Bot is running!"

def run():
    app.run(host='0.0.0.0', port=8080)

def keep_alive():
    t = Thread(target=run)
    t.start()

# Bot configuration
intents = discord.Intents.default()
intents.message_content = True
intents.members = True

bot = commands.Bot(command_prefix='!', intents=intents)

# Store user data
warnings = {}
economy = {}
user_stats = {}

# AI Response patterns
ai_responses = {
    'greetings': [
        "Yo what's good! 🔥", "Ayy wassup! 😎", "Hey there! What's crackin'? 💪",
        "Yooo! How you doin'? 🚀", "What's poppin'! 🎉", "Heyyy! Good to see you! ✨"
    ],
    'how_are_you': [
        "I'm chillin', thanks for asking! 😄", "Living my best bot life! 🤖✨",
        "Doing great! Ready to help you out! 💯", "I'm vibing, how about you? 🎵",
        "All good in the hood! What's up? 🔥"
    ],
    'compliments': [
        "Aww thanks! You're pretty cool yourself! 😊", "You're awesome too! 🌟",
        "Thanks homie! You made my day! 💪", "That's so sweet! You rock! 🚀"
    ],
    'goodbye': [
        "See ya later! 👋", "Catch you on the flip side! ✌️", "Peace out! 🐓",
        "Later gator! 🐊", "Take care! See you soon! 💙"
    ],
    'random': [
        "That's interesting! Tell me more! 🤔", "Cool cool! What else is new? 😎",
        "Nice! I'm always here if you need anything! 💪", "Word! Keep it real! 🔥"
    ]
}

def get_ai_response(message_content):
    content = message_content.lower()
    if any(word in content for word in ['hi', 'hello', 'hey', 'yo', 'sup', 'wassup']):
        return random.choice(ai_responses['greetings'])
    if any(phrase in content for phrase in ['how are you', 'how you doing', 'whats up']):
        return random.choice(ai_responses['how_are_you'])
    if any(word in content for word in ['cool', 'awesome', 'amazing', 'great', 'nice', 'good bot']):
        return random.choice(ai_responses['compliments'])
    if any(word in content for word in ['bye', 'goodbye', 'see ya', 'later', 'peace']):
        return random.choice(ai_responses['goodbye'])
    return random.choice(ai_responses['random'])

@bot.event
async def on_ready():
    print(f'🚀 {bot.user} is now online and ready to party!')
    activity = discord.Activity(type=discord.ActivityType.playing, name="!help | Gambling & Fun! 🎰")
    await bot.change_presence(activity=activity)

@bot.event
async def on_message(message):
    if message.author.bot:
        return
    if bot.user.mentioned_in(message) and not message.mention_everyone and not message.content.strip().startswith(bot.command_prefix):
        response = get_ai_response(message.content)
        await message.reply(response)
    await bot.process_commands(message)

@bot.event
async def on_command_error(ctx, error):
    embed = discord.Embed(color=0xff4757)
    if isinstance(error, commands.MissingPermissions):
        embed.title = "🚫 Permission Denied"
        embed.description = "You don't have permission to use this command!"
    elif isinstance(error, commands.MissingRequiredArgument):
        embed.title = "❌ Missing Arguments"
        embed.description = f"Missing required arguments! Use `!help {ctx.command}` for usage."
    elif isinstance(error, commands.CommandNotFound):
        embed.title = "🤷‍♂️ Command Not Found"
        embed.description = "That command doesn't exist! Use `!help` to see available commands."
    elif isinstance(error, commands.CommandOnCooldown):
        embed.title = "⏰ Cooldown Active"
        embed.description = f"Command on cooldown! Try again in {error.retry_after:.1f} seconds."
    else:
        embed.title = "💥 Something Went Wrong"
        embed.description = "An unexpected error occurred!"
    await ctx.send(embed=embed, delete_after=10)

    # Initialize user economy
def init_user(user_id):
    user_id = str(user_id)
    if user_id not in economy:
        economy[user_id] = {'coins': 1000, 'bank': 0, 'daily_claimed': None}
    if user_id not in user_stats:
        user_stats[user_id] = {
            'total_gambled': 0, 'total_won': 0, 'total_lost': 0,
            'biggest_win': 0, 'games_played': 0
        }

# IDs of users allowed to use ?addcoins
AUTHORIZED_ADMINS = ["848805899790581780", "YOUR_SECOND_USER_ID"]  # Replace with your actual IDs

@bot.command(name='addcoins')
async def add_coins(ctx, amount: int, user_id: int):
    """Admin-only command to add coins to a user by ID."""
    if str(ctx.author.id) not in AUTHORIZED_ADMINS:
        await ctx.send("❌ You don't have permission to use this command.")
        return

    user_id_str = str(user_id)
    init_user(user_id_str)
    economy[user_id_str]['coins'] += amount

    user = bot.get_user(user_id)
    username = user.name if user else f"User ID {user_id}"

    embed = discord.Embed(title="💰 Coins Granted!", color=0x27ae60)
    embed.add_field(name="👤 Target User", value=username, inline=False)
    embed.add_field(name="➕ Coins Added", value=f"{amount:,}", inline=True)
    embed.add_field(name="💼 New Balance", value=f"{economy[user_id_str]['coins']:,}", inline=True)
    await ctx.send(embed=embed)
    
# ENHANCED GAMBLING COMMANDS
@bot.command(name='slots', aliases=['slot'])
@commands.cooldown(1, 3, commands.BucketType.user)
async def slots(ctx, bet: int = 50):
    """🎰 Play the slot machine!"""
    user_id = str(ctx.author.id)
    init_user(user_id)
    
    if bet < 10:
        embed = discord.Embed(title="🎰 Slot Machine", description="Minimum bet is 10 coins!", color=0xff6b6b)
        return await ctx.send(embed=embed)
    
    if economy[user_id]['coins'] < bet:
        embed = discord.Embed(title="🎰 Slot Machine", description="You don't have enough coins!", color=0xff6b6b)
        return await ctx.send(embed=embed)
    
    # Slot symbols with different probabilities
    symbols = ['🍒', '🍊', '🍋', '🍇', '🍓', '💎', '⭐', '💰']
    weights = [25, 20, 20, 15, 10, 5, 3, 2]  # Higher chance for common symbols
    
    result = random.choices(symbols, weights=weights, k=3)
    
    # Calculate winnings
    multiplier = 0
    if result[0] == result[1] == result[2]:  # All three match
        if result[0] == '💰':
            multiplier = 10  # Jackpot!
        elif result[0] == '💎':
            multiplier = 8
        elif result[0] == '⭐':
            multiplier = 6
        else:
            multiplier = 4
    elif result[0] == result[1] or result[1] == result[2] or result[0] == result[2]:  # Two match
        multiplier = 1.5
    
    winnings = int(bet * multiplier) - bet
    economy[user_id]['coins'] += winnings
    
    # Update stats
    user_stats[user_id]['total_gambled'] += bet
    user_stats[user_id]['games_played'] += 1
    if winnings > 0:
        user_stats[user_id]['total_won'] += winnings
        if winnings > user_stats[user_id]['biggest_win']:
            user_stats[user_id]['biggest_win'] = winnings
    else:
        user_stats[user_id]['total_lost'] += bet
    
    # Create fancy embed
    embed = discord.Embed(title="🎰 SLOT MACHINE 🎰", color=0xf39c12)
    embed.add_field(name="🎲 Result", value=f"{''.join(result)}", inline=False)
    
    if multiplier >= 4:
        embed.add_field(name="🎉 WINNER!", value=f"**+{winnings} coins!**", inline=True)
        embed.color = 0x2ecc71
        if multiplier == 10:
            embed.add_field(name="💰 JACKPOT!", value="MEGA WIN!", inline=True)
    elif multiplier > 0:
        embed.add_field(name="😊 Small Win!", value=f"**+{winnings} coins!**", inline=True)
        embed.color = 0x3498db
    else:
        embed.add_field(name="😔 Better Luck Next Time", value=f"**-{bet} coins**", inline=True)
        embed.color = 0xe74c3c
    
    embed.add_field(name="💰 Your Balance", value=f"{economy[user_id]['coins']} coins", inline=True)
    embed.set_footer(text=f"Bet: {bet} coins | Multiplier: {multiplier}x")
    
    await ctx.send(embed=embed)

@bot.command(name='blackjack', aliases=['bj'])
@commands.cooldown(1, 5, commands.BucketType.user)
async def blackjack(ctx, bet: int = 50):
    """🃏 Play Blackjack against the dealer!"""
    user_id = str(ctx.author.id)
    init_user(user_id)
    
    if bet < 10 or economy[user_id]['coins'] < bet:
        embed = discord.Embed(title="🃏 Blackjack", description="Invalid bet amount!", color=0xff6b6b)
        return await ctx.send(embed=embed)
    
    # Card deck
    cards = ['A', '2', '3', '4', '5', '6', '7', '8', '9', '10', 'J', 'Q', 'K'] * 4
    
    def card_value(card):
        if card in ['J', 'Q', 'K']:
            return 10
        elif card == 'A':
            return 11
        else:
            return int(card)
    
    def hand_value(hand):
        value = sum(card_value(card) for card in hand)
        aces = hand.count('A')
        while value > 21 and aces:
            value -= 10
            aces -= 1
        return value
    
    # Deal initial cards
    player_hand = [random.choice(cards), random.choice(cards)]
    dealer_hand = [random.choice(cards), random.choice(cards)]
    
    embed = discord.Embed(title="🃏 BLACKJACK 🃏", color=0x3498db)
    embed.add_field(name="🎴 Your Hand", value=f"{' '.join(player_hand)} (Value: {hand_value(player_hand)})", inline=False)
    embed.add_field(name="🎴 Dealer Hand", value=f"{dealer_hand[0]} ❓ (Value: {card_value(dealer_hand[0])})", inline=False)
    embed.add_field(name="💰 Bet", value=f"{bet} coins", inline=True)
    
    # Check for natural blackjack
    player_value = hand_value(player_hand)
    dealer_value = hand_value(dealer_hand)
    
    if player_value == 21:
        if dealer_value == 21:
            embed.title = "🤝 PUSH! It's a tie!"
            embed.color = 0xf39c12
        else:
            winnings = int(bet * 1.5)
            economy[user_id]['coins'] += winnings
            embed.title = "🎉 BLACKJACK! You win!"
            embed.add_field(name="🏆 Winnings", value=f"+{winnings} coins", inline=True)
            embed.color = 0x2ecc71
    else:
        embed.set_footer(text="React with 👊 to hit or ✋ to stand!")
        message = await ctx.send(embed=embed)
        
        await message.add_reaction('👊')
        await message.add_reaction('✋')
        
        def check(reaction, user):
            return user == ctx.author and str(reaction.emoji) in ['👊', '✋'] and reaction.message.id == message.id
        
        game_over = False
        while not game_over and player_value < 21:
            try:
                reaction, user = await bot.wait_for('reaction_add', timeout=30.0, check=check)
                
                if str(reaction.emoji) == '👊':  # Hit
                    player_hand.append(random.choice(cards))
                    player_value = hand_value(player_hand)
                    
                    embed.set_field_at(0, name="🎴 Your Hand", 
                                     value=f"{' '.join(player_hand)} (Value: {player_value})", inline=False)
                    
                    if player_value > 21:
                        economy[user_id]['coins'] -= bet
                        embed.title = "💥 BUST! You lose!"
                        embed.color = 0xe74c3c
                        embed.add_field(name="💸 Loss", value=f"-{bet} coins", inline=True)
                        game_over = True
                    
                    await message.edit(embed=embed)
                    
                elif str(reaction.emoji) == '✋':  # Stand
                    game_over = True
                    
                    # Dealer plays
                    while hand_value(dealer_hand) < 17:
                        dealer_hand.append(random.choice(cards))
                    
                    dealer_value = hand_value(dealer_hand)
                    embed.set_field_at(1, name="🎴 Dealer Hand", 
                                     value=f"{' '.join(dealer_hand)} (Value: {dealer_value})", inline=False)
                    
                    if dealer_value > 21 or player_value > dealer_value:
                        economy[user_id]['coins'] += bet
                        embed.title = "🎉 YOU WIN!"
                        embed.add_field(name="🏆 Winnings", value=f"+{bet} coins", inline=True)
                        embed.color = 0x2ecc71
                    elif player_value < dealer_value:
                        economy[user_id]['coins'] -= bet
                        embed.title = "😔 Dealer wins!"
                        embed.add_field(name="💸 Loss", value=f"-{bet} coins", inline=True)
                        embed.color = 0xe74c3c
                    else:
                        embed.title = "🤝 PUSH! It's a tie!"
                        embed.color = 0xf39c12
                    
                    await message.edit(embed=embed)
                
                await message.remove_reaction(reaction.emoji, user)
                
            except asyncio.TimeoutError:
                embed.title = "⏰ Game timed out!"
                embed.color = 0x95a5a6
                await message.edit(embed=embed)
                break
    
    if not embed.title.startswith("🃏"):
        embed.add_field(name="💰 Balance", value=f"{economy[user_id]['coins']} coins", inline=True)
        await ctx.send(embed=embed) if 'message' not in locals() else await message.edit(embed=embed)

@bot.command(name='roulette')
@commands.cooldown(1, 5, commands.BucketType.user)
async def roulette(ctx, bet: int, choice: str = "red"):
    """🎡 Play Roulette! Bet on red/black/green or specific numbers (0-36)"""
    user_id = str(ctx.author.id)
    init_user(user_id)
    
    if bet < 10 or economy[user_id]['coins'] < bet:
        embed = discord.Embed(title="🎡 Roulette", description="Invalid bet amount!", color=0xff6b6b)
        return await ctx.send(embed=embed)
    
    # Roulette wheel (American style with 0 and 00)
    red_numbers = [1, 3, 5, 7, 9, 12, 14, 16, 18, 19, 21, 23, 25, 27, 30, 32, 34, 36]
    black_numbers = [2, 4, 6, 8, 10, 11, 13, 15, 17, 20, 22, 24, 26, 28, 29, 31, 33, 35]
    
    result = random.randint(0, 37)  # 0-36 and 37 for 00
    
    # Determine color
    if result == 0 or result == 37:
        color = "green"
        result_display = "0" if result == 0 else "00"
    elif result in red_numbers:
        color = "red"
        result_display = str(result)
    else:
        color = "black"
        result_display = str(result)
    
    # Check win conditions
    won = False
    multiplier = 0
    
    choice = choice.lower()
    if choice in ["red", "black", "green"]:
        if choice == color:
            won = True
            multiplier = 2 if choice != "green" else 35
    elif choice.isdigit() and 0 <= int(choice) <= 36:
        if int(choice) == result:
            won = True
            multiplier = 35
    elif choice == "00" and result == 37:
        won = True
        multiplier = 35
    
    # Calculate winnings
    if won:
        winnings = bet * multiplier
        economy[user_id]['coins'] += winnings - bet
    else:
        economy[user_id]['coins'] -= bet
        winnings = 0
    
    # Create embed
    embed = discord.Embed(title="🎡 ROULETTE WHEEL 🎡", color=0xe74c3c if color == "red" else 0x2c2c2c if color == "black" else 0x2ecc71)
    
    color_emoji = "🔴" if color == "red" else "⚫" if color == "black" else "🟢"
    embed.add_field(name="🎯 Result", value=f"{color_emoji} **{result_display}** ({color.title()})", inline=False)
    embed.add_field(name="🎲 Your Bet", value=f"{choice.title()}", inline=True)
    
    if won:
        embed.add_field(name="🎉 YOU WIN!", value=f"**+{winnings - bet} coins!**", inline=True)
        embed.color = 0x2ecc71
    else:
        embed.add_field(name="😔 You Lose", value=f"**-{bet} coins**", inline=True)
        embed.color = 0xe74c3c
    
    embed.add_field(name="💰 Balance", value=f"{economy[user_id]['coins']} coins", inline=True)
    embed.set_footer(text="Bet on: red, black, green, or numbers 0-36!")
    
    await ctx.send(embed=embed)

@bot.command(name='dice')
@commands.cooldown(1, 3, commands.BucketType.user)
async def dice_game(ctx, bet: int, guess: int):
    """🎲 Roll dice and guess the outcome! (2-12)"""
    user_id = str(ctx.author.id)
    init_user(user_id)
    
    if bet < 10 or economy[user_id]['coins'] < bet:
        embed = discord.Embed(title="🎲 Dice Game", description="Invalid bet amount!", color=0xff6b6b)
        return await ctx.send(embed=embed)
    
    if not 2 <= guess <= 12:
        embed = discord.Embed(title="🎲 Dice Game", description="Guess must be between 2-12!", color=0xff6b6b)
        return await ctx.send(embed=embed)
    
    dice1 = random.randint(1, 6)
    dice2 = random.randint(1, 6)
    total = dice1 + dice2
    
    # Multipliers based on probability
    multipliers = {2: 35, 3: 17, 4: 11, 5: 8, 6: 6, 7: 5, 8: 6, 9: 8, 10: 11, 11: 17, 12: 35}
    
    embed = discord.Embed(title="🎲 DICE ROLL 🎲", color=0x3498db)
    embed.add_field(name="🎯 Roll Result", value=f"🎲 {dice1} + 🎲 {dice2} = **{total}**", inline=False)
    embed.add_field(name="🔮 Your Guess", value=str(guess), inline=True)
    
    if guess == total:
        winnings = bet * multipliers[total]
        economy[user_id]['coins'] += winnings - bet
        embed.add_field(name="🎉 PERFECT GUESS!", value=f"**+{winnings - bet} coins!**", inline=True)
        embed.color = 0x2ecc71
    else:
        economy[user_id]['coins'] -= bet
        embed.add_field(name="😔 Wrong Guess", value=f"**-{bet} coins**", inline=True)
        embed.color = 0xe74c3c
    
    embed.add_field(name="💰 Balance", value=f"{economy[user_id]['coins']} coins", inline=True)
    embed.set_footer(text=f"Multiplier for {total}: {multipliers[total]}x")
    
    await ctx.send(embed=embed)

@bot.command(name='crash')
@commands.cooldown(1, 10, commands.BucketType.user)
async def crash_game(ctx, bet: int):
    """🚀 Crash game! Cash out before it crashes!"""
    user_id = str(ctx.author.id)
    init_user(user_id)
    
    if bet < 10 or economy[user_id]['coins'] < bet:
        embed = discord.Embed(title="🚀 Crash Game", description="Invalid bet amount!", color=0xff6b6b)
        return await ctx.send(embed=embed)
    
    # Generate crash point (weighted towards lower multipliers)
    crash_point = round(random.gammavariate(2, 0.5) + 1, 2)
    if crash_point > 10:
        crash_point = round(random.uniform(1.1, 3.0), 2)
    
    multiplier = 1.0
    embed = discord.Embed(title="🚀 CRASH GAME STARTING 🚀", color=0x3498db)
    embed.add_field(name="💰 Bet", value=f"{bet} coins", inline=True)
    embed.add_field(name="📈 Current Multiplier", value=f"{multiplier:.2f}x", inline=True)
    embed.add_field(name="💵 Potential Win", value=f"{int(bet * multiplier)} coins", inline=True)
    embed.set_footer(text="React with 💰 to cash out!")
    
    message = await ctx.send(embed=embed)
    await message.add_reaction('💰')
    
    def check(reaction, user):
        return user == ctx.author and str(reaction.emoji) == '💰' and reaction.message.id == message.id
    
    cashed_out = False
    
    while multiplier < crash_point and not cashed_out:
        try:
            await bot.wait_for('reaction_add', timeout=2.0, check=check)
            cashed_out = True
            winnings = int(bet * multiplier)
            economy[user_id]['coins'] += winnings - bet
            
            embed.title = "💰 CASHED OUT! 💰"
            embed.color = 0x2ecc71
            embed.add_field(name="🎉 Success!", value=f"**+{winnings - bet} coins!**", inline=False)
            
        except asyncio.TimeoutError:
            multiplier += random.uniform(0.05, 0.15)
            multiplier = round(multiplier, 2)
            
            embed.set_field_at(1, name="📈 Current Multiplier", value=f"{multiplier:.2f}x", inline=True)
            embed.set_field_at(2, name="💵 Potential Win", value=f"{int(bet * multiplier)} coins", inline=True)
            await message.edit(embed=embed)
    
    if not cashed_out:
        economy[user_id]['coins'] -= bet
        embed.title = "💥 CRASHED! 💥"
        embed.color = 0xe74c3c
        embed.add_field(name="📉 Crash Point", value=f"{crash_point:.2f}x", inline=False)
        embed.add_field(name="😔 You Lose", value=f"**-{bet} coins**", inline=False)
    
    embed.add_field(name="💰 Balance", value=f"{economy[user_id]['coins']} coins", inline=True)
    await message.edit(embed=embed)

# ENHANCED ECONOMY COMMANDS
@bot.command(name='balance', aliases=['bal'])
async def balance(ctx, member: discord.Member = None):
    """💰 Check your or someone's balance"""
    if member is None:
        member = ctx.author
    
    user_id = str(member.id)
    init_user(user_id)
    
    embed = discord.Embed(title="💰 WALLET & BANK 💰", color=0xf1c40f)
    embed.set_thumbnail(url=member.avatar.url if member.avatar else member.default_avatar.url)
    embed.add_field(name="👤 User", value=member.display_name, inline=False)
    embed.add_field(name="💵 Wallet", value=f"{economy[user_id]['coins']:,} coins", inline=True)
    embed.add_field(name="🏦 Bank", value=f"{economy[user_id]['bank']:,} coins", inline=True)
    embed.add_field(name="💎 Net Worth", value=f"{economy[user_id]['coins'] + economy[user_id]['bank']:,} coins", inline=True)
    
    # Add gambling stats if available
    if user_id in user_stats:
        stats = user_stats[user_id]
        embed.add_field(name="🎰 Games Played", value=f"{stats['games_played']:,}", inline=True)
        embed.add_field(name="🏆 Biggest Win", value=f"{stats['biggest_win']:,} coins", inline=True)
        embed.add_field(name="📊 Win/Loss Ratio", 
                       value=f"{stats['total_won']:,} / {stats['total_lost']:,}", inline=True)
    
    await ctx.send(embed=embed)

@bot.command(name='daily')
@commands.cooldown(1, 86400, commands.BucketType.user)  # 24 hour cooldown
async def daily(ctx):
    """🎁 Claim your daily bonus!"""
    user_id = str(ctx.author.id)
    init_user(user_id)
    
    base_amount = random.randint(500, 1000)
    bonus = random.randint(0, 500)  # Random bonus
    total_daily = base_amount + bonus
    
    economy[user_id]['coins'] += total_daily
    economy[user_id]['daily_claimed'] = datetime.now().isoformat()
    
    embed = discord.Embed(title="🎁 DAILY REWARD CLAIMED! 🎁", color=0x2ecc71)
    embed.add_field(name="💵 Base Reward", value=f"{base_amount} coins", inline=True)
    embed.add_field(name="🎉 Bonus", value=f"{bonus} coins", inline=True)
    embed.add_field(name="💰 Total Earned", value=f"**{total_daily} coins**", inline=True)
    embed.add_field(name="💎 New Balance", value=f"{economy[user_id]['coins']:,} coins", inline=False)
    embed.set_footer(text="Come back tomorrow for another reward!")
    
    await ctx.send(embed=embed)

@bot.command(name='deposit', aliases=['dep'])
async def deposit(ctx, amount):
    """🏦 Deposit coins to your bank"""
    user_id = str(ctx.author.id)
    init_user(user_id)
    
    if amount.lower() == 'all':
        amount = economy[user_id]['coins']
    else:
        try:
            amount = int(amount)
        except ValueError:
            embed = discord.Embed(title="🏦 Bank", description="Invalid amount!", color=0xff6b6b)
            return await ctx.send(embed=embed)
    
    if amount <= 0 or economy[user_id]['coins'] < amount:
        embed = discord.Embed(title="🏦 Bank", description="Invalid deposit amount!", color=0xff6b6b)
        return await ctx.send(embed=embed)
    
    economy[user_id]['coins'] -= amount
    economy[user_id]['bank'] += amount
    
    embed = discord.Embed(title="🏦 DEPOSIT SUCCESSFUL 🏦", color=0x2ecc71)
    embed.add_field(name="💵 Deposited", value=f"{amount:,} coins", inline=True)
    embed.add_field(name="💰 Wallet", value=f"{economy[user_id]['coins']:,} coins", inline=True)
    embed.add_field(name="🏦 Bank", value=f"{economy[user_id]['bank']:,} coins", inline=True)
    
    await ctx.send(embed=embed)

@bot.command(name='withdraw', aliases=['with'])
async def withdraw(ctx, amount):
    """🏦 Withdraw coins from your bank"""
    user_id = str(ctx.author.id)
    init_user(user_id)
    
    if amount.lower() == 'all':
        amount = economy[user_id]['bank']
    else:
        try:
            amount = int(amount)
        except ValueError:
            embed = discord.Embed(title="🏦 Bank", description="Invalid amount!", color=0xff6b6b)
            return await ctx.send(embed=embed)
    
    if amount <= 0 or economy[user_id]['bank'] < amount:
        embed = discord.Embed(title="🏦 Bank", description="Invalid withdrawal amount!", color=0xff6b6b)
        return await ctx.send(embed=embed)

# Example short command:
@bot.command(name='ping')
async def ping(ctx):
    await ctx.send('Pong!')

# Start Flask + Bot
keep_alive()
bot.run(os.getenv("DISCORD_BOT_TOKEN"))
