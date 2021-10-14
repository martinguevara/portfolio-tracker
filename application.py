import os

from cs50 import SQL
from flask import Flask, flash, redirect, render_template, request, session
from flask_session import Session
from tempfile import mkdtemp
from werkzeug.exceptions import default_exceptions, HTTPException, InternalServerError
from werkzeug.security import check_password_hash, generate_password_hash


from helpers import apology, login_required, lookup, usd

# Configure application
app = Flask(__name__)

# Ensure templates are auto-reloaded
app.config["TEMPLATES_AUTO_RELOAD"] = True


# Ensure responses aren't cached
@app.after_request
def after_request(response):
    response.headers["Cache-Control"] = "no-cache, no-store, must-revalidate"
    response.headers["Expires"] = 0
    response.headers["Pragma"] = "no-cache"
    return response


# Custom filter
app.jinja_env.filters["usd"] = usd

# Configure session to use filesystem (instead of signed cookies)
app.config["SESSION_FILE_DIR"] = mkdtemp()
app.config["SESSION_PERMANENT"] = False
app.config["SESSION_TYPE"] = "filesystem"
Session(app)

# Configure CS50 Library to use SQLite database
db = SQL("sqlite:///finance.db")

# Make sure API key is set
if not os.environ.get("API_KEY"):
    raise RuntimeError("API_KEY not set")


@app.route("/")
@login_required
def index():
    """Show portfolio of stocks"""
    rows = db.execute("""SELECT symbol, SUM(shares) as totalShares FROM transactions WHERE user_id=:user_id GROUP BY symbol HAVING totalShares > 0;""", user_id=session["user_id"])
    holdings = []
    totalval = 0
    for row in rows:
        stock = lookup(row["symbol"])
        holdings.append({
            "symbol": stock["symbol"],
            "name": stock["name"],
            "shares": row["totalShares"],
            "price": usd(stock["price"]),
            "total": usd(stock["price"] * row["totalShares"])
        })
        totalval += stock["price"] * row["totalShares"]
    rows = db.execute("SELECT cash from users where id=?", session["user_id"])
    cash = rows[0]["cash"]
    totalval += cash

    return render_template("index.html", holdings=holdings, cash=usd(cash), totalval = usd(totalval))


@app.route("/buy", methods=["GET", "POST"])
@login_required
def buy():
    """Buy shares of stock"""
    if request.method == "POST":

        #Check if symbol and shares are filled out
        if not request.form.get("symbol"):
            return apology("Please enter a stock symbol",400)

        if not request.form.get("shares"):
            return apology("Please enter the number of shares",400)

        #Check if input is an integer
        try:
            int(request.form.get("shares"))
            numshares = int(request.form.get("shares"))

        except ValueError:
            return apology("Please enter a valid number of shares",400)

        #Check if number of shares is positive
        if numshares < 0:
            return apology("Please enter a positive number of shares",400)

        #Check if symbol exists
        quoted=lookup(request.form.get("symbol"))
        if quoted:
            #look up current stock price and calculate total
            pricenow = quoted.get('price')
            total = numshares*pricenow

            #query cash amount the user has
            cash = db.execute("SELECT cash FROM users WHERE id=?", session["user_id"])
            cashnow = cash[0]["cash"]

            #difference between cash balance and purchase amout
            newbal=cashnow-total

            #if user can't afford it
            if newbal < 0:
                return apology("You have insufficient funds",400)

            #record purchase on database--who, what, number of shares, price, total, when

            #time
            #Subtract from user account
            db.execute("UPDATE users SET cash = ? where id= ?", newbal, session["user_id"])

            #Log as a purchase in new table
            db.execute("INSERT INTO transactions (user_id, symbol, price, shares, type) VALUES (?,?,?,?,?)", session["user_id"], request.form.get("symbol"), pricenow, numshares,"buy")
            flash("Purchase successful!")

            return redirect("/")

        else:
            return apology("Please enter a valid stock symbol",400)

    else:
        return render_template("buy.html")

@app.route("/history")
@login_required
def history():
    """Show history of transactions"""
    if request.method == "GET":
        #Query transactions ordered by time
        rows=db.execute("SELECT symbol, shares, price, time, type FROM transactions where user_id=? ORDER BY time DESC", session["user_id"])

        #Append list
        holdings=[]
        for row in rows:
            stock=lookup(row["symbol"])
            holdings.append ({
                "time": row["time"],
                "symbol": stock["symbol"],
                "name": stock["name"],
                "shares": row["shares"],
                "price": stock["price"],
                "type": row["type"]
            })

        return render_template("history.html", holdings=holdings, usd=usd)
    else:
        return render_template("history.html")


