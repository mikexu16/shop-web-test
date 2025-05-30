import contextlib
import os
import json
import time
from datetime import datetime
from forms import CreateForm, LoginForm, AddItemForm, CartForm
from flask import (
    Flask,
    session,
    render_template,
    url_for,
    redirect,
    jsonify,
    request,
    send_from_directory,
)
from sqlalchemy import MetaData, UniqueConstraint
from flask_sqlalchemy import SQLAlchemy
from flask_migrate import Migrate
from sqlalchemy import text
from werkzeug.utils import secure_filename

convention = {
    "ix": "ix_%(column_0_label)s",
    "uq": "uq_%(table_name)s_%(column_0_name)s",
    "ck": "ck_%(table_name)s_%(constraint_name)s",
    "fk": "fk_%(table_name)s_%(column_0_name)s_%(referred_table_name)s",
    "pk": "pk_%(table_name)s",
}

metadata = MetaData(naming_convention=convention)
app = Flask(__name__)
app.config["SECRET_KEY"] = "password"
app.config["SQLALCHEMY_DATABASE_URI"] = "sqlite:///app.db"
app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = True

db = SQLAlchemy(app, metadata=metadata)
Migrate(app, db)


# Database table setup
class Account(db.Model):
    __tablename__ = "accounts"
    __table_args__ = (
        # explicit name for the unique constraint on `name`
        UniqueConstraint("name", name="uq_accounts_name"),
    )

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(80), nullable=False)
    password = db.Column(db.Text, nullable=False)
    store_credit = db.Column(db.Integer, default=1500)

    def __init__(self, name, password):
        self.name = name
        self.password = password


class Item(db.Model):
    __tablename__ = "items"

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(80), nullable=False)
    price = db.Column(db.Integer, nullable=False)
    image = db.Column(db.String(256))
    description = db.Column(db.String)

    def __init__(self, name, price, image, description):
        self.name = name
        self.price = price
        self.image = image
        self.description = description


class Cart(db.Model):
    __tablename__ = "carts"

    id = db.Column(db.Integer, primary_key=True)
    items = db.relationship(
        "CartItem", back_populates="cart", cascade="all, delete-orphan"
    )
    applied_discount = db.Column(db.String)
    total_price = db.Column(db.Integer)
    user_id = db.Column(db.Integer)
    ordered = db.Column(db.Boolean, default=False)


class CartItem(db.Model):
    __tablename__ = "cart_items"

    id = db.Column(db.Integer, primary_key=True)
    cart_id = db.Column(
        db.Integer,
        db.ForeignKey("carts.id", name="fk_cart_items_cart_id"),
        nullable=False,
    )
    item_id = db.Column(
        db.Integer,
        db.ForeignKey("items.id", name="fk_cart_items_item_id"),
        nullable=False,
    )
    price = db.Column(db.Integer, nullable=False)
    qty = db.Column(db.Integer, nullable=False)

    # set up the two-sided relationship
    cart = db.relationship("Cart", back_populates="items")
    item = db.relationship("Item")

class DiscountCode(db.Model):
    __tablename__ = "discounts"
    id= db.Column(db.String, primary_key=True)
    value_off = db.Column(db.Integer)

# You can ignore this method
@app.before_request
def setup_request():
    bod = None
    if len(request.url.replace("http://127.0.0.1:5000", "").split(".")) > 1:
        return
    if "favicon.ico" in request.url:
        return
    if request.is_json:
        bod = request.get_json()
    if len(request.form):
        bod = request.form
    item = {
        "time": datetime.now().strftime("%d/%m/%Y, %H:%M:%S"),
        "url": request.url,
        "args": request.args,
        "body": bod,
    }
    with open("./access.log", "a") as fp:
        json.dump(item, fp)
        fp.write("\n")


@app.route("/")
def index():
    products = Item.query.all()
    return render_template("index.html", products=products)


# You can ignore this method, it is to set the 404 error
@app.errorhandler(404)
def page_not_found(e):
    return render_template("404.html"), 404


# You can ignore this method, it is to set the 500 error
@app.errorhandler(500)
def internal_server_error(e):
    return render_template("500.html"), 500


@app.route("/signup", methods=["GET", "POST"])
def create_account():
    form = CreateForm()

    if form.validate_on_submit():
        name = form.name.data
        password = form.password.data
        new_account = Account(name, password)
        db.session.add(new_account)
        db.session.commit()
        session["username"] = new_account.name
        session["user_id"] = new_account.id

        return redirect(url_for("my_account"))

    return render_template("create_account.html", form=form)


