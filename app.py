from flask import Flask, render_template, jsonify
import requests
from flask import Flask, render_template, redirect, url_for, request, flash
from flask_wtf import FlaskForm
from wtforms import StringField, PasswordField, SubmitField
from wtforms.validators import DataRequired, Email, EqualTo
from flask_sqlalchemy import SQLAlchemy
from flask_bcrypt import Bcrypt
from sqlalchemy.exc import IntegrityError
from datetime import datetime
import PIL.Image
from IPython.display import display, Markdown
import google.generativeai as genai
import base64
from bs4 import BeautifulSoup
from flask_socketio import SocketIO, join_room, leave_room, emit
import os   

app = Flask(__name__, static_url_path='/static')

UPLOAD_FOLDER = 'static/uploads'
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
app.config['SECRET_KEY'] = 'your_secret_key'
socketio = SocketIO(app, async_mode='eventlet')

@app.route('/chat')
def chat():
    return render_template('chat.html')

@socketio.on('join')
def join(data):
    room = data['room']
    join_room(room)
    emit('message', {'msg': 'User has entered the room.'}, room=room)

@socketio.on('leave')
def leave(data):
    room = data['room']
    leave_room(room)
    emit('message', {'msg': 'User has left the room.'}, room=room)

@socketio.on('message')
def handle_message(data):
    message = data['message']
    room = data['room']
    emit('message', {'msg': message}, room=room)


app.config['SECRET_KEY'] = 'your_secret_key_here'


app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///site.db'
db = SQLAlchemy(app)
bcrypt = Bcrypt(app)

genai.configure(api_key="Your-Api-Key")

model = genai.GenerativeModel('gemini-pro-vision')

class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(20), unique=True, nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    password = db.Column(db.String(60), nullable=False)

class RegistrationForm(FlaskForm):
    username = StringField('Username', validators=[DataRequired()])
    email = StringField('Email', validators=[DataRequired(), Email()])
    password = PasswordField('Password', validators=[DataRequired()])
    confirm_password = PasswordField('Confirm Password', validators=[DataRequired(), EqualTo('password')])
    submit = SubmitField('Sign Up')

class LoginForm(FlaskForm):
    email = StringField('Email', validators=[DataRequired(), Email()])
    password = PasswordField('Password', validators=[DataRequired()])
    submit = SubmitField('Login')



@app.route('/')
def index():
    return render_template('index.html')



def preprocess_events(events_data):
    processed_events = []
    for event_data in events_data:
        description = event_data["description"]
        # Remove HTML tags from description
        description = BeautifulSoup(description, "html.parser").get_text()
        processed_event = {
            "title": event_data["title"],
            "description": description,
            "start_date": event_data["start_date"].split('T')[0],
            "end_date": event_data["end_date"].split('T')[0],
            "location": event_data["location"],
            "url": event_data.get("url", "No URL provided")
        }
        processed_events.append(processed_event)
    return processed_events

def get_all_events():
    base_url = "https://api.artic.edu/api/v1/events"
    response = requests.get(base_url)
    if response.status_code == 200:
        events_data = response.json()["data"]
        return preprocess_events(events_data)
    else:
        return None

@app.route('/events')
def events():
    events = get_all_events()
    return render_template('events.html', events=events)

@app.route('/fund')
def fund():
    return render_template('crowd.html')

@app.route('/gallery')
def gallery():
    return render_template('gallery.html')

@app.route('/crowd_fund')
def crowd_fund():
    return render_template('crowd_fund.html')


@app.route('/hackathons')
def hackathon():
    return render_template('hackathons.html')

@app.route('/market')
def market():
    return render_template('market.html')

@app.route("/register", methods=['GET', 'POST'])
def register():
    form = RegistrationForm()
    if form.validate_on_submit():
        hashed_password = bcrypt.generate_password_hash(form.password.data).decode('utf-8')
        user = User(username=form.username.data, email=form.email.data, password=hashed_password)
        try:
            db.session.add(user)
            db.session.commit()
            flash('Your account has been created! You are now able to log in', 'success')
            return redirect(url_for('login'))
        except IntegrityError:
            db.session.rollback()
            flash('An account with this email address already exists. Please use a different email address.', 'danger')
    return render_template('register.html', title='Register', form=form)

