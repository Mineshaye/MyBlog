from datetime import date
from flask import Flask, abort, render_template, redirect, url_for, flash
from flask_bootstrap import Bootstrap5
from flask_ckeditor import CKEditor
from flask_gravatar import Gravatar
from flask_login import UserMixin, login_user, LoginManager, current_user, logout_user, login_manager
from flask_sqlalchemy import SQLAlchemy
from functools import wraps
from werkzeug.security import generate_password_hash, check_password_hash
from sqlalchemy.orm import relationship
# Import your forms from the forms.py
from forms import CreatePostForm,RegisterForm,LoginForm,CommentForm
import os
'''
Make sure the required packages are installed: 
Open the Terminal in PyCharm (bottom left). 

On Windows type:
python -m pip install -r requirements.txt

On MacOS type:
pip3 install -r requirements.txt

This will install the packages from the requirements.txt for this project.
'''

app = Flask(__name__)
app.config['SECRET_KEY'] = os.environ.get('FLASK_KEY')
ckeditor = CKEditor(app)
Bootstrap5(app)

# TODO: Configure Flask-Login
login_manager=LoginManager()
login_manager.init_app(app)

@login_manager.user_loader
def load_user(user_id):
    with app.app_context():
        return db.session.get(entity = User, ident = user_id)

# CONNECT TO DB
app.config['SQLALCHEMY_DATABASE_URI'] =os.environ.get('DB_URI')
db = SQLAlchemy()
db.init_app(app)


gravatar = Gravatar(app,
                    size=100,
                    rating='g',
                    default='retro',
                    force_default=False,
                    force_lower=False,
                    use_ssl=False,
                    base_url=None)

# admin onlydecorator comec here
def admin_only(function):
    def wrapper_function():
        if current_user.id==1:
            function()
            return wrapper_function
        else:
            return abort()

