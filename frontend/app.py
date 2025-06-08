from flask import Flask, render_template, jsonify
import json
import os

app = Flask(__name__)

# Load the showcase data from JSON file
def load_showcase_data():
    with open(os.path.join('data', 'showcase_data.json')) as f:
        return json.load(f)

# Root route goes directly to the showcase page
@app.route('/')
def showcase():
    data = load_showcase_data()
    return render_template('showcase.html', data=data)

# Placeholder jobs route (can be implemented later)
@app.route('/jobs')
def jobs():
    return "<h1>Jobs Page Coming Soon</h1>"

# Run the app
if __name__ == '__main__':
    app.run(debug=True)
