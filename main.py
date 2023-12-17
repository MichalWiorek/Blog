import os
import smtplib
from datetime import date

import bleach
from flask import Flask, render_template, request, redirect, url_for, flash
from flask_bootstrap import Bootstrap5
from flask_ckeditor import CKEditor
from flask_login import LoginManager, login_user, logout_user, UserMixin
from flask_sqlalchemy import SQLAlchemy
from werkzeug.security import generate_password_hash, check_password_hash

from forms import PostForm, RegisterForm, LoginForm

PASSWORD = os.getenv("PASSWORD")
EMAIL = os.getenv("EMAIL")

app = Flask(__name__)
app.config['SECRET_KEY'] = os.getenv("SECRET_KEY")
Bootstrap5(app)

# Login Manager
login_manager = LoginManager()
login_manager.init_app(app)

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


class User(db.Model, UserMixin):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(250), nullable=False)
    email = db.Column(db.String(250), unique=True, nullable=False)
    password = db.Column(db.String(25), nullable=False)


with app.app_context():
    db.create_all()


@login_manager.user_loader
def load_user(user_id):
    return db.get_or_404(User, user_id)


@app.route("/register", methods=["GET", "POST"])
def register_user():
    form = RegisterForm()
    if form.validate_on_submit():
        data = form.data
        user = db.session.execute(db.select(User).where(User.email == data["email"])).scalar()
        if user:
            flash("User with that email already exists. Log in instead.")
            return redirect(url_for('login'))
        data.pop("submit_button", None)
        data.pop("csrf_token", None)
        data["password"] = generate_password_hash(data["password"])
        new_user = User(**data)
        db.session.add(new_user)
        db.session.commit()
        login_user(new_user)
        return redirect(url_for('get_all_posts'))
    return render_template('register.html', form=form)


@app.route("/login", methods=["GET", "POST"])
def login():
    form = LoginForm()
    if form.validate_on_submit():
        user = db.session.execute(db.select(User).where(User.email == form.email.data)).scalar()
        if not user:
            flash("There is no user registered with that email.")
            return render_template('login.html', form=form)
        if check_password_hash(user.password, form.password.data):
            login_user(user)
            return redirect(url_for('get_all_posts'))
        flash("Password is wrong, try again.")
        return render_template('login.html', form=form)
    return render_template('login.html', form=form)


@app.route("/logout")
def logout():
    logout_user()
    return redirect(url_for('get_all_posts'))


@app.route("/")
def get_all_posts():
    posts_data = db.session.execute(db.select(BlogPost)).scalars().all()
    return render_template("index.html", posts=posts_data)


@app.route("/post/<int:post_id>")
def get_post(post_id):
    post = db.get_or_404(BlogPost, post_id)
    return render_template('post.html', post=post)


@app.route("/new-post", methods=["GET", "POST"])
def add_post():
    h1_text = "Create Post"
    form = PostForm()
    if form.validate_on_submit():
        data = form.data
        data.pop("submit_button", None)
        data.pop("csrf_token", None)
        data["date"] = date.today().strftime("%B %d, %Y")
        data["body"] = strip_invalid_html(data["body"])
        new_post = BlogPost(**data)
        db.session.add(new_post)
        db.session.commit()
        return redirect(url_for('get_all_posts'))
    return render_template('make-post.html', form=form, h1_text=h1_text)


@app.route("/edit-post/<int:post_id>", methods=["GET", "POST"])
def edit_post(post_id):
    h1_text = "Edit Post"
    post = db.get_or_404(BlogPost, post_id)
    form = PostForm(obj=post)
    if form.validate_on_submit():
        form.populate_obj(post)
        db.session.commit()
        return redirect(url_for('get_post', post_id=post_id))
    return render_template('make-post.html', form=form, h1_text=h1_text)


@app.route("/delete/<int:post_id>")
def delete_post(post_id):
    post = db.get_or_404(BlogPost, post_id)
    db.session.delete(post)
    db.session.commit()
    return redirect(url_for('get_all_posts'))


@app.route("/about")
def about():
    return render_template("about.html")


@app.route("/contact", methods=["GET", "POST"])
def contact():
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


# strips invalid tags/attributes
def strip_invalid_html(content):
    allowed_tags = ['a', 'abbr', 'acronym', 'address', 'b', 'br', 'div', 'dl', 'dt',
                    'em', 'h1', 'h2', 'h3', 'h4', 'h5', 'h6', 'hr', 'i', 'img',
                    'li', 'ol', 'p', 'pre', 'q', 's', 'small', 'strike',
                    'span', 'sub', 'sup', 'table', 'tbody', 'td', 'tfoot', 'th',
                    'thead', 'tr', 'tt', 'u', 'ul']
    allowed_attrs = {
        'a': ['href', 'target', 'title'],
        'img': ['src', 'alt', 'width', 'height'],
    }
    cleaned = bleach.clean(content,
                           tags=allowed_tags,
                           attributes=allowed_attrs,
                           strip=True)
    return cleaned


if __name__ == "__main__":
    app.run(debug=True)
