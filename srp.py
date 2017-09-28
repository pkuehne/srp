from flask import Flask # Main flask setup
from flask import redirect # Redirect requests to other handlers
from flask import request # Access to the request
from flask import url_for # To dynamically generate routes
from flask import session # Cookie support
from flask import render_template # Actually return a jinja template
from flask import g # The global context
from flask import flash # Show message from one request to the next
import requests

from character import Character
from database import Database
import esi

app = Flask(__name__)
app.secret_key = "TYDEUS"

def cache_market_prices():
    endpoint = "markets/prices"
    response = esi.call_endpoint(endpoint)
    if not response.ok:
        print ("Failed request: {} - {}".format(response.status_code,
            response.content))
        return
    items = response.json()
    cache = {}
    for item in items:
        cache[item["type_id"]] = item["adjusted_price"]
    return cache

def price_cache():
    """
    Warms up the price cache if its not set yet
    """
    cache = getattr(g, '_cache', None)
    if cache is None:
        cache = g._cache = cache_market_prices()
    return cache

def db():
    """
    Returns the current db context or creates it if it doesn't exist
    """
    db = getattr(g, '_database', None)
    if db is None:
        db = g._database = Database()
    db.create_db_if_not_exists()
    return db

@app.teardown_appcontext
def close_connection(exception):
    """
    Automatically closes the connection to the db when the app context closes
    """
    db = getattr(g, '_database', None)
    if db is not None:
        db.close_db()

def get_access_token(code):
    """ Get my access token for testing """
    client_id = "OTVkOTYyMTM1NGJkNGM1YWI4YWY4ODkzNjZiNmQ2MWE6VVZ1aGtoelVxcUVqWlo3VnRnTGVOZU1pTXJ1QUUwQ2U1VGN4WTVjYw=="
    login_url = "https://login.eveonline.com/oauth/token"
    headers = {"Authorization": "Basic {}".format(client_id)}
    payload = {"grant_type":"authorization_code", "code": code}

    response = requests.post(login_url, data=payload, headers=headers)
    if response.ok:
        return {
                "refresh_token": response.json()["refresh_token"],
                "access_token": response.json()["access_token"]
                }
        print ("Failed request: {} - {}".format(response.status_code,
            response.content))
        return None

def get_character_id(access_token):
    """ Loads the character ID that we'll need for everything else """
    url = "https://login.eveonline.com/oauth/verify"
    headers = {"Authorization": "Bearer {}".format(access_token)}

    response = requests.get(url, headers=headers)
    if not response.ok:
        print ("Failed request: {} - {}".format(response.status_code,
            response.content))
        return None

    return response.json()["CharacterID"]

@app.route("/")
def start_auth():
    login_url="https://login.eveonline.com/oauth/authorize"
    scopes = [
            "esi-killmails.read_killmails.v1",
            "esi-characters.read_corporation_roles.v1",
            ]
    params = {
            "response_type":"code",
            "redirect_uri":"http://localhost:5000/callback",
            "client_id":"95d9621354bd4c5ab8af889366b6d61a",
            "scope": " ".join(scopes)
            }
    options = '&'.join('{}={}'.format(key, value) for key, value in params.items())

    link = "{login_url}?{options}".format(login_url=login_url, options=options)
    return render_template("auth.html", link=link)

@app.route("/callback")
def callback():
    code = request.args.get('code', None)
    if code is None:
        return "Failed to extract code"
    tokens = get_access_token(code)
    if tokens is None:
        flash("Failed to get access token")
        return redirect (url_for("start_auth"))

    session["access_token"] = tokens["access_token"]
    session["refresh_token"] = tokens["refresh_token"]
    return redirect (url_for("killmails"))

@app.route("/killmails")
def killmails():
    """ Displays a list of all killmails """
    if "access_token" not in session:
        return redirect (url_for("start_auth"))

    character_id = get_character_id(session["access_token"])
    if character_id is None:
        flash ("Token expired")
        return redirect (url_for("start_auth"))

    character = Character(character_id, db())
    if character.alliance != Character.ALLIANCE:
        print ("Invalid Alliance ID: {}".format(character.alliance))
        return "You must be a member of Warped Intentions!"

    character.load_private_info(session["access_token"])
    return render_template("killmails.html", character=character)

@app.route("/claim_losses", methods=["POST"])
def claim_losses():
    character_id = get_character_id(session["access_token"])
    if character_id is None:
        flash ("Token expired")
        return redirect (url_for("start_auth"))

    print (request.form)
    for loss_id in request.form.keys():
        status = request.form[loss_id]
        db().update_loss_status(loss_id, status)

    return redirect(url_for("killmails"))

@app.route("/view_claims")
def view_claims():
    character_id = get_character_id(session["access_token"])
    if character_id is None:
        flash ("Token expired")
        return redirect (url_for("start_auth"))

    character = Character(character_id, db())
    if character.alliance != Character.ALLIANCE:
        print ("Invalid Alliance ID: {}".format(character.alliance))
        return "You must be a member of Warped Intentions!"

    rows = db().load_claim_characters()
    claims = []
    for row in rows:
        claim = dict(zip(row.keys(), row))
        entries = db().load_claims(claim["character_id"])
        claim["loss_total"] = 0
        claim["losses"] = []
        for entry in entries:
            loss = dict(zip(entry.keys(), entry))
            loss["price"] = price_cache()[loss["ship_type_id"]]
            claim["loss_total"] += loss["price"]
            claim["losses"].append(loss)
        claims.append(claim)

    if len(claims) == 0:
        flash ("There are no claims to review")
        return redirect(url_for("killmails"))
    return render_template("claims.html", claims=claims)

