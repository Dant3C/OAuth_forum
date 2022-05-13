from flask import Flask, redirect, url_for, session, request, jsonify, render_template, flash, Markup
from flask_oauthlib.client import OAuth
from flask_oauthlib.contrib.apps import github #import to make requests to GitHub's OAuth
from flask import render_template
from datetime import datetime

import pymongo
import os
import sys
import pprint

app = Flask(__name__)

app.debug = True #Change this to False for production
os.environ['OAUTHLIB_INSECURE_TRANSPORT'] = '1' #Remove once done debugging

app.secret_key = os.environ['SECRET_KEY'] #used to sign session cookies
oauth = OAuth(app)
oauth.init_app(app) #initialize the app to be able to make requests for user information

#Set up GitHub as OAuth provider
github = oauth.remote_app(
    'github',
    consumer_key=os.environ['GITHUB_CLIENT_ID'], #your web app's "username" for github's OAuth
    consumer_secret=os.environ['GITHUB_CLIENT_SECRET'],#your web app's "password" for github's OAuth
    request_token_params={'scope': 'user:email'}, #request read-only access to the user's email.  For a list of possible scopes, see developer.github.com/apps/building-oauth-apps/scopes-for-oauth-apps
    base_url='https://api.github.com/',
    request_token_url=None,
    access_token_method='POST',
    access_token_url='https://github.com/login/oauth/access_token',  
    authorize_url='https://github.com/login/oauth/authorize' #URL for github's OAuth login
)

# Connect to MongoDB
connection_string = os.environ["MONGO_CONNECTION_STRING"]
db_name = os.environ["MONGO_DBNAME"]

client = pymongo.MongoClient(connection_string)
db = client[db_name]
collection = db['col-1'] #1. put the name of your collection in the quotes


@app.context_processor
def inject_logged_in():
    return {"logged_in":('github_token' in session)}

@app.route('/')
def home():
    return render_template('home.html')

#redirect to GitHub's OAuth page and confirm callback URL
@app.route('/login', methods=['GET', 'POST'])
def login():   
    return github.authorize(callback=url_for('authorized', _external=True, _scheme='http')) #set as "https" for final version

@app.route('/logout')
def logout():
    session.clear()
    flash('You were logged out.')
    return redirect('/')

@app.route('/login/authorized')
def authorized():
    resp = github.authorized_response()
    if resp is None:
        session.clear()
        flash('Access denied: reason=' + request.args['error'] + ' error=' + request.args['error_description'] + ' full=' + pprint.pformat(request.args), 'error')      
    else:
        try:
            session['github_token'] = (resp['access_token'], '') #save the token to prove that the user logged in
            session['user_data']=github.get('user').data
            #pprint.pprint(vars(github['/email']))
            #pprint.pprint(vars(github['api/2/accounts/profile/']))
            flash('You were successfully logged in as ' + session['user_data']['login'] + '.')
        except Exception as inst:
            session.clear()
            print(inst)
            flash('Unable to login, please try again.', 'error')
    return redirect('/')
    
@app.route('/submitted', methods=['POST', 'GET'])
def submit_post():
    if 'user_data' in session:
        username = str(session['user_data']['login'])
        post_text = request.form['post_text']
        now = datetime.now()
        date_time = now.strftime("%d/%m/%Y %H:%M:%S")
        # Datetime is a string in the format MM/DD/YEAR hh/mm/ss; 
        # 'post_level' refers to the hierarchy of posts/replies '0' refers to a parent post, 1 would be a reply to the parent, 2 would be a reply to that reply, etc. etc.
        # Use 'post_level' and the unique _id of each document to figure out how much to 'indent' the posts, also use the date and time to order them correctly
        document = {'username': username, 'post_text': post_text, 'date_time': date_time, 'post_level': 0}  
        try:
            collection.insert_one(document)
        except Exception as e:
            print("Can't post, try again. error: ", e)
    else:
        flash('You must be logged in to post.')
    return render_template('page1.html', posts = get_all_posts())

@app.route('/search')
def filter_posts():
    query = request.args['search_query']
    option = request.args['option']
    username = ""
    post = ""
    id = ""
    filtered_posts = ""
    # If search by username is selected, search for all documents tagged with the username
    if option == "username":
        for document in collection.find({'username': {"$regex" : query, '$options' : 'i'}}):
            username = document['username']
            post = document['post_text']
            id = document['_id']
            filtered_posts = filtered_posts + Markup("<thead> <tr> <th> " + username + " </th> <th> " + post + " </th> </tr> </thead>")
        return render_template('page1.html', posts = filtered_posts)
    elif option == "text":
        for document in collection.find({"post_text" : {"$regex" : query, '$options' : 'i'}}):
            username = document['username']
            post = document['post_text']
            id = document['_id']
            filtered_posts = filtered_posts + Markup("<thead> <tr> <th> " + username + " </th> <th> " + post + " </th> </tr> </thead>")
        return render_template('page1.html', posts = filtered_posts)
    else:
        return render_template('page1.html', posts = get_all_posts())
    

@app.route('/clearSearch')
def clear_filter():
    return render_template('page1.html', posts = get_all_posts())
    
@app.route('/page1')
def renderPage1():
    return render_template('page1.html', posts = get_all_posts())
    
@app.route('/googleb4c3aeedcc2dd103.html')
def render_google_verification():
    return render_template('googleb4c3aeedcc2dd103.html')

@github.tokengetter
def get_github_oauth_token():
    return session['github_token']

#				<thead>
#					<tr>
#						<th>
#							Username
#						</th>
#						<th>
#							Message
#						</th>
#					</tr>
#				</thead>

def get_all_posts():
    username = ""
    post = ""
    id = ""
    posts = ""
    for document in collection.find():
        username = document['username']
        post = document['post_text']
        id = document['_id']
        posts = posts + Markup("<thead> <tr> <th> " + username + " </th> <th> " + post + " </th> </tr> </thead>")
    return posts

if __name__ == '__main__':
    app.run()
