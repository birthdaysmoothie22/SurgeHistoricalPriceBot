import datetime
import pytz

surge_profit_tracker_queue = []
surge_profit_tracker_queue_users_times = {}

def addToQueue(user_id):
    surge_profit_tracker_queue.append(user_id)
    datetime_now = datetime.datetime.now(pytz.timezone('America/Chicago')).strftime("%m-%d-%Y %H:%M:%S")
    surge_profit_tracker_queue_users_times[user_id] = datetime_now

def removeFromQueue(user_id):
    surge_profit_tracker_queue.remove(user_id)
    surge_profit_tracker_queue_users_times.pop(user_id)

def checkQueuePlace(user_id):
    return surge_profit_tracker_queue.index(user_id)

def checkQueueCount():
    return len(surge_profit_tracker_queue)

        