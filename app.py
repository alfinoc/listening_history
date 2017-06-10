from flask import Flask, request, render_template, redirect, url_for
from json import loads
from urllib2 import urlopen
from grequests import get, map as sendAll
from functools import partial
from datetime import datetime
from film_store import SqlFilmStore
from dateutil.parser import parse
import time

app = Flask(__name__)

SQL_FILE = '/Users/chrisalfino/Projects/listening_history/film_store.sql'
KEY = 'ef2f18ff332a62f72ad46c4820bdb11b'
BASE_URL = 'http://ws.audioscrobbler.com/2.0/?format=json&api_key={0}'.format(KEY)
CHART_METHOD = 'user.getweeklychartlist'
ARTIST_METHOD = 'user.getweeklyartistchart'
ALBUM_METHOD = 'user.getweeklyalbumchart'

# Once you're caching, could just make this a year or something.
NUM_SPANS = 2 * 52

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

def chart_url(user):
  return BASE_URL + '&method={0}&user={1}'.format(CHART_METHOD, user)

def artist_url(user, span):
  return BASE_URL + '&method={0}&user={1}&from={2}&to={3}'.format(ARTIST_METHOD, user, span['from'], span['to']) 

def album_url(user, span):
  return BASE_URL + '&method={0}&user={1}&from={2}&to={3}'.format(ALBUM_METHOD, user, span['from'], span['to']) 

def response_to_model(topLevelKey, titleKey, subtitleKey, response):
  chart = {
    'week': int(response[topLevelKey]['@attr']['from']),
    'entries': []
  }
  for entry in response[topLevelKey][titleKey]:
    model = {}
    model['title'] = entry['name']
    model['weight'] = int(entry['playcount'])
    if subtitleKey:
      model['subtitle'] = entry[subtitleKey]['#text']
    chart['entries'].append(model)
  return chart

# modelFactory should take a last.fm response and output a cute little generic struct
def template_model(modelFactory, urlFactory):
  user = request.args.get('user')
  charts = loads(urlopen(chart_url(user)).read())
  spans = sorted(charts['weeklychartlist']['chart'], key=lambda span : -int(span['from']))[:NUM_SPANS]
  urls = map(partial(urlFactory, user), spans)

  # Build a key agnostic model.
  model = map(modelFactory, getCharts(urls))
  model = sorted(model, key=lambda entry : -entry['week'])

  # Trim to only include entries that haven't appeared in more recent weeks.
  seen = set()
  result = []
  for chart in model:
    chart['entries'] = [entry for entry in chart['entries'] if not entry['title'] in seen]
    seen.update([entry['title'] for entry in chart['entries']])
  return render_template('charts.html', charts=model, user=user)

@app.template_filter('format_date')
def format_date(timestamp):
  return datetime.fromtimestamp(int(timestamp)).strftime('%b %d')

@app.route('/artists')
def artists():
  return template_model(partial(response_to_model, 'weeklyartistchart', 'artist', None), artist_url)

@app.route('/albums')
def albums():
  return template_model(partial(response_to_model, 'weeklyalbumchart', 'album', 'artist'), album_url)

@app.route('/films/<username>')
def films(username):
  if len(username) == 0:
    raise ValueError('username required')
  store = SqlFilmStore('/Users/chrisalfino/Projects/listening_history/film_store.sql')
  return render_template('films.html', log=store.get(username), user=username)

@app.route('/films/<username>/add')
def films_add(username):
  store = SqlFilmStore(SQL_FILE)
  if len(username) == 0:
    raise ValueError('username required')
  film = request.args['film']
  if len(film) > 0:
    try:
      watchTimeDt = parse(request.args['watch_time'])
      watchTimeSeconds = int(time.mktime(watchTimeDt.timetuple()))
      store.insert(username, film, watchTimeSeconds)
    except:
      pass
  return redirect('/films/' + username)

if __name__ == "__main__":
  app.run(debug=True)
