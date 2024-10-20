from datetime import date
from flask import Flask, abort, render_template, redirect, url_for, flash
# from flask_bootstrap5 import Bootstrap
from flask_bootstrap import Bootstrap5
from flask_ckeditor import CKEditor
#from flask_gravatar import Gravatar
from flask_login import UserMixin, login_user, LoginManager, current_user, logout_user
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy.orm import relationship, DeclarativeBase, Mapped, mapped_column
from sqlalchemy import Integer, String, Text
from functools import wraps
# from werkzeug.security import generate_password_hash, check_password_hash
from flask_bcrypt import Bcrypt
from sqlalchemy.orm import relationship
# Import your forms from the forms.py
from forms import CreatePostForm, RegisterForm, LoginForm, CommentForm

app = Flask(__name__)
app.config['SECRET_KEY'] = '8BYkEfBA6O6donzWlSihBXox7C0sKR6b'
ckeditor = CKEditor(app)




# CREATE DATABASE
class Base(DeclarativeBase):
    pass
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///posts.db'
db = SQLAlchemy(model_class=Base)
db.init_app(app)
bootstrap = Bootstrap5(app)
bcrypt = Bcrypt(app)

login_manager = LoginManager()
login_manager.init_app(app)

@login_manager.user_loader
def load_user(user_id):
    return db.get_or_404(User, user_id)

# CONFIGURE TABLES
class BlogPost(db.Model):
    __tablename__ = "blog_posts"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    # Create Foreign Key, "users.id" the users refers to the tablename of User.
    author_id: Mapped[int] = mapped_column(Integer, db.ForeignKey("users.id"))
    # Create reference to the User object. The "posts" refers to the posts property in the User class.
    author = relationship("User", back_populates="posts")
    title: Mapped[str] = mapped_column(String(250), unique=True, nullable=False)
    subtitle: Mapped[str] = mapped_column(String(250), nullable=False)
    date: Mapped[str] = mapped_column(String(250), nullable=False)
    body: Mapped[str] = mapped_column(Text, nullable=False)
    img_url: Mapped[str] = mapped_column(String(250), nullable=False)
    # Parent relationship to the comments
    comments = relationship("Comment", back_populates="parent_post")


# Create a User table for all your registered users
class User(UserMixin, db.Model):
    __tablename__ = "users"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    email: Mapped[str] = mapped_column(String(100), unique=True)
    password: Mapped[str] = mapped_column(String(100))
    name: Mapped[str] = mapped_column(String(100))
    # This will act like a list of BlogPost objects attached to each User.
    # The "author" refers to the author property in the BlogPost class.
    posts = relationship("BlogPost", back_populates="author")
    # Parent relationship: "comment_author" refers to the comment_author property in the Comment class.
    comments = relationship("Comment", back_populates="comment_author")


# Create a table for the comments on the blog posts
class Comment(db.Model):
    __tablename__ = "comments"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    text: Mapped[str] = mapped_column(Text, nullable=False)
    # Child relationship:"users.id" The users refers to the tablename of the User class.
    # "comments" refers to the comments property in the User class.
    author_id: Mapped[int] = mapped_column(Integer, db.ForeignKey("users.id"))
    comment_author = relationship("User", back_populates="comments")
    # Child Relationship to the BlogPosts
    post_id: Mapped[str] = mapped_column(Integer, db.ForeignKey("blog_posts.id"))
    parent_post = relationship("BlogPost", back_populates="comments")

with app.app_context():
    db.create_all()

@app.route('/register', methods=['GET','POST'])
def register_user():
    register_form = RegisterForm()
    if register_form.validate_on_submit():
        result = db.session.execute(db.select(User).where(User.email == register_form.email.data))
        print(result)
        user = result.scalar()
        print(user)
        if user:
            print('User found!!!!')
            flash("You already registered with this email! Please login")
            return  redirect(url_for('login'))

        hashed_password = bcrypt.generate_password_hash(register_form.password.data)
        new_user = User(
            email = register_form.email.data,
            password = hashed_password,
            name = register_form.name.data
        )
        db.session.add(new_user)
        db.session.commit()
        login_user(new_user)
        return redirect(url_for('home'))
    return render_template('register.html', form=register_form,current_user=current_user)

@app.route('/login', methods=['GET', 'POST'])
def login():
    login_form = LoginForm()
    if login_form.validate_on_submit():
        user_exists = db.session.execute(db.select(User).where(User.email == login_form.email.data)).scalar()
        if not user_exists:
            flash("Invalid user try again!!")
            return redirect(url_for('login'))
        elif not bcrypt.check_password_hash(user_exists.password, login_form.password.data):
            flash("Invalid password! Try again!")
            return redirect(url_for('login'))
        else:
            login_user(user_exists)
            return redirect(url_for('home'))

    return render_template('login.html', form=login_form, current_user=current_user)

@app.route('/')
def home():
    all_posts = db.session.execute(db.select(BlogPost))
    posts = all_posts.scalars().all()
    return render_template("index.html", all_posts=posts)

@app.route('/make_post', methods=["GET", "POST"])
def new_post():
    form = CreatePostForm()

    if form.validate_on_submit():
        user = User(email='raj798@gmail', password='raj798@gmail', name='rajSam')
        db.session.add(user)
        db.session.commit()
        new_post = BlogPost(
            title=form.title.data,
            subtitle=form.subtitle.data,
            body=form.body.data,
            img_url=form.img_url.data,
            author=user,
            date=date.today().strftime("%B %d, %Y")
        )
        db.session.add(new_post)
        db.session.commit()
        return redirect(url_for("home"))
    return render_template("make-post.html", form=form)

@app.route('/view_post/<int:post_id>', methods=["GET", "POST"])
def show_post(post_id):
    requested_post = db.get_or_404(BlogPost, post_id)
    comment_form = CommentForm()
    if comment_form.validate_on_submit():
        comment = Comment(
            text = comment_form.comment_text.data,
            parent_post = requested_post,
            comment_author = requested_post.author
        )
        db.session.add(comment)
        db.session.commit()
    return render_template("post.html", post=requested_post,  form=comment_form)

@app.route('/edit_post/<int:post_id>', methods=["GET", "POST"])
def edit_post(post_id):
    requested_post = db.get_or_404(BlogPost, post_id)
    edit_form = CreatePostForm(
                title = requested_post.title,
                 subtitle = requested_post.subtitle,
                 body = requested_post.body,
                img_url = requested_post.img_url
        )
    if edit_form.validate_on_submit():
        requested_post.title = edit_form.title.data
        requested_post.subtitle = edit_form.subtitle.data
        requested_post.img_url = edit_form.img_url.data
        requested_post.body = edit_form.body.data
        db.session.commit()
        return redirect(url_for('home'))

    return render_template("make-post.html", post=requested_post,  form=edit_form, is_edit=True)


@app.route("/delete_post/<int:post_id>")
def delete(post_id):
    post_to_delete = db.get_or_404(BlogPost,post_id)
    db.session.delete(post_to_delete)
    db.session.commit()
    render_template('index.html')

@app.route('/logout')
def logout():
    logout_user()
    return redirect(url_for('home'))

@app.route("/about")
def about():
    return render_template("about.html")

@app.route('/contact')
def contact():
    return render_template('contact.html')


if __name__ == "__main__":
    app.run(debug=True)