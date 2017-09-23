from flask import Flask, redirect, request, url_for, session, render_template
import requests

app = Flask(__name__)
app.secret_key = "TYDEUS"

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

class Character:
    """
    Represent the information held about a character.

    By default loads only publicly available information with the need for an
    access token. This allows saving the character ID in a database and loading
    the associated character without having to request a new access token

    By calling load_private_info() and supplying an access token, more detailed
    information can be obtained
    """
    SERVER = "https://esi.tech.ccp.is"
    BRANCH = "latest"
    #SOURCE = "singularity" #Also change login URL!
    SOURCE = "tranquility"
    ALLIANCE=99004116

    def __init__(self, character_id):
        self.access_token = ""
        self.id = character_id
        self.name = ""
        self.picture = ""
        self.corp = 0
        self.corp_name = ""
        self.alliance = 0
        self.alliance_name = ""
        self.roles = []
        self.losses = []

        self.load_public_info()

    def load_public_info(self):
        """ Loads info available without access token """
        self.load_pilot_info()
        self.load_picture()
        self.load_corp_and_alliance_details()

    def load_private_info(self, access_token):
        """ Loads info only accessible with an access token """
        self.access_token = access_token
        self.load_roles()
        self.load_losses()

    def call_endpoint(self, endpoint, options={}):
        """ Returns a response for the given endpoint """
        url = "{server}/{branch}/{endpoint}".format(server=Character.SERVER,
                branch=Character.BRANCH,
                endpoint=endpoint)

        options["datasource"] = Character.SOURCE

        headers = {}
        headers["Accept"] = "application/json"
        if self.access_token:
            headers["Authorization"] = "Bearer {}".format(self.access_token)

        response = requests.get(url, params=options, headers=headers)
        return response

    def load_pilot_info(self):
        """ Loads name, corp, etc """
        endpoint = "characters/{}".format(self.id)
        response = self.call_endpoint(endpoint)
        if not response.ok:
            print ("Failed request: {} - {}".format(response.status_code,
                response.content))
            return
        self.name = response.json()["name"]
        self.corporation = response.json()["corporation_id"]

    def load_picture(self):
        """ Loads the picture so the site is pretty """
        endpoint = "characters/{}/portrait".format(self.id)
        response = self.call_endpoint(endpoint)
        if not response.ok:
            print ("Failed request: {} - {}".format(response.status_code,
                response.content))
            return
        self.picture = response.json()["px64x64"]

    def load_roles(self):
        """ Loads the corporation roles for this character """
        endpoint = "characters/{}/roles".format(self.id)
        response = self.call_endpoint(endpoint)
        if not response.ok:
            print ("Failed request: {} - {}".format(response.status_code,
                response.content))
            return
        self.roles = response.json()

    def load_corp_and_alliance_details(self):
        """ Loads the corp and alliance IDs """

        # Load the corporation name and alliance ID for the corp
        endpoint = "corporations/{}".format(self.corporation)
        response = self.call_endpoint(endpoint)
        if not response.ok:
            print ("Failed request: {} - {}".format(response.status_code,
                response.content))
            return

        self.corporation_name = response.json()["corporation_name"]
        self.alliance = response.json().get("alliance_id", 0)

        # Load the alliance name
        if self.alliance > 0:
            endpoint = "alliances/{}".format(self.alliance)
            response = self.call_endpoint(endpoint)
            if not response.ok:
                print ("Failed request: {} - {}".format(response.status_code,
                    response.content))
                return
            self.alliance_name = response.json()["alliance_name"]

    def load_losses(self):
        """ Loads the kills/losses for this character """
        endpoint = "characters/{}/killmails/recent".format(self.id)
        response = self.call_endpoint(endpoint)
        if not response.ok:
            print ("Failed request: {} - {}".format(response.status_code,
                response.content))
            return
        for mail in response.json():
            loss = self.load_lossmail(mail["killmail_id"], mail["killmail_hash"])
            if loss is not None:
                self.losses.append(loss)

    def load_lossmail(self, killmail_id, killmail_hash):
        """ Loads a mail if it is a loss """
        endpoint = "killmails/{}/{}".format(killmail_id, killmail_hash)
        response = self.call_endpoint(endpoint)
        if not response.ok:
            print ("Failed request: {} - {}".format(response.status_code,
                response.content))
            return
        mail = response.json()
        if mail["victim"]["character_id"] != self.id:
            return None
        # Ding, ding, ding, a loss mail
        loss = {
                "id": killmail_id,
                "hash": killmail_hash,
                "ship_type": mail["victim"]["ship_type_id"]
                }
        return loss

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
    return "<a href='{}'>Sign in here</a>".format(link)

@app.route("/callback")
def callback():
    code = request.args.get('code', None)
    if code is None:
        return "Failed to extract code"
    tokens = get_access_token(code)
    if tokens is not None:
        session["access_token"] = tokens["access_token"]
        session["refresh_token"] = tokens["refresh_token"]
        return redirect (url_for("killmails"))
    return "Failed to get access token"

@app.route("/killmails")
def killmails():
    """ Displays a list of all killmails """
    if "access_token" not in session:
        return redirect (url_for("start_auth"))

    character_id = get_character_id(session["access_token"])
    if character_id is None:
        print ("Token expired")
        return redirect (url_for("start_auth"))

    character = Character(character_id)
    if character.alliance != Character.ALLIANCE:
        print ("Invalid Alliance ID: {}".format(character.alliance))
        return "You must be a member of Warped Intentions!"

    character.load_private_info(session["access_token"])
    return render_template("killmails.html", character=character)
