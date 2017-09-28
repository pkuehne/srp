import requests

SERVER = "https://esi.tech.ccp.is"
BRANCH = "latest"
SOURCE = "tranquility"

def call_endpoint(endpoint, access_token=None, options={}):
    """ Returns a response for the given endpoint """
    url = "{server}/{branch}/{endpoint}".format(server=SERVER,
            branch=BRANCH,
            endpoint=endpoint)

    options["datasource"] = SOURCE

    headers = {}
    headers["Accept"] = "application/json"
    if access_token:
        headers["Authorization"] = "Bearer {}".format(access_token)

    response = requests.get(url, params=options, headers=headers)
    return response

