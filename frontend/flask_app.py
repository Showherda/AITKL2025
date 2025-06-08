from flask import Flask, render_template, jsonify
import json
import os

app = Flask(__name__)

def load_companies():
    with open(os.path.join('data', 'showcase_data.json'), 'r') as f:
        return json.load(f)

@app.route('/')
def home():
    companies = load_companies()
    return render_template('home.html', companies=companies)

@app.route('/showcase/<int:company_id>')
def showcase(company_id):
    companies = load_companies()
    if 0 <= company_id < len(companies):
        return render_template('showcase.html', data=companies[company_id])
    return "Company not found", 404
# Run the app
if __name__ == '__main__':
    app.run(debug=True)
