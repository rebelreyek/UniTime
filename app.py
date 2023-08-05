from flask import Flask, redirect, url_for, request, render_template, session

app = Flask(__name__)

# root path
@app.route('/', methods=['GET'])
def index():
    return render_template('index.html')

@app.route('/form', methods=['GET'])
def form():
    return render_template('form.html')