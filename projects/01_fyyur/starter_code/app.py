#----------------------------------------------------------------------------#
# Imports
#----------------------------------------------------------------------------#

import json
import dateutil.parser
import babel
from flask import Flask, render_template, request, Response, flash, redirect, url_for, jsonify
from flask_moment import Moment
from flask_sqlalchemy import SQLAlchemy
import logging
from logging import Formatter, FileHandler
from flask_wtf import Form
from forms import *
from flask_migrate import Migrate
from datetime import datetime, timedelta


#----------------------------------------------------------------------------#
# App Config.       
#----------------------------------------------------------------------------#

app = Flask(__name__)
moment = Moment(app)
app.config.from_object('config')
db = SQLAlchemy(app)
migrate = Migrate(app, db)


#----------------------------------------------------------------------------#
# Models.
#----------------------------------------------------------------------------#


# Many-to-many relationship between Venue and Artist models using artist_venue table object.
# one-to-many relationship between Artist and Show models.
# one-to-many relationship between Venue and Show models.

class Venue(db.Model):
    __tablename__ = 'Venue'

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String)
    city = db.Column(db.String(120))
    state = db.Column(db.String(120))
    address = db.Column(db.String(120))
    phone = db.Column(db.String(120))
    image_link = db.Column(db.String(500), default='/static/default.jpg')
    facebook_link = db.Column(db.String(120))
    genres = db.Column(db.String(500))
    website = db.Column(db.String(120))
    seeking_talent = db.Column(db.Boolean())
    seeking_description = db.Column(db.String(120))
    shows = db.relationship('Show', backref='venue', lazy=True, cascade="all, delete")
    def __repr__(self):
        return f'<Venue id:{self.id}  name:{self.name}, city:{self.city}, state:{self.state} address:{self.address}, phone:{self.phone}, image_link:{self.image_link}, facebook_link:{self.facebook_link}, genres:{self.genres}, website:{self.website}, seeking_talent:{self.seeking_talent}, seeking_description:{self.seeking_description} >'


class Artist(db.Model):
    __tablename__ = 'Artist'

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String)
    city = db.Column(db.String(120))
    state = db.Column(db.String(120))
    phone = db.Column(db.String(120))
    genres = db.Column(db.String(120))
    image_link = db.Column(db.String(500), default='/static/default.jpg')
    facebook_link = db.Column(db.String(120))
    genres = db.Column(db.String(500))
    website = db.Column(db.String(120))
    seeking_venue = db.Column(db.Boolean)
    seeking_description = db.Column(db.String(120))
    shows = db.relationship('Show', backref='artist', lazy=True, cascade="all, delete")
    def __repr__(self):
        return f'<Artist id:{self.id}, name:{self.name}, city:{self.city}, state:{self.state}, phone:{self.phone}, image_link:{self.image_link}, facebook_link:{self.facebook_link}, genres:{self.genres}, website:{self.website}, seeking_venue:{self.seeking_venue}, seeking_description:{self.seeking_description}>'
  

    artist_venue = db.Table('artist_venue',
        db.Column('artist_id', db.Integer, db.ForeignKey('Artist.id'), primary_key=True),
        db.Column('venue_id', db.Integer, db.ForeignKey('Venue.id'), primary_key=True)
    )
    venues = db.relationship('Venue', secondary=artist_venue, backref=db.backref('artists', lazy=True), cascade="all, delete")
  

class Show(db.Model):
  __tablename__ = 'Show'

  id = db.Column(db.Integer, primary_key=True)
  artist_id = db.Column(db.Integer, db.ForeignKey('Artist.id'), nullable=False)
  venue_id = db.Column(db.Integer, db.ForeignKey('Venue.id'), nullable=False)
  show_date = db.Column(db.DateTime)
  image_link = db.Column(db.String(500), default='/static/default.jpg')
  def __repr__(self):
        return f'< Show id:{self.id}, artist_id:{self.artist_id}, venue_id:{self.venue_id}, show_date:{self.show_date}, image_link:{self.image_link}>'


#----------------------------------------------------------------------------#
# Filters.
#----------------------------------------------------------------------------#

def format_datetime(value, format='medium'):
  date = dateutil.parser.parse(value)
  if format == 'full':
      format="EEEE MMMM, d, y 'at' h:mma"
  elif format == 'medium':
      format="EE MM, dd, y h:mma"
  return babel.dates.format_datetime(date, format)

app.jinja_env.filters['datetime'] = format_datetime

#----------------------------------------------------------------------------#
# Controllers.
#----------------------------------------------------------------------------#

@app.route('/')
def index():
  return render_template('pages/home.html')


#  Venues
#  ----------------------------------------------------------------


# Show all venues grouped by city and state fields

