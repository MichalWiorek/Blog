import os
import smtplib
from datetime import date, datetime

import bleach
from flask import Flask, render_template, request, redirect, url_for, flash, abort
from flask_bootstrap import Bootstrap5
from flask_ckeditor import CKEditor
from flask_login import LoginManager, login_user, logout_user, UserMixin, current_user
from flask_sqlalchemy import SQLAlchemy
from werkzeug.security import generate_password_hash, check_password_hash
from functools import wraps
from flask_gravatar import Gravatar

from forms import PostForm, RegisterForm, LoginForm, CommentForm

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

year = str(datetime.now().year)


# CONFIGURE TABLE
class BlogPost(db.Model):
    __tablename__ = "blog_posts"
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(250), unique=True, nullable=False)
    subtitle = db.Column(db.String(250), nullable=False)
    date = db.Column(db.String(250), nullable=False)
    body = db.Column(db.Text, nullable=False)
    author = db.relationship("User", back_populates="posts")
    author_id = db.Column(db.Integer, db.ForeignKey("users.id"))
    img_url = db.Column(db.String(250), nullable=False)
    comments = db.relationship("Comment", back_populates="post")


class User(db.Model, UserMixin):
    __tablename__ = "users"
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(250), nullable=False)
    email = db.Column(db.String(250), unique=True, nullable=False)
    password = db.Column(db.String(25), nullable=False)
    posts = db.relationship("BlogPost", back_populates="author")
    comments = db.relationship("Comment", back_populates="author")


class Comment(db.Model):
    __tablename__ = "comments"
    id = db.Column(db.Integer, primary_key=True)
    body = db.Column(db.Text, nullable=False)
    author_id = db.Column(db.Integer, db.ForeignKey("users.id"))
    author = db.relationship("User", back_populates="comments")
    post_id = db.Column(db.Integer, db.ForeignKey("blog_posts.id"))
    post = db.relationship("BlogPost", back_populates="comments")


with app.app_context():
    db.create_all()


gravatar = Gravatar(app,
                    size=100,
                    rating='g',
                    default='robohash',
                    force_default=False,
                    force_lower=False,
                    use_ssl=False,
                    base_url=None)


@login_manager.user_loader
def load_user(user_id):
    return db.get_or_404(User, user_id)


# admin_only decorator
def admin_only(func):
    @wraps(func)
    def wrap(*args, **kwargs):
        if current_user.is_authenticated and current_user.id == 1:
            return func(*args, **kwargs)
        else:
            abort(403)
    return wrap


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
        return redirect(url_for('get_all_posts', year=year))
    return render_template('register.html', form=form, year=year)


@app.route("/login", methods=["GET", "POST"])
def login():
    form = LoginForm()
    if form.validate_on_submit():
        user = db.session.execute(db.select(User).where(User.email == form.email.data)).scalar()
        if not user:
            flash("There is no user registered with that email.")
            return render_template('login.html', form=form, year=year)
        if check_password_hash(user.password, form.password.data):
            login_user(user)
            return redirect(url_for('get_all_posts', year=year))
        flash("Password is wrong, try again.")
        return render_template('login.html', form=form, year=year)
    return render_template('login.html', form=form, year=year)


@app.route("/logout")
def logout():
    logout_user()
    return redirect(url_for('get_all_posts', year=year))


@app.route("/")
def get_all_posts():
    posts_data = db.session.execute(db.select(BlogPost)).scalars().all()
    return render_template("index.html", posts=posts_data, year=year)


@app.route("/post/<int:post_id>", methods=["GET", "POST"])
def get_post(post_id):
    post = db.get_or_404(BlogPost, post_id)
    form = CommentForm()
    comments = db.session.execute(db.select(Comment).where(Comment.post_id==post_id))
    if form.validate_on_submit():
        if not current_user.is_authenticated:
            flash("Log in to comment.")
            return redirect(url_for('login', year=year))
        new_comment = Comment(
            body=strip_invalid_html(form.body.data),
            author=current_user,
            post=post
        )
        db.session.add(new_comment)
        db.session.commit()
        return render_template('post.html', post=post, form=form, year=year)
    return render_template('post.html', post=post, form=form, year=year)


@app.route("/new-post", methods=["GET", "POST"])
@admin_only
def add_post():
    form = PostForm()
    if form.validate_on_submit():
        data = form.data
        data.pop("submit_button", None)
        data.pop("csrf_token", None)
        data["date"] = date.today().strftime("%B %d, %Y")
        data["body"] = strip_invalid_html(data["body"])
        data["author"] = current_user
        new_post = BlogPost(**data)
        db.session.add(new_post)
        db.session.commit()
        return redirect(url_for('get_all_posts', year=year))
    return render_template('make-post.html', form=form, year=year)


@app.route("/edit-post/<int:post_id>", methods=["GET", "POST"])
@admin_only
def edit_post(post_id):
    post = db.get_or_404(BlogPost, post_id)
    form = PostForm(obj=post)
    if form.validate_on_submit():
        form.populate_obj(post)
        db.session.commit()
        return redirect(url_for('get_post', post_id=post_id, year=year))
    return render_template('make-post.html', form=form, is_edit=True, year=year)


@app.route("/delete/<int:post_id>")
@admin_only
def delete_post(post_id):
    post = db.get_or_404(BlogPost, post_id)
    db.session.delete(post)
    db.session.commit()
    return redirect(url_for('get_all_posts', year=year))


@app.route("/about")
def about():
    return render_template("about.html", year=year)


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
        return render_template("contact.html", request="POST", year=year)
    return render_template("contact.html", request="GET", year=year)


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