def admin_only(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if current_user.id!=1:
            return abort(403)
        return f(*args, **kwargs)
    return decorated_function

# CONFIGURE TABLES

# TODO: Create a User table for all your registered users. 


class  User(UserMixin,db.Model):
    __tablename__ = "users"
    id=db.Column(db.Integer,primary_key=True)
    email=db.Column(db.String(250),unique=True,nullable=False)
    password=db.Column(db.String(250),nullable=False)
    name=db.Column(db.String(250),nullable=False)
    posts = relationship("BlogPost", back_populates="author")
    comments=relationship("Comment",back_populates="comment_author")


class BlogPost(db.Model):
    __tablename__ = "blog_posts"
    id = db.Column(db.Integer, primary_key=True)
    #Create Foreign Key, "users.id" the users refers to the tablename of User.
    author_id = db.Column(db.Integer, db.ForeignKey("users.id"))
    #Create reference to the User object, the "posts" refers to the posts protperty in the User class.
    author = relationship("User", back_populates="posts")
    title = db.Column(db.String(250), unique=True, nullable=False)
    subtitle = db.Column(db.String(250), nullable=False)
    date = db.Column(db.String(250), nullable=False)
    body = db.Column(db.Text, nullable=False)
    img_url = db.Column(db.String(250), nullable=False)
    comments=relationship("Comment",back_populates="parent_post")

class Comment(db.Model):
    __tablename__ = "comments"
    id=db.Column(db.Integer, primary_key=True)
    author_id = db.Column(db.Integer, db.ForeignKey("users.id"))
    comment_author = relationship("User", back_populates="comments")
    post_id = db.Column(db.Integer, db.ForeignKey("blog_posts.id"))
    parent_post=relationship("BlogPost",back_populates="comments")
    text=db.Column(db.Text, nullable=False)

with app.app_context():
    db.create_all()


# TODO: Use Werkzeug to hash the user's password when creating a new user.
@app.route('/register',methods=["POST","GET"])
def register():
    form=RegisterForm()
    if form.validate_on_submit():
        user=db.session.execute(db.Select(User).where(User.email==form.email.data)).scalar()
        if user:
            flash("This email already exits ,log in  instead")
            return redirect(url_for('login'))
        password= form.password.data
        new_user=User(
            email=form.email.data,
            password=generate_password_hash(password,method='pbkdf2:sha256',salt_length=8),
            name= form.name.data
        )
        db.session.add(new_user)
        db.session.commit()
        login_user(new_user)
        return redirect(url_for('get_all_posts'))
    return render_template("register.html",form=form,is_logged_in=current_user.is_authenticated)


# TODO: Retrieve a user from the database based on their email. 
@app.route('/login',methods=["GET","POST"])
def login():
    form=LoginForm()
    if form.validate_on_submit():
        email=form.email.data
        password=form.password.data
        current_user=db.session.execute(db.Select(User).where(User.email==email)).scalar()
        # email is unique in a db so we can only have 1 result
        if not current_user:
            flash("This email does not exit here .try again")
            return redirect(url_for("login"))
        elif not  check_password_hash(current_user.password,password):
            flash("Password incorrect, pls try again")
            return redirect(url_for("login"))
        else:
            login_user(current_user)
            return redirect(url_for("get_all_posts"))
    return render_template("login.html",form=form)


@app.route('/logout')
def logout():
    logout_user()
    return redirect(url_for('get_all_posts'))


@app.route('/')
def get_all_posts():
    result = db.session.execute(db.select(BlogPost))
    posts = result.scalars().all()
    users=db.session.execute(db.select(User)).scalars().all()
    return render_template("index.html", all_posts=posts,current_user=current_user)


# TODO: Allow logged-in users to comment on posts
@app.route("/post/<int:post_id>",methods=["GET","POST"])
def show_post(post_id):
    requested_post = db.get_or_404(BlogPost, post_id)
    form=CommentForm()
    comments=db.session.execute(db.select(Comment)).scalars().all()
    if form.validate_on_submit():
        if current_user.is_authenticated:
            new_comment=Comment(
                text=form.content.data,
                comment_author=current_user,
                parent_post=requested_post
                )
            db.session.add(new_comment)
            db.session.commit()
            return redirect(url_for('get_all_posts'))
        else:
            flash("You need to be logged in first")
            return redirect(url_for('login'))
    return render_template("post.html", post=requested_post,current_user=current_user,form=form)


# TODO: Use a decorator so only an admin user can create a new post

@app.route("/new-post", methods=["GET", "POST"])
@admin_only
def add_new_post():
    form = CreatePostForm()
    if form.validate_on_submit():
        new_post = BlogPost(
            title=form.title.data,
            subtitle=form.subtitle.data,
            body=form.body.data,
            img_url=form.img_url.data,
            author=current_user,
            date=date.today().strftime("%B %d, %Y")
        )
        db.session.add(new_post)
        db.session.commit()
        return redirect(url_for("get_all_posts"))
    return render_template("make-post.html", form=form,current_user=current_user)


# TODO: Use a decorator so only an admin user can edit a post

@app.route("/edit-post/<int:post_id>", methods=["GET", "POST"])
@admin_only
def edit_post(post_id):
    post = db.get_or_404(BlogPost, post_id)
    edit_form = CreatePostForm(
        title=post.title,
        subtitle=post.subtitle,
        img_url=post.img_url,
        author=post.author,
        body=post.body
    )
    if edit_form.validate_on_submit():
        post.title = edit_form.title.data
        post.subtitle = edit_form.subtitle.data
        post.img_url = edit_form.img_url.data
        post.author = current_user
        post.body = edit_form.body.data
        db.session.commit()
        return redirect(url_for("show_post", post_id=post.id))
    return render_template("make-post.html", form=edit_form, is_edit=True,current_user=current_user)


# TODO: Use a decorator so only an admin user can delete a post

@app.route("/delete/<int:post_id>")
@admin_only
def delete_post(post_id):
    post_to_delete = db.get_or_404(BlogPost, post_id)
    db.session.delete(post_to_delete)
    db.session.commit()
    return redirect(url_for('get_all_posts'))


@app.route("/about")
def about():
    return render_template("about.html",current_user=current_user)


@app.route("/contact")
def contact():
    return render_template("contact.html",current_user=current_user)


if __name__ == "__main__":
    app.run(debug=True, port=5002)
