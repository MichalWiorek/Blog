import os
from flask import Flask, render_template
import requests


app = Flask(__name__)
API_URL = os.getenv('API_URL')
posts_data = []
try:
    posts_data = requests.get(url=API_URL).json()
except requests.exceptions.RequestException:
    print("error")


@app.route("/")
def home_page():
    return render_template("index.html", posts=posts_data)


@app.route("/about")
def about_page():
    return render_template("about.html")


@app.route("/contact")
def contact_page():
    return render_template("contact.html")


@app.route("/post/<int:post_id>")
def post_page(post_id):
    for post in posts_data:
        if post["id"] == post_id:
            return render_template('post.html', post=post)
    return render_template('post.html', post={"title": "Post not found!"})


if __name__ == "__main__":
    app.run(debug=True)
