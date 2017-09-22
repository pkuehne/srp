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
        return None

class Character:
    SERVER = "https://esi.tech.ccp.is"
    BRANCH = "latest"
    SOURCE = "tranquility"
    ALLIANCE="99004116"

    def __init__(self, access_token):
        self.access_token = access_token
        self.id = 0
        self.name = ""
        self.picture = ""
        self.corp = 0
        self.corp_name = ""
        self.alliance = 0
        self.alliance_name = ""
        self.roles = []
        self.losses = []

        self.load_basic_info()
        self.load_picture()
        self.load_corp_and_alliance()
        self.load_roles()
        self.load_losses()

    def call_endpoint(self, endpoint, options={}):
        """ Returns a response for the given endpoint """
        url = "{server}/{branch}/{endpoint}".format(server=Character.SERVER,
                branch=Character.BRANCH,
                endpoint=endpoint)
        options["datasource"] = Character.SOURCE
        options["token"] = self.access_token
        response = requests.get(url, params=options)
        return response

    def load_basic_info(self):
        """ Loads the character ID that we'll need for everything else """
        url = "https://login.eveonline.com/oauth/verify"
        headers = {"Authorization": "Bearer {}".format(self.access_token)}

        response = requests.get(url, headers=headers)
        if not response.ok:
            return

        self.id = response.json()["CharacterID"]
        self.name = response.json()["CharacterName"]

    def load_picture(self):
        """ Loads the picture so the site is pretty """
        endpoint = "characters/{}/portrait".format(self.id)
        response = self.call_endpoint(endpoint)
        if not response.ok:
            return
        self.picture = response.json()["px64x64"]

    def load_roles(self):
        """ Loads the corporation roles for this character """
        endpoint = "characters/{}/roles".format(self.id)
        response = self.call_endpoint(endpoint)
        if not response.ok:
            return
        self.roles = response.json()

    def load_corp_and_alliance(self):
        """ Loads the corp and alliance IDs """

        # Load the corporation for this character
        endpoint = "characters/{}".format(self.id)
        response = self.call_endpoint(endpoint)
        if not response.ok:
            return
        self.corporation = response.json()["corporation_id"]

        # Load the corporation name and alliance ID for the corp
        endpoint = "corporations/{}".format(self.corporation)
        response = self.call_endpoint(endpoint)
        if not response.ok:
            return
        self.corporation_name = response.json()["corporation_name"]
        self.alliance = response.json()["alliance_id"]

        # Load the alliance name
        endpoint = "alliances/{}".format(self.alliance)
        response = self.call_endpoint(endpoint)
        if not response.ok:
            return
        self.alliance_name = response.json()["alliance_name"]

    def load_losses(self):
        """ Loads the kills/losses for this character """
        endpoint = "characters/{}/killmails/recent".format(self.id)
        response = self.call_endpoint(endpoint)
        if not response.ok:
            return
        for mail in response.json():
            loss = self.load_lossmail(mail)
            if loss is not None:
                self.losses.append(loss)

    def load_lossmail(self, killmail_id, killmail_hash):
        """ Loads a mail if it is a loss """
        endpoint = "killmails/{}/{}".format(killmail_id, killmail_hash)
        response = self.call_endpoint(endpoint)
        if not response.ok:
            return
        mail = response.json()
        if mail["victim"] != self.id:
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
            "esi-characters.read_standings.v1"
            "esi-killmails.read_corporation_killmails.v1",
            ]
    params = {
            "response_type":"code",
            "redirect_uri":"http://localhost:5000/callback",
            "client_id":"95d9621354bd4c5ab8af889366b6d61a",
            "scope": ",".join(scopes)
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
        return "You need to authenticate first"

    character = Character(session["access_token"])
    return render_template("killmails.html", character=character)
