# displays 24h digital clock
from datetime import datetime

def data(time, **kwargs):
    return datetime.fromtimestamp(time).strftime("%H%M")
