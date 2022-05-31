from flask import Flask, redirect, url_for, session, request, jsonify, render_template, flash, Markup
from flask_oauthlib.client import OAuth
from flask_oauthlib.contrib.apps import github #import to make requests to GitHub's OAuth
from flask import render_template
from datetime import datetime
from bson import ObjectId

import pymongo
import os
import sys
import pprint
from pymongo import MongoClient

app = Flask(__name__)

app.debug = False #Change this to False for production

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
collection = db['col-1'] 


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
            flash('You were successfully logged in as ' + session['user_data']['login'] + '.')
        except Exception as inst:
            session.clear()
            print(inst)
            flash('Unable to login, please try again.', 'error')
    return redirect('/')
    
@app.route('/submitted', methods=['POST', 'GET'])
def submit_post():
    if 'user_data' in session:
        if request.form['post_text'].replace(" ", "").replace("<p>", "").replace("</p>", "").replace("&nbsp;", "") != "":
            username = str(session['user_data']['login'])
            post_text = request.form['post_text']
            now = datetime.now()
            date_time = now.strftime("%d/%m/%Y %H:%M:%S")
            # Datetime is a string in the format MM/DD/YEAR hh/mm/ss; 
            # 'post_level' refers to the hierarchy of posts/replies '0' refers to a parent post, 1 would be a reply to the parent, 2 would be a reply to that reply, etc. etc.
            # Use 'post_level' and the unique _id of each document to figure out how much to 'indent' the posts, also use the date and time to order them correctly
            document = {'username': username, 'post_text': post_text, 'date_time': date_time, 'post_level': 0, 'child_posts': []}  
            try:
                collection.insert_one(document)
            except Exception as e:
                print("Can't post, try again. error: ", e)
        else:
            pass
    else:
        flash('You must be logged in to post.')
    return redirect(url_for('renderPage1'))

@app.route('/search', methods=['POST', 'GET'])
def filter_posts():
    query = request.form['search_query']
    filtered_posts = ""
    filtered_posts = searched_posts(query)
    return render_template('page1.html', posts = filtered_posts)
    
def searched_posts(query=".*?"):
    username = ""
    post = ""
    id = ""
    posts = ""
    reply_form = ""
    count = 0   
    for document in collection.find({"$or": [{"post_text" : {"$regex" : query, '$options' : 'i'}}, {'username': {"$regex" : query, '$options' : 'i'}}]}):
        count = count + 1
        username = document['username']
        post = document['post_text']
        id = document['_id']
        date = document['date_time']
        post_level = document['post_level']
        reply_form = "<button id='rButton" + str(count) + "'>Reply</button> <form action='/reply' method='post' id='reply" + str(count) + "' class='replyForm'> <label for='reply_text'>Type your reply!</label> <br> <textarea name='reply_text' id='reply_editor" + str(count) + "' > " + "@" + username + " </textarea> <script> ClassicEditor.create( document.querySelector( '#reply_editor" + str(count) + "' ) ).catch( error => { console.error( error )} ); </script> <input type='hidden' value='" + str(id) + "' name='parent_id'> <input type='hidden' value='" + str(post_level) + "' name='post_level'> <input type='submit' value ='Submit'> </form>"
        posts = posts + Markup("<div class='card m-3 level" + str(post_level) + "' style='max-width: 100%;'>  <div class='card-body'>  <h4 class='card-title'> <strong>" + username + "</strong> </h4>  <h6 class='card-subtitle mb-2 text-muted'> " + date + " </h6>  <p class='card-text'> " + post + " </p>  " + reply_form + " </div>  </div>")
    return posts
    

@app.route('/clearSearch')
def clear_filter():
    return redirect(url_for('renderPage1'))
    
@app.route('/reply', methods=['POST', 'GET'])
def add_reply():
    if 'user_data' in session and 'reply_text' not in session:
        if request.form['reply_text'].replace(" ", "").replace("<p>", "").replace("</p>", "").replace("&nbsp;", "") != "":
            username = str(session['user_data']['login'])
            # parent_level should be the post you're replying to's post_level, parent_id should be the _id of the parent post/reply
            parent_level = request.form['post_level']
            parent_id = ObjectId(request.form['parent_id'])
            reply_text = request.form['reply_text']
            now = datetime.now()
            date_time = now.strftime("%d/%m/%Y %H:%M:%S")
            document = {'username': username, 'post_text': reply_text, 'date_time': date_time, 'post_level': int(parent_level) + 1, 'child_posts': []}
            try:
                collection.insert_one(document)
                reply_id = str(document['_id'])
                collection.update_one({ '_id': parent_id }, { '$push': {'child_posts': reply_id} })
            except Exception as e:
                print("Can't post, try again. error: ", e)
        else:
            pass
    else:
        flash('You must be logged in to post.')
    return redirect(url_for('renderPage1'))
    
