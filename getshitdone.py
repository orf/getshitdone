from flask import Flask, render_template, request, redirect, url_for, session
from flask.ext.sqlalchemy import SQLAlchemy
from sqlalchemy.ext.hybrid import hybrid_property, hybrid_method
from sqlalchemy.orm.exc import NoResultFound
from sqlalchemy.sql import exists
import sys
import logging
import datetime
import uuid

app = Flask(__name__)
app.secret_key = "test"
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///test.db'
db = SQLAlchemy(app)

file_handler = logging.FileHandler("logs/flask.log")
file_handler.setLevel(logging.WARNING)
app.logger.addHandler(file_handler)


class Post(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    added = db.Column(db.DateTime)

    title = db.Column(db.String(120))
    more = db.Column(db.Text)

    upvotes = db.Column(db.Integer, default=0)
    downvotes = db.Column(db.Integer, default=0)

    poster_ip = db.Column(db.String(16))
    poster_ua = db.Column(db.Text)

    votes = db.relationship("Vote", backref="post", lazy="dynamic")

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


@app.route('/')
def landing_page():
    get_vote = db.session.query(Vote.post_id, Vote.type.label('vote_type')).filter_by(uid=session["uid"]).subquery()
    post_query = Post.query.order_by(Post.score.desc())\
        .outerjoin(get_vote, Post.id == get_vote.c.post_id).add_column("vote_type").all()

    return render_template("index.html", posts=post_query, DOWNVOTE=DOWNVOTE, UPVOTE=UPVOTE)


@app.route("/new", methods=["POST"])
def new_post():
    title = request.form.get("title")
    text = request.form.get("more")

    if title:
        post = Post(added=datetime.datetime.now(), title=title, more=text,
                    poster_ip=request.remote_addr, poster_ua=request.headers.get('User-Agent'))
        db.session.add(post)
        db.session.commit()

    return redirect(url_for("landing_page"))


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
        vote = Vote(uid=uid, post_id=post.id, type=vote_type,
                    vote_ip=request.remote_addr, vote_ua=request.headers.get('User-Agent'))
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
def add_mobile():
    return render_template("submit_mobile.html")


if __name__ == '__main__':
    try:
        db.create_all()
        print "Created database"
    except Exception:
        pass

    app.run(debug="--debug" in sys.argv)
