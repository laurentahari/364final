###############################
####### SETUP (OVERALL) #######
###############################

## Import statements
# Import statements
import os
from flask import Flask, render_template, session, redirect, url_for, flash, request
from flask_wtf import FlaskForm
from flask_script import Manager, Shell
from wtforms import StringField, PasswordField, BooleanField, SelectField, SelectMultipleField, SubmitField, IntegerField, ValidationError # Note that you may need to import more here! Check out examples that do what you want to figure out what.
from wtforms.validators import Required, Length, Email, Regexp, EqualTo # Here, too
from flask_sqlalchemy import SQLAlchemy
from flask_migrate import Migrate, MigrateCommand
from flask_login import LoginManager, login_required, logout_user, login_user, UserMixin, current_user
from werkzeug.security import generate_password_hash, check_password_hash
import json, requests, omdb
from sqlalchemy import desc

## App setup code
app = Flask(__name__)
app.debug = True
app.use_reloader = True
#app.config["SQLALCHEMY_DATABASE_URI"] = "postgresql://localhost/SI364midterm"
app.config["SQLALCHEMY_DATABASE_URI"] = "postgres://localhost/taharil364final"
## All app.config values
app.config['SECRET_KEY'] = 'hard to guess string from SI364'
app.config['SQLALCHEMY_COMMIT_ON_TEARDOWN'] = True
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

## Statements for db setup (and manager setup if using Manager)
manager = Manager(app)
db = SQLAlchemy(app)
migrate = Migrate(app, db)
manager.add_command('db', MigrateCommand)

login_manager = LoginManager()
login_manager.session_protection = 'strong'
login_manager.login_view = 'login'
login_manager.init_app(app)

API_KEY = "00fe092a5217b7f9031d8db132e0fdaa"
HOST_URL = "https://api.themoviedb.org/3"
MOVIE_URL = "/search/movie"
GENRE_URL = "/genre/movie/list"


##################
##### MODELS #####
##################
'''
class Person(db.Model):
    __tablename__ = "People"
    id = db.Column(db.Integer,primary_key=True)
    person = db.Column(db.String(64))

    def __repr__(self):
        return "{} (ID: {})".format(self.person, self.id)
'''

movie_collection = db.Table('user_movies',
    db.Column('movie_id', db.Integer, db.ForeignKey("Movie_Titles.id"), primary_key=True),
    db.Column('favorite_id', db.Integer, db.ForeignKey("Favorite_Collection.id"), primary_key=True)
)

genre_movies = db.Table('genre_movies',
    db.Column('genre_id', db.Integer, db.ForeignKey("Genres.id"), primary_key=True),
    db.Column('movie_id', db.Integer, db.ForeignKey("Movie_Titles.id"), primary_key=True)
)

class User(UserMixin, db.Model):
    __tablename__ = "Users"
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(255), unique=True, index=True)
    email = db.Column(db.String(64), unique=True, index=True)
    password_hash = db.Column(db.String(128))
    collections = db.relationship('FavoriteCollection', backref="owner")

    @property
    def password(self):
        raise AttributeError('password is not a readable attribute')

    @password.setter
    def password(self, password):
        self.password_hash = generate_password_hash(password)

    def verify_password(self, password):
        return check_password_hash(self.password_hash, password)

@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id)) # returns User object or None

class Movie(db.Model):
    __tablename__ = "Movie_Titles"
    id = db.Column(db.Integer, primary_key = True)
    movie = db.Column(db.String(64))
    #year = db.Column(db.Integer)
    plot = db.Column(db.String(1024))
    #directors = db.relationship('Director', backref = 'Title')
    year_id = db.Column(db.Integer, db.ForeignKey('Movie_Year.year'))
    #users = db.relationship('User', secondary=user_movies, lazy="dynamic",
    #        backref=db.backref('fav_movies', lazy=True))

    def __repr__(self):
        return "{0} ({1}) : {2}".format(self.movie, self.year, self.plot)

class FavoriteCollection(db.Model):
    __tablename__ = "Favorite_Collection"
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(255))
    owner_id = db.Column(db.Integer, db.ForeignKey('Users.id'))
    movies = db.relationship('Movie', secondary=movie_collection, lazy="dynamic",
           backref=db.backref('collections', lazy=True))

class Year(db.Model):
    __tablename__ = "Movie_Year"
    year = db.Column(db.Integer, primary_key=True)
    movies = db.relationship('Movie', backref='year')

'''
class Director(db.Model):
    __tablename__="Movie_Directors"
    id = db.Column(db.Integer, primary_key=True)
    directorname = db.Column(db.String(64))
    #titleid = db.Column(db.Integer, db.ForeignKey("Movie_Titles.id"))
    movies = db.relationship('Movie', backref='director')
    users = db.relationship('User', secondary=user_directors, lazy="dynamic",
            backref=db.backref('fav_directors', lazy=True))

    def __repr__(self):
        return "{1} (ID: {0})".format(self.id, self.directorname)
'''
class Genre(db.Model):
    __tablename__ = "Genres"
    id = db.Column(db.Integer, primary_key=True)
    genre = db.Column(db.String(64))
    movies = db.relationship("Movie", secondary=genre_movies, lazy="dynamic",
            backref=db.backref("genre", lazy=True))

