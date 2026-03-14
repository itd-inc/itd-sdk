from itd.request import fetch

def get_top_clans(token: str):
    return fetch(token, 'get', 'users/stats/top-clans')

def get_who_to_follow(token: str):
    return fetch(token, 'get', 'users/suggestions/who-to-follow')