@app.route('/venues')
def venues():

  upcoming_shows = Venue.query.join(Show).filter( Show.show_date > datetime.now()).count()
  venues = Venue.query.all()

# Creating map in terms of grouping the result by index and state,
# index and state are the map key and the venues are the value.

  data = []
  idx_map = {}
  for venue in venues:
    key = venue.city+'-'+venue.state
    if key in idx_map:
      idx = idx_map[key]
      data[idx]['venues'].append({
        'id': venue.id,
        'name': venue.name,
        'num_upcoming_shows': Venue.query.join(Show).filter( Show.show_date > datetime.now()).filter(Venue.id == venue.id).count()
      })
    else:
      data.append({
        'city': venue.city,
        'state': venue.state,
        'venues': [{
          'id': venue.id,
          'name': venue.name,
          'num_upcoming_shows': Venue.query.join(Show).filter( Show.show_date > datetime.now()).filter(Venue.id == venue.id).count()
        }]
      })

      idx_map[key] =len(data)-1

  return render_template('pages/venues.html', areas=data)



@app.route('/venues/search', methods=['POST'])
def search_venues():

# Search on artists with partial and insensitive string search.
  data = []
  search_term = request.form.get('search_term', '')
  venues = Venue.query.filter(Venue.name.ilike(f'%{search_term}%'))
  venueCount = venues.count()
  for venue in venues:
    data.append(formated_venue(venue))
  response = {
    "count": venueCount,
    "data": data
  }
  return render_template('pages/search_venues.html', results=response, search_term=request.form.get('search_term', ''))


@app.route('/venues/<int:venue_id>')
def show_venue(venue_id):

  # shows the venue page with the given venue_id
  # Declaring upcoming and past show arrays and fill them during loops with proper data(filtered by sqlalchemy query methods)

  data = {}
  past_shows = []
  upcoming_shows = []

  venue = Venue.query.filter_by(id=venue_id).first()

  upcoming_shows_artists = Artist.query.join(Show).filter(Show.venue_id == venue_id).filter(Show.show_date >  datetime.now()).all()
  for show_artist in upcoming_shows_artists:
    upcoming_shows.append(formated_show_artists(show_artist, venue_id))

  past_shows_artists = Artist.query.join(Show).filter(Show.id == venue_id).filter(Show.show_date <  datetime.now()).all()
  for show_artist in past_shows_artists:
    past_shows.append(formated_show_artists(show_artist, venue_id))

  num_upcoming_shows = Venue.query.join(Show).filter( Show.show_date > datetime.now()).filter(Venue.id == venue.id).count()
  num_past_shows = Venue.query.join(Show).filter( Show.show_date < datetime.now()).filter(Venue.id == venue.id).count()

  data = {
    "id": venue.id,
    "name": venue.name,
    "genres": venue.genres.split(","),
    "address": venue.address, 
    "city": venue.city,
    "state": venue.state,
    "phone": venue.phone,
    "website": venue.website,
    "facebook_link": venue.facebook_link,
    "seeking_talent": venue.seeking_talent,
    "seeking_description": venue.seeking_description,
    "image_link": venue.image_link,
    "past_shows": past_shows ,
    "upcoming_shows": upcoming_shows,
    "past_shows_count": num_past_shows,
    "upcoming_shows_count": num_upcoming_shows,
  }

  return render_template('pages/show_venue.html', venue=data)


def formated_show_artists(show_artist, venue_id):
  artistId = show_artist.id
  time = Show.query.filter(Show.artist_id == artistId).filter(Show.venue_id == venue_id).first()
  print(time)
  return {
  'artist_id': show_artist.id,
  'artist_name': show_artist.name,
  'artist_image_link': show_artist.image_link,
  'start_time': f"{time.show_date}"
  }
#  Create Venue
#  ----------------------------------------------------------------

@app.route('/venues/create', methods=['GET'])
def create_venue_form():
  form = VenueForm()
  return render_template('forms/new_venue.html', form=form)

@app.route('/venues/create', methods=['POST'])
def create_venue_submission():

  # Take venue data from the form(the form called this endpoint), 
  # and make new instance of venue model,
  # save it in the database,
  # if error occurred, rollback the committed changes and inform the user using flash.

  name = request.form.get('name', '')
  city = request.form.get('city', '')
  state = request.form.get('state', '')
  phone = request.form.get('phone', '')
  genres = ','.join(request.form.getlist('genres'))
  address = request.form.get('address', '')
  facebook_link = request.form.get('facebook_link', '')


  # on successful db insert
  try:
    venue = Venue(name=name, city=city, state=state, phone=phone, genres=genres, address=address, facebook_link=facebook_link)
    db.session.add(venue)
    db.session.commit()
    flash('Venue ' + request.form['name'] + ' was successfully listed!')
  # on unsuccessful db insert
  except:
    db.session.rollback()
    flash('An error occurred. Venue ' + request.form['name'] + ' could not be listed.')
  finally:
    db.session.close()

  return render_template('pages/home.html')

