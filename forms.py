from flask_wtf import FlaskForm
from wtforms import StringField, SubmitField, PasswordField
from wtforms.validators import DataRequired, Email, URL
from flask_ckeditor import CKEditorField


class PostForm(FlaskForm):
    title = StringField('Post Title', validators=[DataRequired()])
    subtitle = StringField('Subtitle', validators=[DataRequired()])
    body = CKEditorField('Post', validators=[DataRequired()])
    img_url = StringField('Post image URL', validators=[DataRequired(), URL()])
    submit_button = SubmitField('Submit Post')


class RegisterForm(FlaskForm):
    name = StringField("Username", validators=[DataRequired()])
    email = StringField("Email", validators=[DataRequired(), Email()])
    password = PasswordField("Password", validators=[DataRequired()])
    submit_button = SubmitField("Register")


class LoginForm(FlaskForm):
    email = StringField("Email", validators=[DataRequired(), Email()])
    password = PasswordField("Password", validators=[DataRequired()])
    submit_button = SubmitField("Log in")


class CommentForm(FlaskForm):
    body = CKEditorField("Comment", validators=[DataRequired()])
    submit_button = SubmitField("Send")
