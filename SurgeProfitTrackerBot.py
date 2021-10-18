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
        color=surge_tokens[token]['color'])
    embed.set_thumbnail(url=surge_tokens[token]['icon'])
    embed.add_field(name="Total Amount Bought in USD", value=data[token]['total_underlying_asset_amount_purchased'], inline=False)
    if token != 'SurgeUSD':
        embed.add_field(name="Total Amount Bought in "+surge_tokens[token]['symbol'], value=data[token]['total_underlying_asset_value_purchased'], inline=False)
    embed.add_field(name="Total Amount Sold in USD", value=data[token]['total_underlying_asset_amount_received'], inline=False)
    embed.add_field(name="Current Value After Sell Fee in USD", value=data[token]['current_underlying_asset_value'], inline=False)
    if token != 'SurgeUSD':
        embed.add_field(name="Current Value After Sell Fee in "+surge_tokens[token]['symbol'], value=data[token]['current_underlying_asset_amount'], inline=False)
        embed.add_field(name="Current "+surge_tokens[token]['symbol']+" Price:", value=data[token]['current_underlying_asset_price'], inline=False)
    embed.add_field(name="Overall +/- Profit in USD", value=data[token]['overall_profit_or_loss'], inline=False)
    
    embed_disclaimer_text = "This bot gives you a close approximation of your overall accrual of Surge Token value. This is accomplished by pulling buyer transaction history and tracking historical price data on both the Surge Token and it's backing asset. Due to volatility of the backing asset, the price average between milliseconds of every transaction is used to attain the historical value. Because of this, the reflected value may not be 100% accurate. Estimated accuracy is estimated to be within 90-100%."
    embed_disclaimer_text +="\n\nPlease contact birthdaysmoothie#9602 if you have any question, issues, or data-related concerns."
    embed_disclaimer_text +="\n\nPricing data powered by Binance and Coingecko APIs."
    embed_disclaimer_text +="\nTransaction data powered by BscScan APIs"
    embed.set_footer(text=embed_disclaimer_text)

    return embed

def createCustomHelpEmbedMessage():
    embed = discord.Embed(
        title="Available SurgeProfitTrackerBot Commands",
        description="Here are all the available commands for the SurgeProfitTrackerBot.", 
        color=0x22B4AB)
    embed.set_thumbnail(url="https://cdn.discordapp.com/attachments/892852181802291215/898293624528338944/Profit_Checker_3.png")
    embed.add_field(name="calculate, calc", value="Calculates your overall Surge Token value.  Requires you to pick a token and provide your public wallet address.", inline=False)
    embed.add_field(name="calculate_manual, calc_manual", value="Calculates your overall Surge Token value.  You must provide the token you wish to caluclate and your public wallet address.  Example: !calculate_manual SurgeADA 0x00a...", inline=False)
    embed.add_field(name="list", value="View available tokens to choose from.", inline=False)
    embed.add_field(name="remove_daily", value="Be removed from the daily report list.", inline=False)
    #embed.add_field(name="queue", value="View how many people are queued up to calculate profits.", inline=False)

    return embed

# Old calculateProfits function that has queue in it
#
# async def calculateProfits(ctx, token, wallet_address):
#     tracker_queue_count = surge_profit_tracker_queue.checkQueueCount()
#     if tracker_queue_count < 5:
#         surge_profit_tracker_queue.addToQueue(ctx.author.id)
#         queue_place = surge_profit_tracker_queue.checkQueuePlace(ctx.author.id)
#         # check queue place and send a message
#         if queue_place > 0:
#             await ctx.author.send("You are #"+str(queue_place)+" in line. I'll message you your results when I'm done calculating.")     
        
#         await processProfitCalculation(ctx, token, wallet_address)
#         return
#     else:
#         await ctx.author.send("There are too many people requesting right now, please try again leter.  You can check the queue count at anytime by typing in !queue")
#         return

async def calculateProfits(ctx, token, wallet_address):
    await ctx.author.send("I'm creating your report now:")
    result = surge_profit_tracker.calculateSurgeProfits(wallet_address, token)
    embed = createCalcResultEmbedMessage(token, result)
    await ctx.author.send(embed=embed)
    return

