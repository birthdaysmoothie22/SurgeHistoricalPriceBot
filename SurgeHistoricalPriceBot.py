import os
import json
import logging
import time
import datetime
from discord.client import Client
import pytz
import asyncio
import discord
from discord.ext import tasks, commands
from discord_components import *
from dotenv import load_dotenv
from web3 import Web3, exceptions

#load environment variables
load_dotenv()

ROOT_PATH = os.getenv('ROOT_PATH')
SURGE_HISTORICAL_PRICE_BOT_KEY = os.getenv('SURGE_HISTORICAL_PRICE_BOT_KEY')
OWNER_DISCORD_ID = int(os.getenv('OWNER_DISCORD_ID'))

with open(ROOT_PATH+"/surge_tokens.json", "r") as surge_tokens_json:
	surge_tokens = json.load(surge_tokens_json)

bot = commands.Bot(command_prefix='$', owner_id=OWNER_DISCORD_ID, help_command=None)

@bot.event
async def on_ready():
	print('We have logged in as {0.user}'.format(bot))
	DiscordComponents(bot)

@bot.command(aliases=['Price'])
@commands.dm_only()
async def price(ctx):
	message = await ctx.author.send("Pick a Surge token to calculate", delete_after=30,
		components =
		[Select(placeholder="Select a Surge Token",
				options=[
					SelectOption(
						label="OG Surge BNB", 
						value="OgSurgeBNB"
					),
					SelectOption(
						label="Surge USD", 
						value="SurgeUSD"
					),
					SelectOption(
						label="Surge ETH", 
						value="SurgeETH"
					),
					SelectOption(
						label="Surge BTC", 
						value="SurgeBTC"
					),
					SelectOption(
						label="Surge ADA", 
						value="SurgeADA"
					),
					SelectOption(
						label="Surge USLS", 
						value="SurgeUSLS"
					),
					SelectOption(
						label="Surge XUSD", 
						value="SurgeXUSD"
					)
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

		message_2 = 'Please enter a block number:\n'
		await ctx.author.send(message_2)

		def check_message_2(msg):
			return msg.author == ctx.author and len(msg.content) > 0

		try:
			block_number = await bot.wait_for("message", check=check_message_2, timeout = 30) # 30 seconds to reply
		except asyncio.TimeoutError:
			await ctx.send("Sorry, you either didn't reply with a block number or didn't reply in time!")
			return

		bsc_archive = "https://speedy-nodes-nyc.moralis.io/826220dcb5df29a279541244/bsc/mainnet/archive"
		web3 = Web3(Web3.HTTPProvider(bsc_archive))

		contract_address = surge_tokens[token]['address']
		contract_address = web3.toChecksumAddress(contract_address)
		with open(ROOT_PATH+"/surge_abis/"+surge_tokens[token]['abi_name']+".json", "r") as surge_abi:
			contract_abi = json.load(surge_abi)
		
		contract = web3.eth.contract(address=contract_address, abi=contract_abi)

		try:
			block_number = int(block_number.content)
			tokenPriceRaw = contract.functions.calculatePrice().call(block_identifier = block_number)

			tokenPrice = web3.fromWei(tokenPriceRaw, surge_tokens[token]['wei_unit'])
			tokenPrice = f'{tokenPrice:.18f}'
			await ctx.send(tokenPrice)
		except exceptions.BlockNumberOutofRange:
			await ctx.send("Sorry, I can't find a price")

	except discord.NotFound:
		return # not sure what to do here...
	except asyncio.TimeoutError:
		await ctx.author.send("Sorry, you didn't reply in time!")
		await message.delete()
		return

@bot.command(aliases=['Help'])
@commands.dm_only()
async def help(ctx):
	print('help')

bot.run(SURGE_HISTORICAL_PRICE_BOT_KEY)