@app.route('/venues/<venue_id>', methods=['DELETE'])
def delete_venue(venue_id):

  # Get desired venue by id 
  # delete the returned venue and commit changes
  # if errors occurred rollback changes and notify the user.


  try:
    ven = Venue.query.get(venue_id) 
    db.session.delete(ven)
    db.session.commit()
    flash('Venue deleted successfully!')
  except:
    db.session.rollback()
    flash('An error occurred. Venue could not be deleted.')
  finally:
    db.session.close()

  return jsonify({})

#  Artists
#  ----------------------------------------------------------------
@app.route('/artists')
def artists():

  # Return all artists name

  data = []
  artists = Artist.query.all()
  for artist in artists:
    data.append({
       "id": artist.id,
       "name": artist.name,
    })
  
  return render_template('pages/artists.html', artists=data)

@app.route('/artists/search', methods=['POST'])
def search_artists():

  # Search on artists with partial and ase-insensitive string search.
  

  data = []
  search_term = request.form.get('search_term', '')
  artists = Artist.query.filter(Artist.name.ilike(f'%{search_term}%'))
  artistCount = artists.count()
  for artist in artists:
    data.append({
      "id": artist.id,
      "name": artist.name,
      "num_upcoming_shows": Artist.query.join(Show).filter(Show.show_date > datetime.now()).count()
    })
  response = {
    "count": artistCount,
    "data": data
  }
 
  return render_template('pages/search_artists.html', results=response, search_term=request.form.get('search_term', ''))

@app.route('/artists/<int:artist_id>')
def show_artist(artist_id):

  # Return artist details with the given id
  # Declaring upcoming and past show arrays and fill them during loops with proper data(filtered by sqlalchemy query methods)

  data = {}
  past_shows = []
  upcoming_shows = []

  artist = Artist.query.filter_by(id=artist_id).first()
  
  upcoming_shows_venues = db.session.query(Venue, Show).join(Show).filter(Show.artist_id == artist_id).filter(Show.show_date > datetime.now()).all()
  for show_venue in upcoming_shows_venues:
    upcoming_shows.append({
      "venue_id": show_venue.Venue.id ,
      "venue_name": show_venue.Venue.name,
      "venue_image_link":show_venue.Venue.image_link,
      "start_time": f'{show_venue.Show.show_date}'
    })

  past_shows_venues = db.session.query(Venue, Show).join(Show).filter(Show.artist_id == artist_id).filter(Show.show_date <  datetime.now()).all()
  for show_venue in past_shows_venues:
    past_shows.append({
      "venue_id": show_venue.Venue.id ,
      "venue_name": show_venue.Venue.name,
      "venue_image_link":show_venue.Venue.image_link,
      "start_time": f'{show_venue.Show.show_date}'
    })

  num_upcoming_shows = db.session.query(Venue, Show).join(Show).filter(Show.artist_id == artist_id).filter(Show.show_date >  datetime.now()).count()
  num_past_shows =db.session.query(Venue, Show).join(Show).filter(Show.artist_id == artist_id).filter(Show.show_date <  datetime.now()).count()


  data={
    "id": artist.id,
    "name": artist.name,
    "genres": artist.genres.split(","),
    "city": artist.city,
    "state": artist.state,
    "phone": artist.phone,
    "website": artist.website ,
    "facebook_link": artist.facebook_link,
    "seeking_venue": artist.seeking_venue,
    "seeking_description": artist.seeking_description,
    "image_link": artist.image_link,
    "past_shows": past_shows,
    "upcoming_shows": upcoming_shows,
    "past_shows_count": num_past_shows,
    "upcoming_shows_count": num_upcoming_shows,
  }

  return render_template('pages/show_artist.html', artist=data)

#  Update
#  ----------------------------------------------------------------
@app.route('/artists/<int:artist_id>/edit', methods=['GET'])
def edit_artist(artist_id):

  # Pass the artist with given id to fill the artist form for updating any of its data
  artist = Artist.query.filter_by(id=artist_id).first()
  form = ArtistForm()
  return render_template('forms/edit_artist.html', form=form, artist=artist)

@app.route('/artists/<int:artist_id>/edit', methods=['POST'])
def edit_artist_submission(artist_id):


  # Take artist data from the form(the form called this endpoint), 
  # and make updates to the artist model,
  # save it in the database.

  artist = Artist.query.filter_by(id=artist_id).first()

  artist.name = request.form.get('name', '')
  artist.genres = ','.join(request.form.getlist('genres'))
  artist.city = request.form.get('city', '')
  artist.state = request.form.get('state', '')
  artist.phone = request.form.get('phone', '')
  artist.facebook_link = request.form.get('facebook_link', '')

  db.session.commit()

  return redirect(url_for('show_artist', artist_id=artist_id))