async def calculateAllProfits(ctx, wallet_address):
    await ctx.author.send("I'm creating your reports now:")
    for token in surge_tokens:
        result = surge_profit_tracker.calculateSurgeProfits(wallet_address, token)
        embed = createCalcResultEmbedMessage(token, result)
        await ctx.author.send(embed=embed)
    
    await ctx.author.send("All your reports are complete.")
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
                        label="Show All", 
                        value="all"
                    ),
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
        
        if token == 'all':
            await calculateAllProfits(ctx, wallet_address.content)

            daily_report_list_message = 'Would you like to receive these reports daily [Y/N]?\n'
            daily_report_list_message += 'It will require me to save your wallet address so I can automatically send them to you.'
            await ctx.author.send(daily_report_list_message)

            def check_message(msg):
                return msg.author == ctx.author and len(msg.content) > 0

            try:
                daily_report_list_response = await bot.wait_for("message", check=check_message, timeout = 30) # 30 seconds to reply
                if daily_report_list_response.content.lower() == 'y':
                    with open(ROOT_PATH+"/daily_report_list.json", "r") as daily_report_list_json:
                        daily_report_list = json.load(daily_report_list_json)

                    if str(ctx.author.id) not in daily_report_list:
                        daily_report_list[ctx.author.id] = wallet_address.content

                        with open(ROOT_PATH+"/daily_report_list.json", "w") as daily_report_list_json:
                            json.dump(daily_report_list, daily_report_list_json)
                        
                        await ctx.author.send("Thank you, you've been added to the daily report list.")
                    else:
                        await ctx.author.send("You are already on the daily report list.")
            except asyncio.TimeoutError:
                await ctx.send("Sorry, you either did't reply in time!")
            
            return
        else:
            await calculateProfits(ctx, token, wallet_address.content)
            #@todo give the user the option to pick another token without asking them for their wallet again
            return
    except discord.NotFound:
        return # not sure what to do here...
    except asyncio.TimeoutError:
        await ctx.author.send("Sorry, you didn't reply in time!")
        await message.delete()
        return
    except Exception as e:
        #@todo save errors in a log file
        await ctx.author.send("Sorry, something went wrong, please try again later.")
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

# @bot.command(aliases=['Queue'])
# @commands.dm_only()
# async def queue(ctx):
#     tracker_queue = surge_profit_tracker_queue.checkQueueCount()
#     await ctx.author.send("There are "+str(tracker_queue)+" people in the profit tracker queue")

@bot.command(aliases=['Remove_daily'])
@commands.dm_only()
async def remove_daily(ctx):
    with open(ROOT_PATH+"/daily_report_list.json", "r") as daily_report_list_json:
        daily_report_list = json.load(daily_report_list_json)
    
    if str(ctx.author.id) in daily_report_list:
        daily_report_list.pop(str(ctx.author.id))
        with open(ROOT_PATH+"/daily_report_list.json", "w") as daily_report_list_json:
            json.dump(daily_report_list, daily_report_list_json)

        await ctx.author.send("You have been removed from the daily report.")
    else:
        await ctx.author.send("You are not in the daily report list.")

    return

@bot.command(aliases=['List'])
@commands.dm_only()
async def list(ctx):
    message = 'Here are a list of available tokens to calculate: \n'
    message += ' >>> '
    for token in surge_tokens:
        message += token+"\n"
    await ctx.author.send(message)

@bot.command(aliases=['Help'])
@commands.dm_only()
async def help(ctx):
    help_embed = createCustomHelpEmbedMessage()
    await ctx.author.send(embed=help_embed)

# start owner commands only
# @bot.command(aliases=['Queue_entries'])
# @commands.is_owner()
# @commands.dm_only()
# async def queue_entries(ctx):
#     message = '```'
#     if len(surge_profit_tracker_queue.surge_profit_tracker_queue) > 0:
#         for k in surge_profit_tracker_queue.surge_profit_tracker_queue:
#             if k in surge_profit_tracker_queue.surge_profit_tracker_queue_users_times:
#                 message += str(k)+' since '+surge_profit_tracker_queue.surge_profit_tracker_queue_users_times[k]+'\n'
#             else:
#                 message += str(k)+'\n'
#     else:
#         message += 'No queue entries'
#     message += '```'
#     await ctx.author.send(message)

#     return

# @bot.command(aliases=['Remove_queue_entry'])
# @commands.is_owner()
# @commands.dm_only()
# async def remove_queue_entry(ctx, user_id):
#     surge_profit_tracker_queue.removeFromQueue(int(user_id))
#     message = user_id+" has been removed from the queue"
#     await ctx.author.send(message)
    
#     return

@bot.command(aliases=['Restart'])
@commands.is_owner()
@commands.dm_only()
async def restart(ctx):
    await ctx.author.send("Bot is restarting")
    os.system("pm2 restart SurgeProfitTrackerBot --interpreter python3")

    return

bot.run(SURGE_PROFIT_TRACKER_BOT_KEY)