@app.route('/delete', methods=['POST', 'GET'])
def delete_post():
    if 'user_data' in session:
        if request.form['username'] == session['user_data']['login']:
            target_id = ObjectId(request.form['post_id'])
            collection.update_one( { '_id': target_id }, { '$set': {'post_text': '<p><i> [Post has been deleted by user.] </i><p>'} })
        else:
            flash('You did not post this...')
    else:
        pass
    return redirect(url_for('renderPage1'))

@app.route('/page1')
def renderPage1():
    return render_template('page1.html', posts = format_all_posts())
    
@app.route('/googleb4c3aeedcc2dd103.html')
def render_google_verification():
    return render_template('googleb4c3aeedcc2dd103.html')

@github.tokengetter
def get_github_oauth_token():
    return session['github_token']

    

count = 0
posts = ""

def format_all_posts(query=".*?"):
    username = ""
    post = ""
    id = ""
    global count
    count = 0
    global posts
    posts = ""
    reply_form = ""
    for document in collection.find({"$or": [{"post_text" : {"$regex" : query, '$options' : 'i'}}, {'username': {"$regex" : query, '$options' : 'i'}}]}):
        if document['post_level'] == 0:
            count  = count + 1
            username = document['username']
            post = document['post_text']
            id = document['_id']
            date = document['date_time']
            post_level = document['post_level']
            delete = "<form action='/delete' method='post' id='delete" + str(count) + "'>  <input type='submit' value='Delete'>  <input type='hidden' value='" + str(id) + "' name='post_id'>  <input type='hidden' value='" + username + "' name='username'>  </form>"
            reply_form = "<button id='rButton" + str(count) + "'>Reply</button> <form action='/reply' method='post' id='reply" + str(count) + "' class='replyForm'> <label for='reply_text'>Type your reply!</label> <br> <textarea name='reply_text' id='reply_editor" + str(count) + "' > " + "@" + username + " </textarea> <script> ClassicEditor.create( document.querySelector( '#reply_editor" + str(count) + "' ) ).catch( error => { console.error( error )} ); </script> <input type='hidden' value='" + str(id) + "' name='parent_id'> <input type='hidden' value='" + str(post_level) + "' name='post_level'> <input type='submit' value ='Submit'> </form>"
            posts = posts + Markup("<div class='card m-3 level" + str(post_level) + "' style='max-width: 100%;'>  <div class='card-body'>  <h4 class='card-title'> <strong>" + username + "</strong> </h4>  <h6 class='card-subtitle mb-2 text-muted'> " + date + " </h6>  <p class='card-text'> " + post + " </p>  " + reply_form + delete + " </div>  </div>")
            get_children(document)
        else:
            pass
    return posts

def get_children(doc):
    if doc['child_posts']:
        for c in doc['child_posts']:
            global count
            count = count + 1
            child_id = ObjectId(c)
            child_doc = collection.find_one( {'_id': child_id} )
            child_username = child_doc['username']
            child_post = child_doc['post_text']
            child_date = child_doc['date_time']
            child_level = child_doc['post_level']
            delete = "<form action='/delete' method='post' id='delete" + str(count) + "'>  <input type='submit' value='Delete'>  <input type='hidden' value='" + str(child_id) + "' name='post_id'>  <input type='hidden' value='" + child_username + "' name='username'>  </form>"
            reply_form = "<button id='rButton" + str(count) + "'>Reply</button> <form action='/reply' method='post' id='reply" + str(count) + "' class='replyForm'> <label for='reply_text'>Type your reply!</label> <br> <textarea name='reply_text' id='reply_editor" + str(count) + "' > " + "@" + child_username + " </textarea> <script> ClassicEditor.create( document.querySelector( '#reply_editor" + str(count) + "' ) ).catch( error => { console.error( error )} ); </script> <input type='hidden' value='" + str(child_id) + "' name='parent_id'> <input type='hidden' value='" + str(child_level) + "' name='post_level'> <input type='submit' value ='Submit'> </form>"
            global posts
            posts = posts + Markup("<div class='card m-3 level" + str(child_level) + "' style='max-width: 100%;'>  <div class='card-body'>  <h4 class='card-title'> <strong>" + child_username + "</strong> </h4>  <h6 class='card-subtitle mb-2 text-muted'> " + child_date + " </h6>  <p class='card-text'> " + child_post + " </p>  " + reply_form + delete + " </div>  </div>")
            get_children(child_doc)
    else:
        pass
    return posts


if __name__ == '__main__':
    app.run()
