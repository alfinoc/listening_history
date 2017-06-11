from sqlite3 import connect
import time

"""
Setup:

CREATE TABLE film_log (
  Id integer primary key autoincrement,
  User varchar(255),
  Film varchar(255),
  WatchTime int,
  SubmitTime int,
  Latitude real,
  Longitude real
);

"""

SELECT_FMT = 'SELECT Id, User, Film, WatchTime, SubmitTime \
  FROM film_log WHERE User = ?'

INSERT_FMT = 'INSERT INTO film_log \
  (User, Film, WatchTime, SubmitTime, Latitude, Longitude) \
  VALUES (?, ?, ?, ?, ?, ?)'

DELETE_FMT = 'DELETE FROM film_log WHERE User = ? AND Id = ?'

def toDict(row):
  return dict(zip(('id', 'user', 'film', 'watch_time', 'submit_time'), row))

class SqlFilmStore:
  def __init__(self, sqlPath):
    self.store_ = connect(sqlPath)

  def insert(self, user, film, watchTime, position=(None, None)):
    submitTime = int(time.time())
    with self.store_:
      cursor = self.store_.cursor()
      values = (user, film, watchTime, submitTime) + position
      cursor.execute(INSERT_FMT, values)
      self.store_.commit()

  def get(self, user):
    with self.store_:
      cursor = self.store_.cursor()
      cursor.execute(SELECT_FMT, (user,))
      rows = cursor.fetchall()
    return map(toDict, rows)

  def remove(self, user, id):
    with self.store_:
      cursor = self.store_.cursor()
      cursor.execute(DELETE_FMT, (user, id))
      self.store_.commit()


