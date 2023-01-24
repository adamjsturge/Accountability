import asyncio
import discord
from discord.ext import commands
from src.utils.logger import logtofile
import src.lib.user as user_lib
import src.lib.wk_api as wk_api
from src.utils.utils import get_config
import traceback
from src.utils.time import get_seconds_until_next_hour

running = False
pending_review_disappointed_threshold = 25

async def do_daily_summary(bot: commands.Bot) -> None:
    global running
    if running:
        return

    try:
        running = True
        await asyncio.sleep(get_seconds_until_next_hour())
        while True:
            users = user_lib.get_users_with_api_tokens()
            data = {}
            for user in users:
                if user_lib.is_midnight_in_users_timezone(user.id):
                    reviews = wk_api.get_count_of_reviews_completed_yesterday(user.token, user.timezone)
                    lessons = wk_api.get_lessons_completed_yesterday(user.token, user.timezone)
                    pending_reviews = wk_api.get_count_of_reviews_available_before_end_of_yesterday(user.token, user.timezone)
                    data[user.id] = {
                        'reviews': reviews,
                        'lessons': len(lessons),
                        'pending_reviews': pending_reviews
                    }
            await send_daily_summary_message(data, bot)
            await asyncio.sleep(get_seconds_until_next_hour())
    except:
        s = traceback.format_exc()
        content = f'Ignoring exception\n{s}'
        logtofile(content, 'error')
        running = False
        await do_daily_summary(bot)

async def send_daily_summary_message(data: dict, bot: commands.Bot) -> None:
    if len(data) == 0:
        return

    user_name = bot.user.name
    icon_url = bot.user.avatar_url
    channel = bot.get_channel(int(get_config('channel_id')))
    embed = discord.Embed(title=f'Daily WaniKani Summary', color=0xFF5733)

    message = ''
    disappointed_in_users = []
    for user_id, wk_data in data.items():
        user = channel.guild.get_member(user_id)
        lessons = wk_data['lessons']
        reviews = wk_data['reviews']
        pending_reviews = wk_data['pending_reviews']
        if pending_reviews >= pending_review_disappointed_threshold:
            disappointed_in_users.append(user.mention)
        if pending_reviews == 0:
            pending_reviews = 'no'
        message = f'Completed {lessons} lessons and {reviews} reviews\nHas {pending_reviews} available reviews'
        embed.add_field(name=user.display_name, value=message, inline=False)
    await channel.send(embed=embed)

    if len(disappointed_in_users) > 0:
        message = ' '.join(disappointed_in_users)
        message += f' you had at least {pending_review_disappointed_threshold} reviews remaining at the end of the day\n'
        message += 'https://tenor.com/view/anime-k-on-disappoint-disappointed-gif-6051447'
        await channel.send(message)