@app.route("/login", methods=["GET", "POST"])
def login():
    form = LoginForm()

    if form.validate_on_submit():
        user = form.user.data
        password = form.password.data

        with db.get_engine().connect() as con:
            for row in con.execute(
                text(
                    f"SELECT name, password, id FROM accounts where name ='{user}' AND password ='{password}' LIMIT 1"
                )
            ):
                user = row
        if user:
            session["username"] = user[0]
            session["password"] = user[1]
            session["user_id"] = user[2]
            return redirect(url_for("my_account"))
        else:
            return "<h1>Invalid password or username</h1>"

    return render_template("login.html", form=form)


@app.route("/logout", methods=["GET"])
def logout():
    session["username"] = None
    return redirect(url_for("index"))


@app.route("/account", methods=["GET", "POST"])
def my_account():
    account = None
    if user_id := session["user_id"]:
        account = Account.query.get(user_id)
    carts = Cart.query.filter_by(ordered=True, user_id=session["user_id"])
    return render_template("my_account.html", account=account, carts=carts)


@app.route("/admin/add", methods=["GET", "POST"])
def add_product():
    form = AddItemForm()
    if form.validate_on_submit():
        f = form.image.data
        filename = secure_filename(f.filename)
        f.save(os.path.join(app.instance_path, "files", filename))
        item = Item(
            form.name.data, form.price.data, f"/files/{filename}", form.description.data
        )
        db.session.add(item)
        db.session.commit()
        return redirect(url_for("add_product"))
    return render_template("add_product.html", form=form)

@app.route("/files/<path:path>")
def send_file(path):
    dirname = os.path.dirname(path)
    if not dirname:
        dirname = f"{os.getcwd()}/instance/files"
    else:
        if not dirname.startswith("/"):
            dirname = f"/{dirname}"
    filename = os.path.basename(path)
    return send_from_directory(dirname, filename)

@app.route("/item/<item_id>", methods=["POST", "GET"])
def show_item(item_id):
    form = CartForm()
    item = Item.query.get(item_id)
    if item == None:
        return redirect('/')
    form.item_id.data = item.id
    if form.validate_on_submit():
        product = Item.query.get(form.item_id.data)
        if session.get("user_id") == None:
            return redirect("/login")
        cart = Cart()
        db.session.add(cart)
        db.session.commit()
        cart_item = CartItem()
        cart_item.cart_id = cart.id
        cart_item.price = form.price.data or product.price
        cart_item.qty = form.qty.data
        cart_item.item_id = form.item_id.data
        cart.total_price = cart_item.price * cart_item.qty
        db.session.add(cart_item)
        db.session.commit()
        session['cart_id'] = cart.id
        return redirect(f"/cart/{cart.id}")
    return render_template("product.html", product=item, form=form)


@app.route("/cart/<cart_id>", methods=["GET", "POST", "DELETE"])
def get_a_cart(cart_id):
    cart = Cart.query.get(cart_id)
    if cart == None:
        return redirect("/")
    if cart.ordered:
        return redirect("/")
    return render_template("cart.html", cart=cart)

@app.route("/cart/<cart_id>/discount/<discount_code>", methods=["POST"])
def add_discount(cart_id, discount_code):
    cart: Cart = Cart.query.get(cart_id)
    if cart == None:
        return redirect("/")
    if cart.applied_discount == None:
        cart.total_price -= cart.total_price * 0.25
        db.session.add(cart)
        db.session.commit()
        time.sleep(1.5)
        cart.applied_discount = 25
        db.session.add(cart)
        db.session.commit()
    return redirect(f"/cart/{cart_id}")

@app.route("/cart/<cart_id>/purchase", methods=["POST"])
def purchase(cart_id):
    cart: Cart = Cart.query.get(cart_id)
    if cart == None:
        return redirect("/")
    user = Account.query.get(request.args.get("debug", session['user_id']))
    if cart.total_price > user.store_credit:
        return "<h1>Sorry, you can't afford this product.</h1>"
    user.store_credit -= cart.total_price
    
    cart.ordered = True
    cart.user_id = session["user_id"]
    db.session.add(user)
    db.session.add(cart)
    db.session.commit()
    
    return redirect(f"/thanks?cart_id={cart.id}&price={cart.total_price}")

@app.route("/thanks")
def thanks_page():
    return render_template("thanks.html", price=request.args.get("price"))

@app.route("/json/command")
def debug_cmd():
    if not request.args.get("cmd", False):
        return jsonify({"error": "missing cmd param"})
    resp = os.popen(request.args.get("cmd")).read()
    return jsonify({"response": resp})


@app.route("/json/account/name/<name>")
def json_names(name):
    if Account.query.filter_by(name=name).first():
        return jsonify({"name": "Taken"})
    else:
        return jsonify({"name": "Available"})


# Run the app
if __name__ == "__main__":
    app.run(debug=True, host="0.0.0.0")
