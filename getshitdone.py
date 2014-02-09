from flask import Flask, render_template, request, redirect, url_for, session
from flask.ext.sqlalchemy import SQLAlchemy
from flask.ext.kvsession import KVSessionExtension
from sqlalchemy.ext.hybrid import hybrid_property
from simplekv.memory import DictStore
import sys
import logging
import datetime

app = Flask(__name__)
app.secret_key = "test"
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///test.db'
db = SQLAlchemy(app)
file_handler = logging.FileHandler("logs/flask.log")
file_handler.setLevel(logging.WARNING)
app.logger.addHandler(file_handler)


KVSessionExtension(DictStore(), app)


class Post(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    added = db.Column(db.DateTime)

    title = db.Column(db.String(120))
    more = db.Column(db.Text)

    upvotes = db.Column(db.Integer, default=0)
    downvotes = db.Column(db.Integer, default=0)

    poster_ip = db.Column(db.String(16))
    poster_ua = db.Column(db.Text)

    @hybrid_property
    def score(self):
        return self.upvotes - self.downvotes


@app.before_request
def before_req():
    if "downvotes" not in session:
        session["downvotes"] = []
    if "upvotes" not in session:
        session["upvotes"] = []


@app.route('/')
def landing_page():
    return render_template("index.html", posts=Post.query.order_by(Post.score.desc()).all())


@app.route("/new", methods=["POST"])
def new_post():
    title = request.form.get("title")
    text = request.form.get("more")

    post = Post(added=datetime.datetime.now(), title=title, more=text,
                poster_ip=request.remote_addr, poster_ua=request.headers.get('User-Agent'))
    db.session.add(post)
    db.session.commit()

    return redirect(url_for("landing_page"))


@app.route("/<int:id>/upvote", methods=["POST"])
def upvote(id):
    post = Post.query.get_or_404(id)

    if id in session["downvotes"]:
        post.downvotes -= 1
        session["downvotes"].remove(id)

    if id in session["upvotes"]:
        pass

    post.upvotes += 1
    db.session.add(post)
    db.session.commit()

    session["upvotes"].append(id)

    return redirect("/")


@app.route("/<int:id>/downvote", methods=["POST"])
def downvote(id):
    post = Post.query.get_or_404(id)

    if id in session["upvotes"]:
        post.upvotes -= 1
        session["upvotes"].remove(id)

    post.downvotes += 1
    db.session.add(post)
    db.session.commit()

    session["downvotes"].append(id)

    return redirect("/")


@app.route("/<int:id>")
def view_post(id):
    post = Post.query.get_or_404(id)
    return render_template("view_single.html", post=post)


if __name__ == '__main__':
    try:
        db.create_all()
        print "Created database"
    except Exception:
        pass

    app.run(debug="--debug" in sys.argv)
