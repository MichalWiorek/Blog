import os
from flask import Flask, render_template, request
import requests
import smtplib

PASSWORD = os.getenv("PASSWORD")
EMAIL = os.getenv("EMAIL")

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


@app.route("/contact", methods=["GET", "POST"])
def contact_page():
    if request.method == "POST":
        data = request.form
        msg = ""
        for key, value in data.items():
            msg += f"{key.title()}: {value}\n"
        with smtplib.SMTP("smtp.gmail.com", port=587) as connection:
            connection.starttls()
            connection.login(EMAIL, PASSWORD)
            connection.sendmail(
                from_addr=EMAIL,
                to_addrs=EMAIL,
                msg=f"Subject:New message!\n\n{msg}".encode('utf-8')
            )
        return render_template("contact.html", request="POST")
    return render_template("contact.html", request="GET")


@app.route("/post/<int:post_id>")
def post_page(post_id):
    for post in posts_data:
        if post["id"] == post_id:
            return render_template('post.html', post=post)
    return render_template('post.html', post={"title": "Post not found!"})


if __name__ == "__main__":
    app.run(debug=True)
