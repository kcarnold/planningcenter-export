
# Browser: https://api.planningcenteronline.com/explorer/services/v2/songs/7714382/arrangements/8671960

import streamlit as st
import requests
from requests.auth import HTTPBasicAuth
import dotenv
import os
import io
from contextlib import redirect_stdout
from datetime import date, timedelta

dotenv.load_dotenv()

client_id = os.getenv('PLANNINGCENTER_CLIENT_ID') or ""
secret = os.getenv('PLANNINGCENTER_SECRET') or ""

assert client_id, "Missing PLANNINGCENTER_CLIENT_ID"
assert secret, "Missing PLANNINGCENTER_SECRET"

@st.cache_data(ttl=3600)
def get_json(url, params=None):
    response = requests.get(url, auth=HTTPBasicAuth(client_id, secret), params=params)
    return response.json()

service_types = get_json('https://api.planningcenteronline.com/services/v2/service_types')
service_type_ids = [st['id'] for st in service_types['data']]
service_type_names = {st['id']: st['attributes']['name'] for st in service_types['data']}
service_type = st.selectbox("Service type",
                            options=service_type_ids,
                            format_func=lambda x: service_type_names[x])

today = date.today()
two_weeks_ago = today - timedelta(days=14)

def get_recent_services(service_type):
    #return get_json(f'https://api.planningcenteronline.com/services/v2/service_types/{service_type}/plans?order=sort_date&filter=future')
    return get_json(f'https://api.planningcenteronline.com/services/v2/service_types/{service_type}/plans',
                    {'order': 'sort_date', 'filter': 'after', 'after': two_weeks_ago})

recent_services = get_recent_services(service_type)
service_dates = [service['attributes']['dates'] for service in recent_services['data']]
# find the index of the upcoming service, if any.
upcoming_service_idx = next((i for i, service in enumerate(recent_services['data']) if service['attributes']['sort_date'] >= str(today)), 0)
service_idx = st.selectbox("Service date", options=list(range(len(service_dates))), format_func=lambda x: service_dates[x], index=upcoming_service_idx)
service = recent_services['data'][service_idx]
service_date = service['attributes']['dates']

items = get_json(service['links']['self'] + '/items')

def get_lyrics(song):
    """Takes a "song" object and grabs all the "arrangements" and picks the "lyrics" of the first one where it's not empty."""
    if 'links' not in song:
        song = song['data']
    arrangements_url = song['links']['arrangements']
    arrangements = get_json(arrangements_url)
    for arrangement in arrangements['data']:
        lyrics = arrangement['attributes']['lyrics']
        if lyrics:
            return lyrics

include_lyrics = st.checkbox("Include lyrics", value=False)

output = io.StringIO()
with redirect_stdout(output):
    prev_item_type = None
    for item in items['data']:
        attrs = item['attributes']
        item_type = attrs['item_type']
        if item_type == "item":
            title = attrs['title']
            if title.startswith("NOTE: SERVICE PLANNING"):
                continue
            print(f"### {attrs['title']}\n\n")
            if attrs['description']:
                print(attrs['description'].replace('\n', '\\\n'))
            print('\n\n')
        elif item_type == "song":
            if include_lyrics:
                song_id = item['relationships']['song']['data']['id']
                song = get_json(f"https://api.planningcenteronline.com/services/v2/songs/{song_id}")
                print(f"### {attrs['title']}\n\n")
                lyrics = get_lyrics(song)
                if lyrics:
                    print(lyrics)
                else:
                    print("No lyrics found.")
                print('\n\n')
            else:
                if prev_item_type != "song":
                    print(f"### Songs\n\n")
                print(f"- {attrs['title']}")
        prev_item_type = item_type

st.markdown(output.getvalue())