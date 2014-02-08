from flask import Flask, render_template, request, redirect, url_for
from flask.ext.sqlalchemy import SQLAlchemy
import sys
import datetime

app = Flask(__name__)
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///test.db'
db = SQLAlchemy(app)


class Post(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    added = db.Column(db.DateTime)

    title = db.Column(db.String(120))
    more = db.Column(db.Text)

    upvotes = db.Column(db.Integer, default=0)
    downvotes = db.Column(db.Integer, default=0)

    poster_ip = db.Column(db.String(16))
    poster_ua = db.Column(db.Text)


@app.route('/')
def landing_page():
    return render_template("index.html", posts=Post.query.all())

@app.route("/new", methods=["POST"])
def new_post():
    title = request.form.get("title")
    text = request.form.get("more")

    post = Post(added=datetime.datetime.now(), title=title, more=text,
                poster_ip=request.remote_addr, poster_ua=request.headers.get('User-Agent'))
    db.session.add(post)
    db.session.commit()

    return redirect(url_for("landing_page"))


@app.route("/<int:id>")
def view_post(id):
    pass


if __name__ == '__main__':
    try:
        db.create_all()
        print "Created database"
    except Exception:
        pass

    app.run(debug="--debug" in sys.argv)
