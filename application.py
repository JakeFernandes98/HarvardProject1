import os
import requests
from flask import Flask, session, render_template, request,jsonify
from flask_session import Session
from sqlalchemy import create_engine
from sqlalchemy.orm import scoped_session, sessionmaker

app = Flask(__name__)
userid = 0;
logout = 0;

# Check for environment variable
if not os.getenv("DATABASE_URL"):
    raise RuntimeError("DATABASE_URL is not set")

# Configure session to use filesystem
app.config["SESSION_PERMANENT"] = False
app.config["SESSION_TYPE"] = "filesystem"
Session(app)

# Set up database
engine = create_engine(os.getenv("DATABASE_URL"))
db = scoped_session(sessionmaker(bind=engine))


@app.route("/", methods=["GET","POST"])
def index():
    print(session.get("userid"))
    if request.method == "POST":
        session.clear()
    if session.get("userid") is None:
        return render_template("index.html")
    else:
        return render_template("home.html")

@app.route("/home",methods=["GET","POST"])
def home():
    if request.method == "GET":
        return "Please log in or register for an account."
    name = request.form.get("name")
    pwd = request.form.get("password")
    user = db.execute("SELECT * FROM users where username = :name",{"name":name}).fetchone();
    if user is None:
        db.execute("INSERT INTO users (username, password) VALUES (:name,:pwd)",{"name":name,"pwd":pwd})
        db.commit()
        userid = db.execute("SELECT userid FROM users WHERE username = :name",{"name":name}).fetchone();
        session["userid"] = userid[0]
        return render_template("home.html")
    else:
        if user.password != pwd:
            errorcode = 1
            return render_template("index.html", error = errorcode)
        else:
            print(user.userid)
            session["userid"] = user.userid
            return render_template("home.html")


@app.route("/search",methods=["POST"])
def search():
    query = request.form.get("searchquery")
    books = db.execute("SELECT * FROM books where isbn LIKE :isbn",{"isbn":"%"+query+"%"}).fetchall()
    books += db.execute("SELECT * FROM books where title LIKE :title",{"title":"%"+query+"%"}).fetchall()
    books += db.execute("SELECT * FROM books where author LIKE :author",{"author":"%"+query+"%"}).fetchall()
    return render_template("search.html", books=books)

@app.route("/<string:info_isbn>",methods=["GET","POST"])
def bookinfo(info_isbn):
    if request.method == "POST":
        rating = request.form.get("rating")
        review = request.form.get("review")
        if review is None:
            review = sqlalchemy.null()
        db.execute("INSERT into reviews (isbn, userid, rating, review) VALUES (:isbn, :userid, :rating, :review)",
        {"isbn":info_isbn,"userid":session.get("userid")[0],"rating":rating,"review":review})
        db.commit()

    book = db.execute("SELECT * FROM books where isbn=:isbn",{"isbn":info_isbn}).fetchone()
    if book is None:
        return render_template("bookinfo.html", book=None, reviews=None, userrev=None)

    userrev = db.execute("SELECT * FROM reviews WHERE userid=:userid AND isbn=:isbn",{"userid":session.get("userid"),"isbn":info_isbn}).fetchone()
    print(userrev)

    devkey = "4A1oHc5UmFwmeEsfctDQpw"
    res = requests.get("https://www.goodreads.com/book/review_counts.json",
                        params={"isbns":[info_isbn],"format": "json","key": devkey})
    if res.status_code != 200:
        return render_template("bookinfo.html", book=book, reviews = None, userrev=userrev)

    reviews = res.json()
    reviews = reviews["books"]
    reviews = reviews[0]
    return render_template("bookinfo.html", book=book, review_count = reviews["ratings_count"],review_rating=reviews["average_rating"], userrev= userrev);

@app.route("/api/<string:isbn>",methods=["GET"])
def isbn_api(isbn):
    book = db.execute("SELECT * FROM books where isbn=:isbn",{"isbn":isbn}).fetchone()
    if book is None:
        return jsonify({"Error":"Book not found"}), 404
    devkey = "4A1oHc5UmFwmeEsfctDQpw"
    res = requests.get("https://www.goodreads.com/book/review_counts.json",
                        params={"isbns":[isbn],"format": "json","key": devkey})
    if res.status_code != 200:
        ratings_count = "0"
        average_rating = "0"
    else:
        reviews = res.json()
        reviews = reviews["books"]
        reviews = reviews[0]
        ratings_count = reviews["ratings_count"]
        average_rating = reviews["average_rating"]
    return jsonify(
    {
        "title": book.title,
        "author": book.author,
        "year": book.year,
        "isbn": isbn,
        "review_count": ratings_count,
        "average_score": average_rating
    }
    )
