import os
import json
import time
import datetime
from discord.client import Client
import pytz
import asyncio
import discord
from discord.ext import tasks, commands
from discord_components import *
from dotenv import load_dotenv
import surge_profit_tracker
import surge_profit_tracker_queue

#load environment variables
load_dotenv()

ROOT_PATH = os.getenv('ROOT_PATH')
SURGE_PROFIT_TRACKER_BOT_KEY = os.getenv('SURGE_PROFIT_TRACKER_BOT_KEY')
OWNER_DISCORD_ID = int(os.getenv('OWNER_DISCORD_ID'))

with open(ROOT_PATH+"/surge_tokens.json", "r") as surge_tokens_json:
    surge_tokens = json.load(surge_tokens_json)

def createCalcResultEmbedMessage(token, result):
    data = json.loads(result)

    embed = discord.Embed(
        title="Surge "+surge_tokens[token]['symbol']+" Details",
        description="", 
        color=0x22B4AB)
    embed.set_thumbnail(url=surge_tokens[token]['icon'])
    embed.add_field(name="Total Amount Bought", value=data[token]['total_underlying_asset_amount_purchased'], inline=False)
    embed.add_field(name="Total Amount Sold", value=data[token]['total_underlying_asset_amount_received'], inline=False)
    embed.add_field(name="Current Value of Surge After Sell Fee", value=data[token]['current_underlying_asset_value'], inline=False)
    embed.add_field(name="Overall +/- Profit", value=data[token]['overall_profit_or_loss'], inline=False)
    
    embed_disclaimer_text = "This bot gives you a close approximation of your overall accrual of Surge Token value. This is accomplished by pulling buyer transaction history and tracking historical price data on both the Surge Token and it's backing asset. Due to volatility of the backing asset, the price average between milliseconds of every transaction is used to attain the historical value. Because of this, the reflected value may not be 100% accurate. Estimated accuracy is estimated to be within 90-100%. \n\nPlease contact birthdaysmoothie#9602 if you have any question, issues, or data-related concerns."
    embed.set_footer(text=embed_disclaimer_text)

    return embed

def createCustomHelpEmbedMessage():
    embed = discord.Embed(
        title="Available SurgeProfitTrackerBot Commands",
        description="Here are all the available commands for the SurgeProfitTrackerBot.\nAll commands must start with !", 
        color=0x22B4AB)
    embed.set_thumbnail(url="https://cdn.discordapp.com/attachments/892852181802291215/898293624528338944/Profit_Checker_3.png")
    embed.add_field(name="!calculate", value="Calculates your overall Surge Token value.  Requires you to pick a token and provide your public wallet address.", inline=False)
    embed.add_field(name="!calculate_manual", value="Calculates your overall Surge Token value.  You must provide the token you wish to caluclate and your public wallet address.  Example: !calculate_manual SurgeADA 0x00a...", inline=False)
    embed.add_field(name="!list", value="View available tokens to choose from.", inline=False)
    embed.add_field(name="!queue", value="View how many people are queued up to calculate profits.", inline=False)

    return embed

async def processProfitCalculation(ctx, token, wallet_address):
    if surge_profit_tracker_queue.checkQueuePlace(ctx.author.id) == 0:
        await ctx.author.send("I'm calculating your profits now")
        result = surge_profit_tracker.calculateSurgeProfits(wallet_address, token)
        embed = createCalcResultEmbedMessage(token, result)
        await ctx.author.send(embed=embed)
        surge_profit_tracker_queue.removeFromQueue(ctx.author.id)
    else:
        await asyncio.sleep(1)
        await processProfitCalculation(ctx, token, wallet_address)

async def calculateProfits(ctx, token, wallet_address):
    tracker_queue_count = surge_profit_tracker_queue.checkQueueCount()
    if tracker_queue_count < 5:
        surge_profit_tracker_queue.addToQueue(ctx.author.id)
        queue_place = surge_profit_tracker_queue.checkQueuePlace(ctx.author.id)
        # check queue place and send a message
        if queue_place > 0:
            await ctx.author.send("You are #"+str(queue_place)+" in line. I'll message you your results when I'm done calculating.")     
        
        await processProfitCalculation(ctx, token, wallet_address)
        return
    else:
        await ctx.author.send("There are too many people requesting right now, please try again leter.  You can check the queue count at anytime by typing in !queue")
        return

bot = commands.Bot(command_prefix='', owner_id=OWNER_DISCORD_ID, help_command=None)

