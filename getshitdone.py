from flask import Flask, render_template, request, redirect, url_for, session, Response
from flask.ext.sqlalchemy import SQLAlchemy
from flask_wtf.csrf import CsrfProtect
from sqlalchemy.ext.hybrid import hybrid_property
from sqlalchemy.orm.exc import NoResultFound
from flask_wtf import Form
from wtforms import TextField, TextAreaField
from wtforms.validators import Length, DataRequired
import sys
import logging
import datetime
import uuid

app = Flask(__name__)
app.secret_key = "Z<\xe7`W\x03\xda\xd5p\x8ab\xfe\x05O\x00\xcc\xa2\xf9\x04e\xfeSg{"
app.config['SQLALCHEMY_DATABASE_URI'] = 'postgresql+psycopg2://getshitdone:password@localhost:5432/getshitdone'
db = SQLAlchemy(app)
CsrfProtect(app)

ADMIN_PASSWORD = "Qw9EN3nd"

file_handler = logging.FileHandler("logs/flask.log")
file_handler.setLevel(logging.WARNING)
app.logger.addHandler(file_handler)


class PostForm(Form):
    title = TextField('title', validators=[DataRequired(), Length(min=10, max=120)])
    more_info = TextAreaField('more_info')


class Post(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    added = db.Column(db.DateTime)

    title = db.Column(db.String(120))
    more = db.Column(db.Text)

    upvotes = db.Column(db.Integer, default=0)
    downvotes = db.Column(db.Integer, default=0)

    poster_ip = db.Column(db.String(16))
    poster_ua = db.Column(db.Text)

    votes = db.relationship("Vote", backref="post", cascade="all,delete", lazy="dynamic")

    @hybrid_property
    def score(self):
        return self.upvotes - self.downvotes

    def __repr__(self):
        return "<Post %s. Up: %s, Down: %s>" % (self.id, self.upvotes, self.downvotes)


UPVOTE = 1
DOWNVOTE = -1


class Vote(db.Model):
    uid = db.Column(db.String(32), primary_key=True)
    post_id = db.Column(db.Integer, db.ForeignKey("post.id"), primary_key=True)
    type = db.Column(db.Integer)  # -1: Down, 1: Up

    vote_ip = db.Column(db.String(16))
    vote_ua = db.Column(db.Text)


@app.before_request
def before_req():
    if "uid" not in session:
        session["uid"] = uuid.uuid4().hex
    if "a" not in session:
        session["a"] = False


@app.route("/admin")
def login_as_admin():
    auth = request.authorization
    if auth and auth.password == ADMIN_PASSWORD:
        session["a"] = True
    else:
        return Response(
    'Could not verify your access level for that URL.\n'
    'You have to login with proper credentials', 401,
    {'WWW-Authenticate': 'Basic realm="Login Required"'})

    return redirect(url_for("landing_page"))


@app.route("/delete/<int:id>", methods=["POST"])
def delete_post(id):
    post = Post.query.get_or_404(id)
    db.session.delete(post)
    db.session.commit()

    return redirect(url_for("landing_page"))


@app.route('/')
def landing_page(form=None):
    get_vote = db.session.query(Vote.post_id, Vote.type.label('vote_type')).filter_by(uid=session["uid"]).subquery()
    post_query = Post.query.order_by(Post.score.desc())\
        .outerjoin(get_vote, Post.id == get_vote.c.post_id).add_column("vote_type").all()

    return render_template("index.html", posts=post_query, DOWNVOTE=DOWNVOTE, UPVOTE=UPVOTE, form=form or PostForm())


@app.route("/new", methods=("POST", "GET"))
def new_post():
    form = PostForm()
    if form.validate_on_submit():
        post = Post(added=datetime.datetime.now(), title=form.title.data, more=form.more_info.data,
                    poster_ip=request.remote_addr, poster_ua=request.headers.get('User-Agent'))
        db.session.add(post)
        db.session.commit()
    else:
        if request.args.get("mobile", False):
            print form.title.errors
            return add_mobile(form)
        else:
            return landing_page(form)

    return redirect(url_for('landing_page'))


def vote_post(post, vote_type, uid):
    try:
        vote = Vote.query.filter_by(uid=uid, post_id=post.id).one()
        if vote.type == vote_type:
            # Do nothing, already voted
            return

        if vote_type == DOWNVOTE:
            post.upvotes -= 1
        else:
            post.downvotes -= 1

        vote.type = vote_type
        db.session.add(vote)
    except NoResultFound:
        # Make a new vote
        ips = request.access_route
        vote = Vote(uid=uid, post_id=post.id, type=vote_type,
                    vote_ip=ips[0], vote_ua=request.headers.get('User-Agent'))
        db.session.add(vote)

    if vote_type == DOWNVOTE:
        post.downvotes += 1
    else:
        post.upvotes += 1

    db.session.add(post)
    db.session.commit()


@app.route("/<int:id>/upvote", methods=["POST"])
def upvote(id):
    post = Post.query.get_or_404(id)
    vote_post(post, UPVOTE, session["uid"])

    return redirect("/")


@app.route("/<int:id>/downvote", methods=["POST"])
def downvote(id):
    post = Post.query.get_or_404(id)
    vote_post(post, DOWNVOTE, session["uid"])

    return redirect("/")


@app.route("/<int:id>")
def view_post(id):
    get_vote = db.session.query(Vote.post_id, Vote.type.label('vote_type')).filter_by(uid=session["uid"]).subquery()
    post = Post.query.filter_by(id=id).order_by(Post.score.desc())\
        .outerjoin(get_vote, Post.id == get_vote.c.post_id).add_column("vote_type").first_or_404()

    return render_template("view_single.html", post=post[0], vote=post[1], DOWNVOTE=DOWNVOTE, UPVOTE=UPVOTE)


@app.route("/about_me")
def about_me():
    return render_template("about_me.html")

@app.route("/policies")
def policies():
    return render_template("policies.html")

@app.route("/add")
def add_mobile(form=None):
    return render_template("submit_mobile.html", form=form or PostForm())


if __name__ == '__main__':
    try:
        db.create_all()
        print "Created database"
    except Exception:
        pass

    app.run(debug="--debug" in sys.argv)