######################################
######## HELPER FXNS (If any) ########
######################################

def save_titles(db_session, titlename):
    #x = db.session.query(Title).filter_by(title=titlename).first()
    #url = "http://www.omdbapi.com/?apikey=5d008589&t={}".format(titlename)
    url = HOST_URL + MOVIE_URL
    params = {'api_key': API_KEY,
        'language': 'en-US',
        'query': titlename,
        'page': 1,
        'include_adult': 'false'
    }
    get_request = requests.get(url, params=params).json()['results'][0]
    x = Movie.query.filter_by(movie=get_request["original_title"]).first()
    if not x:
        update_genre()
        g = [get_genre_by_id(id) for id in get_request['genre_ids']]
        y = get_or_create_year(int(get_request['release_date'][:4]))
        x = Movie(
            movie=get_request['original_title'],
            plot=get_request['overview'],
            year=y
        )
        for genre in g:
            genre.movies.append(x)
        db.session.add(x)
        db.session.commit()
        flash("The movie was successfully added!")

    else:
        flash ("This movie already exists")
        return redirect(url_for('display_all_titles'))

def get_or_create_year(check):
    y = Year.query.filter_by(year=check).first()
    if not y:
        y = Year(year=check)
        db.session.add(y)
        db.session.commit()
    return y

def update_genre():
    url = HOST_URL + GENRE_URL
    params = {
        'api_key': API_KEY,
        'language': 'en-US'
    }
    get_request = requests.get(url, params=params).json()#['genres']
    get_request = get_request['genres']
    for g in get_request:
        check = Genre.query.filter_by(id=g['id']).first()
        if not check:
            check = Genre(id=g['id'], genre=g['name'])
            db.session.add(check)
            db.session.commit()

def get_genre_by_id(id):
    g = Genre.query.filter_by(id=id).first()
    return g

def get_movie_by_id(id):
    """Should return gif object or None"""
    m = Movie.query.filter_by(id=id).first()
    return m

def get_or_create_collection(name, current_user, movie_list=[]):
    collection = FavoriteCollection.query.filter_by(name=name,owner=current_user).first()
    if not collection:
        collection = FavoriteCollection(name=name, owner=current_user, movies=movie_list)
        db.session.add(collection)
        db.session.commit()
    return collection
'''
def save_director(db_session, directorname):
    y = db.session.query(Director).filter_by(directorname = directorname).first()
    if y:
        flash("This director has already been added")
        return redirect(url_for('display_all_directors'))

    else:
        director = Director(directorname = directorname)
        db_session.add(director)
        db_session.commit
        flash('The director was successfully added!')
        return redirect(url_for('index'))
'''

###################
###### FORMS ######
###################

class RegistrationForm(FlaskForm):
    email = StringField('Email:', validators=[Required(),Length(1,64),Email()])
    username = StringField('Username:',validators=[Required(),Length(1,64),Regexp('^[A-Za-z][A-Za-z0-9_.]*$',0,'Usernames must have only letters, numbers, dots or underscores')])
    password = PasswordField('Password:',validators=[Required(),EqualTo('password2',message="Passwords must match")])
    password2 = PasswordField("Confirm Password:",validators=[Required()])
    submit = SubmitField('Register User')

    #Additional checking methods for the form
    def validate_email(self,field):
        if User.query.filter_by(email=field.data).first():
            raise ValidationError('Email already registered.')

    def validate_username(self,field):
        if User.query.filter_by(username=field.data).first():
            raise ValidationError('Username already taken')

# Provided
class LoginForm(FlaskForm):
    email = StringField('Email', validators=[Required(), Length(1,64), Email()])
    password = PasswordField('Password', validators=[Required()])
    remember_me = BooleanField('Remember Me')
    submit = SubmitField('Log In')
'''
class NameForm(FlaskForm):
    person = StringField("Please enter your name ",validators=[Required()])
    submit = SubmitField()

    def validate_person(self,field):
        if field.data[0] == "@":
            raise ValidationError("This is not a valid name (do not use an @ symbol).")
'''

class TitleForm(FlaskForm):
    titlename = StringField("Please enter the name of a movie", validators=[Required(),Length(min=1,max=280)])
    submit = SubmitField('Submit')

    def validate_titlename(self,field):
        if field.data[0] == "@" :
            raise ValidationError("This is not a valid title")

        if field.data[0] == "!" :
            raise ValidationError("This is not a valid title")
'''
class DirectorForm(FlaskForm):
    directorname = StringField("Please enter the name of a director", validators=[Required(),Length(min=1,max=280)])
    submit = SubmitField('Submit')
'''

class GenreForm(FlaskForm):
    genre = SelectField("Choose a genre to search", coerce=int)
    submit = SubmitField("Search")

class YearForm(FlaskForm):
    year = SelectField("Choose a year to search", coerce=int)
    submit = SubmitField("Search")