@bot.event
async def on_ready():
    print('We have logged in as {0.user}'.format(bot))
    DiscordComponents(bot)

@bot.command(aliases=['Calculate', 'calc'])
@commands.dm_only()
async def calculate(ctx):
    message = await ctx.author.send("Pick a Surge token to calculate", delete_after=30,
        components =
        [Select(placeholder="Select a Surge Token",
                options=[
                    SelectOption(
                        label="SurgeUSD", 
                        value="SurgeUSD"
                    ),
                    SelectOption(
                        label="SurgeETH", 
                        value="SurgeETH"
                    ),
                    SelectOption(
                        label="SurgeBTC", 
                        value="SurgeBTC"
                    ),
                    SelectOption(
                        label="SurgeADA", 
                        value="SurgeADA"
                    ),
                    SelectOption(
                        label="SurgeUSLS", 
                        value="SurgeUSLS"
                    ),
                ]
            )
        ]
    )

    try:
        # Wait for the user to select a token
        event = await bot.wait_for("select_option", check = None, timeout = 30) # 30 seconds to reply

        token = event.values[0]
        response_messsge = "You selected "+token
        await ctx.author.send(response_messsge)
        # Delete the original drop down so the user can't interact with it again
        await message.delete()

        message_2 = 'Please tell me your wallet address\n'
        await ctx.author.send(message_2)

        def check_message_2(msg):
            return msg.author == ctx.author and len(msg.content) > 0

        try:
            wallet_address = await bot.wait_for("message", check=check_message_2, timeout = 30) # 30 seconds to reply
        except asyncio.TimeoutError:
            await ctx.send("Sorry, you either did't reply with your wallet address or didn't reply in time!")
            return
            
        await calculateProfits(ctx, token, wallet_address.content)
        return
        
    except discord.NotFound:
        return # not sure what to do here...
    except asyncio.TimeoutError:
        await ctx.send("Sorry, you didn't reply in time!")
        await message.delete()
        return

@bot.command(aliases=['Calculate_manual', 'calc_manual'])
@commands.dm_only()
async def calculate_manual(ctx, token, wallet_address):
    if token in surge_tokens:
        await calculateProfits(ctx, token, wallet_address)
        return
    else:
        await ctx.author.send("That is not a valid Surge token. Please type !list to see available tokens to calculate.")
        return

@calculate_manual.error
async def on_command_error(ctx, error):
    if isinstance(error, commands.MissingRequiredArgument):
        await ctx.author.send("I did not get the required details for this request. A proper request looks like this !calculate_manual *token* *wallet_address*")

@bot.command(brief='Returns how many people are in the tracker queue')
@commands.dm_only()
async def queue(ctx):
    tracker_queue = surge_profit_tracker_queue.checkQueueCount()
    await ctx.author.send("There are "+str(tracker_queue)+" people in the profit tracker queue")

@bot.command(brief='Lists available tokens to calculate')
@commands.dm_only()
async def list(ctx):
    message = 'Here are a list of available tokens to calculate: \n'
    message += ' >>> '
    for token in surge_tokens:
        message += token+"\n"
    await ctx.author.send(message)

@bot.command()
@commands.dm_only()
async def help(ctx):
    help_embed = createCustomHelpEmbedMessage()
    await ctx.author.send(embed=help_embed)

# start owner commands only
@bot.command()
@commands.is_owner()
@commands.dm_only()
async def queue_entries(ctx):
    message = '```'
    if len(surge_profit_tracker_queue.surge_profit_tracker_queue) > 0:
        for k in surge_profit_tracker_queue.surge_profit_tracker_queue:
            if k in surge_profit_tracker_queue.surge_profit_tracker_queue_users_times:
                message += str(k)+' since '+surge_profit_tracker_queue.surge_profit_tracker_queue_users_times[k]+'\n'
            else:
                message += str(k)+'\n'
    else:
        message += 'No queue entries'
    message += '```'
    await ctx.author.send(message)

    return

@bot.command()
@commands.is_owner()
@commands.dm_only()
async def remove_queue_entry(ctx, user_id):
    surge_profit_tracker_queue.removeFromQueue(int(user_id))
    message = user_id+" has been removed from the queue"
    await ctx.author.send(message)
    
    return

# @bot.command()
# @commands.is_owner()
# @commands.dm_only()
# async def restart(ctx):
#     await ctx.author.send("Bot is restarting")
#     os.system("pm2 restart SurgeProfitTrackerBotV2 --interpreter python3")

#     return

bot.run(SURGE_PROFIT_TRACKER_BOT_KEY)