import sys
sys.path.append('..')
sys.path.append('../..')

from flask import Flask, render_template, jsonify
import json
import os
from flask import Flask, render_template, request, redirect, url_for, jsonify
from werkzeug.utils import secure_filename

UPLOAD_FOLDER = 'static/uploads'
DATA_FILE = os.path.join('data', 'showcase_data.json')
PITCH_FOLDER = os.path.join(UPLOAD_FOLDER, 'pitchdecks')
FOUNDER_FOLDER = os.path.join(UPLOAD_FOLDER, 'founders')
LOGO_FOLDER = os.path.join(UPLOAD_FOLDER, 'logos')

import sys

sys.path.append('./data/')

app = Flask(__name__)
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER

os.makedirs(PITCH_FOLDER, exist_ok=True)
os.makedirs(FOUNDER_FOLDER, exist_ok=True)
os.makedirs(LOGO_FOLDER, exist_ok=True)

@app.route('/apply', methods=['GET', 'POST'])
def apply():
    if request.method == 'POST':
        # Handle file uploads
        logo = request.files['logo']
        founder_img = request.files['founder_img']
        pitch_deck = request.files.get('pitch_deck')

        logo_filename = secure_filename(logo.filename)
        founder_img_filename = secure_filename(founder_img.filename)

        logo.save(os.path.join(LOGO_FOLDER, logo_filename))
        founder_img.save(os.path.join(FOUNDER_FOLDER, founder_img_filename))

        pitch_deck_filename = None
        if pitch_deck and request.form['got_grant'] == 'yes':
            pitch_deck_filename = secure_filename(pitch_deck.filename)
            pitch_deck.save(os.path.join(PITCH_FOLDER, pitch_deck_filename))

        # Prepare new company data
        new_company = {
            "logo_url": f"/{LOGO_FOLDER}/{logo_filename}",
            "name": request.form['name'],
            "short_summary": request.form['short_summary'],
            "about": request.form['about'],
            "status": request.form['status'],
            "website": request.form['website'],
            "founded": request.form['founded'],
            "state": request.form['state'],
            "founder_size": request.form['founder_size'],
            "team_size": request.form['team_size'],
            "grant": [],
            "news": [],
            "program": [],
            "founders": [{
                "name": request.form['founder_name'],
                "img": f"/{FOUNDER_FOLDER}/{founder_img_filename}",
                "linkedin": request.form['founder_linkedin'],
                "email": request.form['founder_email'],
                "phone": request.form['founder_phone']
            }]
        }

        if pitch_deck_filename:
            new_company['grant'].append({
                "title": "Pitch Deck",
                "url": f"/{PITCH_FOLDER}/{pitch_deck_filename}",
                "date": "Submitted"
            })

        # Load and append
        with open(DATA_FILE, 'r') as f:
            companies = json.load(f)

        companies.append(new_company)

        with open(DATA_FILE, 'w') as f:
            json.dump(companies, f, indent=2)

        return redirect(url_for('home'))

    return render_template('apply.html')

def load_companies():
    with open(os.path.join('data', 'showcase_data.json'), 'r') as f:
        return json.load(f)

def load_companies1():
    return get_startups()

@app.route('/')
def home():
    companies = load_companies()
    return render_template('home.html', companies=companies)

@app.route('/companies1')
def api_companies1():
    companies = load_companies1()
    return render_template('home.html', companies=companies)

@app.route('/showcase/<int:company_id>')
def showcase(company_id):
    companies = load_companies()
    if 0 <= company_id < len(companies):
        return render_template('showcase.html', data=companies[company_id])
    return "Company not found", 404

@app.route('/showcase1/<int:company_id>')
def showcase1(company_id):
    companies = load_companies1()
    if 0 <= company_id < len(companies):
        return render_template('showcase1.html', data=companies[company_id])
    return "Company not found", 404
# Run the app
if __name__ == '__main__':
    app.run(debug=True)
