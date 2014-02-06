from flask import Flask, render_template
from flask.ext.sqlalchemy import SQLAlchemy
import sys

app = Flask(__name__)
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///test.db'
db = SQLAlchemy(app)


class Post(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    added = db.Column(db.DateTime)

    title = db.Column(db.String(120))
    more = db.Column(db.Text)

    upvotes = db.Column(db.Integer)
    downvotes = db.Column(db.Integer)

    poster_ip = db.Column(db.String(16))
    poster_ua = db.Column(db.Text)


@app.route('/')
def hello_world():
    return render_template("index.html")


if __name__ == '__main__':
    try:
        db.create_all()
        print "Created database"
    except Exception:
        pass

    app.run(debug="--debug" in sys.argv)