@app.route("/login", methods=['GET', 'POST'])
def login():
    form = LoginForm()
    if form.validate_on_submit():
        user = User.query.filter_by(email=form.email.data).first()
        if user and bcrypt.check_password_hash(user.password, form.password.data):
            flash('You have been logged in!', 'success')
            return redirect(url_for('index'))
        else:
            flash('Login Unsuccessful. Please check email and password', 'danger')
    return render_template('login.html', title='Login', form=form)

@app.route('/explain-art')
def explain():
    return render_template('explain-art.html')

@app.route('/upload', methods=['POST'])
def upload():
    if 'image' not in request.files:
        return "No image uploaded"
    
    image = request.files['image']
    file=request.files['image']
    if file:
            filename = file.filename
            file.save(os.path.join(app.config['UPLOAD_FOLDER'], filename))
    
    if image.filename == '':
        return "No selected file"
    
    img = PIL.Image.open(image)
    img_base64 = base64.b64encode(image.read()).decode('utf-8')
    response = model.generate_content(["Based on the above art give me the artist name and art details about how it is painted and give me all details about the art also at the end give me a art authenticity score ", img], stream=True)
    response.resolve()
    
    return render_template('art-result.html', explanation=response.text,image_path=f'static/uploads/{filename}')


@app.route('/meta-login')
def metalogin():
    return render_template('meta-login.html')

@app.route('/pay')
def pay():
    # In a real application, you would retrieve the recipient address from a database or another secure source
    recipient_address = '0x3F3329F5B4280130a09b0d8FBE330d445AbF1F67'
    return render_template('pay.html', recipient_address=recipient_address)


@app.route('/blog1')
def blog1():
    return render_template('blog1.html')

@app.route('/blog2')
def blog2():
    return render_template('blog2.html')

@app.route('/blog3')
def blog3():
    return render_template('blog3.html')


@app.route('/create-art')
def explain2():
    return render_template('art-create.html')

@app.route('/upload2', methods=['GET','POST'])
def upload2():
    if 'image2' not in request.files:
        return "No image uploaded"
    
    image = request.files['image2']
    file=request.files['image2']
    if file:
            filename = file.filename
            file.save(os.path.join(app.config['UPLOAD_FOLDER'], filename))
            
    if image.filename == '':
        return "No selected file"
    
    img = PIL.Image.open(image)
    img_base64 = base64.b64encode(image.read()).decode('utf-8')
    response = model.generate_content(["Based on the above art Give me step by step instructions on how to create this art and i dont want the history of this art just  what are the stationary required and what method this art is created etc dont tell the history instead tell how it is created step by step", img], stream=True)
    response.resolve()
    
    return render_template('art-create-result.html', explanation=response.text,image_path=f'static/uploads/{filename}')


url = 'https://oevortex-webscout.hf.space/api/news'
params = {
    'q': 'Art and museums',  # Query parameter
    'max_results': 10,   # Maximum number of results
    'safesearch': 'moderate',  # Safe search option
    'region': 'wt-wt'   # Region parameter
}

headers = {
    'accept': 'application/json'
}

response = requests.get(url, params=params, headers=headers)

if response.status_code == 200:
    news_data = response.json()['results']  # Access 'results' key
      # or do something with the data
else:
    print("Error:", response.status_code)

# Sample news data (replace this with actual data from the API)

@app.route('/news')
def news():
    # Format date in day-month-year format
    for item in news_data:
        # Parse the ISO 8601 formatted date and convert it to day-month-year
        item['date'] = datetime.fromisoformat(item['date'].replace('Z', '+00:00')).strftime('%d-%m-%Y')

    return render_template('news.html', news=news_data)



@app.route('/map')
def map():
    return render_template('map.html')

@app.route('/museums')
def get_museums():
    url = "https://api.foursquare.com/v3/places/nearby?query=Museum&limit=15"

    headers = {
        "accept": "application/json",
        "Authorization": "fsq3ASvU/8kLfic0LIHWmP0w6oK/M7ov9Bn/+Be3oMRZ1HM="
    }

    response = requests.get(url, headers=headers)
    data = response.json().get('results', [])

    museums = []
    for item in data:
        museum = {
            'name': item['name'],
            'lat': item['geocodes']['main']['latitude'],
            'lon': item['geocodes']['main']['longitude'],
            'address': item.get('location', {}).get('formatted_address', 'Address not available')
        }
        museums.append(museum)

    return jsonify(museums)


if __name__ == '__main__':
    with app.app_context():
        db.create_all()  # Create all database tables
    socketio.run(app, debug=True)