@app.route("/login", methods=["GET", "POST"])
def login():
    """Log user in"""

    # Forget any user_id
    session.clear()

    # User reached route via POST (as by submitting a form via POST)
    if request.method == "POST":

        # Ensure username was submitted
        if not request.form.get("username"):
            return apology("must provide username", 403)

        # Ensure password was submitted
        elif not request.form.get("password"):
            return apology("must provide password", 403)

        # Query database for username
        rows = db.execute("SELECT * FROM users WHERE username = ?", request.form.get("username"))

        # Ensure username exists and password is correct
        if len(rows) != 1 or not check_password_hash(rows[0]["hash"], request.form.get("password")):
            return apology("invalid username and/or password", 403)

        # Remember which user has logged in
        session["user_id"] = rows[0]["id"]
        session["username"] = rows[0]["username"]

        # Redirect user to home page
        return redirect("/")

    # User reached route via GET (as by clicking a link or via redirect)
    else:
        return render_template("login.html")


@app.route("/logout")
def logout():
    """Log user out"""

    # Forget any user_id
    session.clear()

    # Redirect user to login form
    return redirect("/")


@app.route("/quote", methods=["GET", "POST"])
@login_required
def quote():
    """Get stock quote."""
    if request.method == "POST":

        #Check if symbol is valid
        quoted=lookup(request.form.get("symbol"))
        if quoted:
            return render_template("quoted.html", quoted=quoted)
        else:
            return apology("Please enter a valid stock symbol",400)

    else:
        return render_template("quote.html")


@app.route("/register", methods=["GET", "POST"])
def register():

    if request.method == "POST":

        #Check for username
        if not request.form.get("username"):
            return apology("Please enter a username",400)

        #Check for password
        if not request.form.get("password"):
            return apology("Please enter a password",400)

        #Check for matching passwords
        if request.form.get("password") != request.form.get("confirmation"):
            return apology("The passwords do not match",400)

        #Check for unused username
        check = db.execute("SELECT * FROM users WHERE username = ?", request.form.get("username"))
        if len(check) == 1:
            return apology("Username already exists",400)

        else:
            #Hash password & insert new user into database
            hash = generate_password_hash(request.form.get("password"))
            db.execute("INSERT INTO users (username, hash) VALUES (?,?)", request.form.get("username"), hash)

            return redirect("/login")

    else:
        return render_template("registration.html")


@app.route("/myaccount", methods=["GET", "POST"])
@login_required
def myaccount():
    """Add additional cash to account"""
    if request.method == "POST":
        #Validate amounts
        addamt=int(request.form.get("amount"))

        if not request.form.get("amount"):
            return apology("Please enter an amount",400)
        if addamt < 0:
            return apology("Please enter a positive amount",400)

        addamt=int(request.form.get("amount"))
        cash=db.execute("SELECT cash FROM users WHERE id=?", session["user_id"])[0]["cash"]
        newbal=cash+addamt

        db.execute("UPDATE users SET cash = ? WHERE id=?", newbal, session["user_id"])
        flash("Amount added!")
        return redirect("/")

    else:
        return render_template("myaccount.html")

@app.route("/sell", methods=["GET", "POST"])
@login_required
def sell():
    """Sell shares of stock"""
    if request.method == "POST":
        #Fill out number of shares
        if not request.form.get("shares"):
            return apology("Please enter the number of shares",400)

        #Check if user owns enough shares
        rows=db.execute("SELECT shares FROM transactions WHERE symbol =? AND user_id =?", request.form.get("symbol"), session["user_id"])
        shares=rows[0]["shares"]

        numshares=int(request.form.get("shares"))
        if numshares>shares:
            return apology("You do not own enough shares",400)
        else:
            #Update cash
            stock=lookup(request.form.get("symbol"))
            cashquery=db.execute("SELECT cash FROM users WHERE id=?",session["user_id"])
            cash=cashquery[0]["cash"]
            saleprice=(stock["price"]*numshares)
            newcash=cash+saleprice

            db.execute("UPDATE users SET cash=? WHERE id=?", newcash,session["user_id"])

            #Log sale into transactions table
            db.execute("INSERT INTO transactions (user_id, symbol, price, shares, type) VALUES (?,?,?,?,?)", session["user_id"], request.form.get("symbol"), saleprice, -numshares, "sell")
            flash("Sale successful!")

            return redirect("/")


    else:
        symbols=db.execute("SELECT symbol FROM transactions WHERE user_id=? GROUP BY symbol",session["user_id"])
        return render_template("sell.html", symbols=symbols)



def errorhandler(e):
    """Handle error"""
    if not isinstance(e, HTTPException):
        e = InternalServerError()
    return apology(e.name, e.code)


# Listen for errors
for code in default_exceptions:
    app.errorhandler(code)(errorhandler)