class CollectionCreateForm(FlaskForm):
    name = StringField('Collection Name',validators=[Required()])
    movie_picks = SelectMultipleField('Movies to include', coerce=int)
    submit = SubmitField("Create Collection")

class UpdateColForm(FlaskForm):
    name = StringField("Please enter a new name", validators=[Required()])
    update = SubmitField("Update")

class UpdateButtonForm(FlaskForm):
    update = SubmitField("Update")

class DeleteButtonForm(FlaskForm):
    delete = SubmitField("Delete")

#######################
###### VIEW FXNS ######
#######################
'''
#need to edit below this
@app.route('/people')
def people():
    form = NameForm() # User should be able to enter name after name and each one will be saved, even if it's a duplicate! Sends data with GET
    if request.args:
        person = request.args['person']
        newperson = Person(person=person)
        db.session.add(newperson)
        db.session.commit()
    return render_template('name_example.html', form=form, people=Person.query.all())
'''
## Code to run the application...

# Put the code to do so here!
# NOTE: Make sure you include the code you need to initialize the database structure when you run the application!

#error handler routes

@app.errorhandler(404)
def page_not_found(e):
    return render_template('404.html'), 404

@app.errorhandler(500)
def internal_server_error(e):
    return render_template('500.html'), 500
#initialize the database

@app.route('/', methods=['GET', 'POST'])
def index():
    form = TitleForm()
    return render_template('index.html',form = form)

@app.route('/login',methods=["GET","POST"])
def login():
    form = LoginForm()
    if form.validate_on_submit():
        user = User.query.filter_by(email=form.email.data).first()
        if user is not None and user.verify_password(form.password.data):
            login_user(user, form.remember_me.data)
            return redirect(request.args.get('next') or url_for('index'))
        flash('Invalid username or password.')
    return render_template('login.html',form=form)

@app.route('/logout')
@login_required
def logout():
    logout_user()
    flash('You have been logged out')
    return redirect(url_for('index'))

@app.route('/register',methods=["GET","POST"])
def register():
    form = RegistrationForm()
    if form.validate_on_submit():
        user = User(email=form.email.data,username=form.username.data,password=form.password.data)
        db.session.add(user)
        db.session.commit()
        flash('You can now log in!')
        return redirect(url_for('login'))
    return render_template('register.html',form=form)

@app.route('/create_collection',methods=["GET","POST"])
@login_required
def create_collection():
    form = CollectionCreateForm()
    movies = Movie.query.all()
    choices = [(m.id, m.movie) for m in movies]
    form.movie_picks.choices = choices
    form.movie_picks.coerce = int
    if form.validate_on_submit():
        get_movies = [get_movie_by_id(id) for id in form.movie_picks.data]
        collection = get_or_create_collection(form.name.data, current_user, get_movies)
        return redirect(url_for("collections"))
    return render_template('create_collection.html',form=form)

@app.route('/collections',methods=["GET","POST"])
@login_required
def collections():
    formd = DeleteButtonForm()
    formu = UpdateButtonForm()
    collections = FavoriteCollection.query.filter_by(owner=current_user).all()
    return render_template("collections.html", collections=collections, formd=formd, formu=formu)

@app.route('/update/<col>',methods=["GET","POST"])
def update(col):
    form = UpdateColForm()
    if form.validate_on_submit():
        updateItem = FavoriteCollection.query.filter_by(id=col).first()
        updateItem.name = form.name.data
        db.session.commit()
        flash("Updated name of collection")
        return redirect(url_for('collections'))
    return render_template('update_collection.html', form=form, colID=col)

@app.route('/delete/<col>',methods=["GET","POST"])
def delete(col):
    l = FavoriteCollection.query.filter_by(id=col)
    name = l.first().name
    db.session.delete(l.first())
    db.session.commit()
    flash("Deleted list " + name)
    return redirect(url_for('collections'))

@app.route('/collection/<id_num>')
def single_collection(id_num):
    id_num = int(id_num)
    collection = FavoriteCollection.query.filter_by(id=id_num).first()
    movies = collection.movies#.all()
    return render_template('collection.html',collection=collection, movies=movies)

@app.route('/view_all_years')
def display_all_years():
    years = Year.query.order_by(desc(Year.year)).all()
    return render_template('view_all_years.html', years=years)

@app.route('/year/<yid>')
def single_year(yid):
    movies = Year.query.filter_by(year=yid).first().movies
    return render_template('year.html', movies=movies, yid=yid)

@app.route('/view_all_titles', methods = ['GET','POST'])
def display_all_titles():
    form = TitleForm()
    if request.args:
        titlename = request.args.get('titlename')
        save_titles(db.session, titlename)
    error = [l for l in form.errors.values()]
    if len(error) > 0:
        flash("ERROR IN SUBMISSION - " + str(error))
    movies = Movie.query.all()
    return render_template('view_all_titles.html', form = form, view_all_titles = movies)


if __name__ == '__main__':
    db.create_all() # Will create any defined models when you run the application
    app.run(use_reloader=True,debug=True) # The usual