@app.route('/venues/<int:venue_id>/edit', methods=['GET'])
def edit_venue(venue_id):
  # Pass the venue with given id to fill the venue form for updating any of its data.

  venue = Venue.query.filter_by(id=venue_id).first()
  form = VenueForm()
  return render_template('forms/edit_venue.html', form=form, venue=venue)

@app.route('/venues/<int:venue_id>/edit', methods=['POST'])
def edit_venue_submission(venue_id):

  # Take artist data from the form(the form called this endpoint), 
  # and make updates to the artist model,
  # save it in the database.

  venue = Venue.query.filter_by(id=venue_id).first()

  venue.name = request.form.get('name', '')
  venue.genres = ','.join(request.form.getlist('genres'))
  venue.city = request.form.get('city', '')
  venue.state = request.form.get('state', '')
  venue.phone = request.form.get('phone', '')
  venue.facebook_link = request.form.get('facebook_link', '')

  db.session.commit()

  return redirect(url_for('show_venue', venue_id=venue_id))

#  Create Artist
#  ----------------------------------------------------------------

@app.route('/artists/create', methods=['GET'])
def create_artist_form():
  form = ArtistForm()
  return render_template('forms/new_artist.html', form=form)

@app.route('/artists/create', methods=['POST'])
def create_artist_submission():

  # Take artist data from the form(the form called this endpoint), 
  # and make new instance of artist model,
  # save it in the database,
  # if error occurred, rollback the committed changes and inform the user using flash.

  

  name = request.form.get('name', '')
  city = request.form.get('city', '')
  state = request.form.get('state', '')
  phone = request.form.get('phone', '')
  genres = ','.join(request.form.getlist('genres'))
  facebook_link = request.form.get('facebook_link', '')


  # on successful db insert.
  try:
    artist = Artist(name=name, city=city, state=state, phone=phone, genres=genres, facebook_link=facebook_link)
    db.session.add(artist)
    db.session.commit()
    flash('Artist ' + request.form['name'] + ' was successfully listed!')
  # on unsuccessful db insert.
  except:
    db.session.rollback()
    flash('An error occurred. Venue ' + request.form['name'] + ' could not be listed.')
  finally:
    db.session.close()

  return render_template('pages/home.html')


#  Shows
#  ----------------------------------------------------------------

@app.route('/shows')
def shows():

  # displays list of shows at /shows


  data = []
  shows = db.session.query(Show, Artist, Venue).join(Artist).join(Venue).all()
  for show in shows:
    data.append({
    "venue_id": show.Venue.id,
    "venue_name": show.Venue.name,
    "artist_id": show.Artist.id,
    "artist_name": show.Artist.name,
    "artist_image_link": show.Artist.image_link,
    "start_time": f'{show.Show.show_date}'
    })
  return render_template('pages/shows.html', shows=data)

@app.route('/shows/create')
def create_shows():
  # renders form. do not touch.
  form = ShowForm()
  return render_template('forms/new_show.html', form=form)

@app.route('/shows/create', methods=['POST'])
def create_show_submission():

  # Take show data from the form(the form called this endpoint), 
  # and make new instance of show model,
  # save it in the database,
  # if error occurred, rollback the committed changes and inform the user using flash.


  artist_id = request.form.get('artist_id', '')
  venue_id = request.form.get('venue_id', '')
  start_time = request.form.get('start_time', '')

  try:
    show = Show(artist_id=artist_id, venue_id=venue_id, show_date=start_time)
    db.session.add(show)
    db.session.commit()
    flash('Show was successfully listed!')
  # on unsuccessful db insert.
  except:
    db.session.rollback()
    flash('An error occurred. The show could not be listed.')
  finally:
    db.session.close()

  return render_template('pages/home.html')

@app.errorhandler(404)
def not_found_error(error):
    return render_template('errors/404.html'), 404

@app.errorhandler(500)
def server_error(error):
    return render_template('errors/500.html'), 500


if not app.debug:
    file_handler = FileHandler('error.log')
    file_handler.setFormatter(
        Formatter('%(asctime)s %(levelname)s: %(message)s [in %(pathname)s:%(lineno)d]')
    )
    app.logger.setLevel(logging.INFO)
    file_handler.setLevel(logging.INFO)
    app.logger.addHandler(file_handler)
    app.logger.info('errors')

#----------------------------------------------------------------------------#
# Launch.
#----------------------------------------------------------------------------#

# Default port:
if __name__ == '__main__':
    app.run()

# Or specify port manually:
'''
if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port)
'''
