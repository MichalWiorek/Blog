import os
import smtplib

from flask import Flask, render_template, request, redirect, url_for
from flask_ckeditor import CKEditor
from flask_sqlalchemy import SQLAlchemy


PASSWORD = os.getenv("PASSWORD")
EMAIL = os.getenv("EMAIL")

app = Flask(__name__)
app.config['SECRET_KEY'] = os.getenv("SECRET_KEY")

# CONNECTION TO DB
app.config['SQLALCHEMY_DATABASE_URI'] = os.getenv('DATABASE_URI', 'sqlite:///posts.db')
db = SQLAlchemy()
db.init_app(app)

# INIT CKEDITOR
app.config['CKEDITOR_PKG_TYPE'] = 'full'
ckeditor = CKEditor(app)


# CONFIGURE TABLE
class BlogPost(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(250), unique=True, nullable=False)
    subtitle = db.Column(db.String(250), nullable=False)
    date = db.Column(db.String(250), nullable=False)
    body = db.Column(db.Text, nullable=False)
    author = db.Column(db.String(250), nullable=False)
    img_url = db.Column(db.String(250), nullable=False)


with app.app_context():
    db.create_all()


@app.route("/")
def home_page():
    posts_data = db.session.execute(db.select(BlogPost)).scalars().all()
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
    post = db.get_or_404(BlogPost, post_id)
    return render_template('post.html', post=post)


if __name__ == "__main__":
    app.run(debug=True)
