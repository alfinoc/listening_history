from flask import Flask, request, render_template
from json import loads
from urllib2 import urlopen
from grequests import get, map as sendAll
from functools import partial
from datetime import datetime
app = Flask(__name__)

KEY = 'ef2f18ff332a62f72ad46c4820bdb11b'
BASE_URL = 'http://ws.audioscrobbler.com/2.0/?format=json&api_key={0}'.format(KEY)
CHART_METHOD = 'user.getweeklychartlist'
ARTIST_METHOD = 'user.getweeklyartistchart'

# Once you're caching, could just make this a year or something.
NUM_SPANS = 52 * 2

# Keyed on API urls.
cache = {}

# May not return responses in order given in urls. Also, first url
# in urls will always be a cache miss.
def getCharts(urls):
  if urls[0] in cache:
    del cache[urls[0]]
  cached = [cache[url] for url in urls if url in cache]
  newUrls = [url for url in urls if url not in cache]
  responses = map(lambda resp: loads(resp.content), sendAll(map(get, newUrls)))
  for i in range(len(newUrls)):
    cache[newUrls[i]] = responses[i]
  return cached + responses

# methods: , 
def chart_url(user):
  return BASE_URL + '&method={0}&user={1}'.format(CHART_METHOD, user)

def artist_url(user, span):
  return BASE_URL + '&method={0}&user={1}&from={2}&to={3}'.format(ARTIST_METHOD, user, span['from'], span['to']) 

@app.template_filter('format_date')
def format_date(timestamp):
  return datetime.fromtimestamp(int(timestamp)).strftime('%b %d')

@app.route('/artists')
def artists():
  user = request.args.get('user')
  charts = loads(urlopen(chart_url(user)).read())
  spans = sorted(charts['weeklychartlist']['chart'], key=lambda span : -int(span['from']))[:NUM_SPANS]
  urls = map(partial(artist_url, user), spans)
  responses = sorted(getCharts(urls), key=lambda response : 0)#- int(response['weeklyartistchart']['@attr']['from']))
  
  # Trim to only include artists that haven't appeared in a more recent week.
  seen = set()
  result = []
  for response in responses:
    artists = response['weeklyartistchart']['artist']
    artists = [a for a in artists if not a['name'] in seen]
    seen.update([a['name'] for a in artists])
    response['weeklyartistchart']['artist'] = artists

  return render_template('artists.html', spans=responses, user=user)

if __name__ == "__main__":
    app.run(debug=True)
