import requests
import esi

SHIP_TYPES = {}
SOLAR_SYSTEMS = {}

class Character:
    """
    Represent the information held about a character.

    By default loads only publicly available information with the need for an
    access token. This allows saving the character ID in a database and loading
    the associated character without having to request a new access token

    By calling load_private_info() and supplying an access token, more detailed
    information can be obtained
    """
    ALLIANCE=99004116

    def __init__(self, character_id, db):
        self.access_token = ""
        self.id = character_id
        self.db = db
        self.name = ""
        self.picture = ""
        self.corp = 0
        self.corp_name = ""
        self.alliance = 0
        self.alliance_name = ""
        self.srp_owner = False
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

    def load_pilot_info(self):
        """ Loads name, corp, etc """
        endpoint = "characters/{}".format(self.id)
        response = esi.call_endpoint(endpoint, self.access_token)
        if not response.ok:
            print ("Failed request: {} - {}".format(response.status_code,
                response.content))
            return
        self.name = response.json()["name"]
        self.corporation = response.json()["corporation_id"]

    def load_picture(self):
        """ Loads the picture so the site is pretty """
        endpoint = "characters/{}/portrait".format(self.id)
        response = esi.call_endpoint(endpoint, self.access_token)
        if not response.ok:
            print ("Failed request: {} - {}".format(response.status_code,
                response.content))
            return
        self.picture = response.json()["px64x64"]

    def load_roles(self):
        """ Loads the corporation roles for this character """
        endpoint = "characters/{}/roles".format(self.id)
        response = esi.call_endpoint(endpoint, self.access_token)
        if not response.ok:
            print ("Failed request: {} - {}".format(response.status_code,
                response.content))
            return
        self.roles = response.json()
        self.srp_owner = any([role == "director" for role in self.roles])
        self.srp_owner = self.id == 92959174

    def load_corp_and_alliance_details(self):
        """ Loads the corp and alliance IDs """

        # Load the corporation name and alliance ID for the corp
        endpoint = "corporations/{}".format(self.corporation)
        response = esi.call_endpoint(endpoint, self.access_token)
        if not response.ok:
            print ("Failed request: {} - {}".format(response.status_code,
                response.content))
            return

        self.corporation_name = response.json()["corporation_name"]
        self.alliance = response.json().get("alliance_id", 0)

        # Load the alliance name
        if self.alliance > 0:
            endpoint = "alliances/{}".format(self.alliance)
            response = esi.call_endpoint(endpoint, self.access_token)
            if not response.ok:
                print ("Failed request: {} - {}".format(response.status_code,
                    response.content))
                return
            self.alliance_name = response.json()["alliance_name"]

    def load_losses(self):
        """ Loads the kills/losses for this character """
        endpoint = "characters/{}/killmails/recent".format(self.id)
        response = esi.call_endpoint(endpoint, self.access_token)
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
        loss = self.db.get_loss(killmail_id)
        if loss is None:
            print("Record not found, loading: {}".format(killmail_id))
            loss = self.load_lossmail_from_esi(killmail_id, killmail_hash)
            if  loss is None:
                return None
            self.db.insert_loss(loss)
        if loss["is_loss"]:
            return loss
        return None

    def load_lossmail_from_esi(self, killmail_id, killmail_hash):
        """ Loads the lossmail from ESI """
        endpoint = "killmails/{}/{}".format(killmail_id, killmail_hash)
        response = esi.call_endpoint(endpoint, self.access_token)
        if not response.ok:
            print ("Failed request: {} - {}".format(response.status_code,
                response.content))
            return
        mail = response.json()
        is_loss = mail["victim"]["character_id"] == self.id
        loss = {
                "id": killmail_id,
                "hash": killmail_hash,
                "character_id": self.id,
                "character_name": self.name,
                "ship_type_id": mail["victim"]["ship_type_id"],
                "ship_type_name": self.load_ship_type(mail["victim"]["ship_type_id"]),
                "system_id": mail["solar_system_id"],
                "system_name": self.load_system_name(mail["solar_system_id"]),
                "timestamp": mail["killmail_time"],
                "is_loss": is_loss,
                "notes": "",
                "market_price": self.load_market_price(mail["victim"]["ship_type_id"]),
                "status": "Unclaimed",
                }
        return loss

    def load_ship_type(self, ship_type_id):
        """ Returns the ship name from the type ID """
        if ship_type_id in SHIP_TYPES:
            return SHIP_TYPES[ship_type_id]

        endpoint = "universe/types/{}".format(ship_type_id)
        response = esi.call_endpoint(endpoint, self.access_token)
        if not response.ok:
            print ("Failed request: {} - {}".format(response.status_code,
                response.content))
            return
        SHIP_TYPES[ship_type_id] = response.json()["name"]
        return SHIP_TYPES[ship_type_id]

    def load_system_name(self, system_id):
        """ Returns the name of the requested solar system """
        if system_id in SOLAR_SYSTEMS:
            return SOLAR_SYSTEMS[system_id]

        endpoint = "universe/systems/{}".format(system_id)
        response = esi.call_endpoint(endpoint, self.access_token)
        if not response.ok:
            print ("Failed request: {} - {}".format(response.status_code,
                response.content))
            return
        SOLAR_SYSTEMS[system_id] = response.json()["name"]
        return SOLAR_SYSTEMS[system_id]


