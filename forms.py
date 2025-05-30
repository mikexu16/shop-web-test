from flask_wtf import FlaskForm
from wtforms import (
    StringField,
    IntegerField,
    SubmitField,
    FloatField,
    PasswordField,
    HiddenField,
    FileField,
)
from wtforms.validators import InputRequired, EqualTo
from flask_wtf.file import FileField, FileRequired


class CreateForm(FlaskForm):
    class Meta:
        csrf = False

    name = StringField("Name of Account: ", [InputRequired()])
    password = PasswordField(
        "Account password",
        [InputRequired(), EqualTo("pwd_confirm", message="Passwords must match")],
    )
    pwd_confirm = PasswordField("Confirm account password")
    submit = SubmitField("Create Account")


class LoginForm(FlaskForm):
    class Meta:
        csrf = False

    user = StringField("Username: ", [InputRequired()])
    password = PasswordField("Account password: ", [InputRequired()])
    submit = SubmitField("Login")


class AddItemForm(FlaskForm):
    class Meta:
        csrf = False

    name = StringField("Name of product: ", [InputRequired()])
    description = StringField("Description of product: ", [InputRequired()])
    price = StringField("Price of product: ", [InputRequired()])
    image = FileField(validators=[FileRequired()])
    submit = SubmitField("Add Item")


class CartForm(FlaskForm):
    class Meta:
        csrf = False

    item_id = IntegerField()
    qty = IntegerField("Qty", [InputRequired()])
    price = IntegerField("Price")
    submit = SubmitField("Add to Cart")
