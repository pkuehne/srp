import sqlite3



class Database:
    """ Access to the SRP database """

    FILENAME = './srp.db'

    def __init__(self):
        self.connection = sqlite3.connect(Database.FILENAME)
        self.connection.row_factory = sqlite3.Row

    def close_db(self):
        if self.connection:
            self.connection.close()

    def query_db(self, query, args=(), one=False):
        """
        Generic database query request
        """
        cursor = self.connection.cursor()
        cursor.execute(query, args)
        rv = cursor.fetchall()
        cursor.close()
        self.connection.commit()
        return (rv[0] if rv else None) if one else rv


    def create_db_if_not_exists(self):
        """
        Checks whether the db is set up and if not creates it
        """
        query = "SELECT name FROM sqlite_master"
        rv = self.query_db(query, ())
        if not rv:
            with open('schema.sql', mode='r') as f:
                self.connection.cursor().executescript(f.read())
            self.connection.commit()

    def get_loss(self, killmail_id):
        return self.query_db ("select * from losses where id = ?",
                [killmail_id], one=True)

    def update_loss_status(self, loss_id, status):
        self.query_db("UPDATE losses set status=? WHERE id = ? ",
                (status, loss_id))

    def insert_loss(self, loss):
        query = "INSERT INTO losses (id, hash, character_id, character_name," \
                " ship_type_id, ship_type_name, system_id, system_name, " \
                " timestamp, notes, is_loss, status)" \
                " VALUES (?, ?, ?, ?," \
                " ?, ?, ?, ?," \
                " ?, ?, ?, ?)"
        args = [
                loss["id"],
                loss["hash"],
                loss["character_id"],
                loss["character_name"],
                loss["ship_type_id"],
                loss["ship_type_name"],
                loss["system_id"],
                loss["system_name"],
                loss["timestamp"],
                loss["notes"],
                loss["is_loss"],
                "Unclaimed",
                ]
        result = self.query_db(query, args)

    def load_claim_characters(self):
        query = "SELECT character_id, character_name" \
                " FROM losses WHERE status='Claimed'  GROUP BY 1;"
        return self.query_db(query)

    def load_claims(self, character_id):
        query = "SELECT * FROM losses WHERE status='Claimed'" \
                " AND character_id = ?"
        return self.query_db(query, args=[character_id])

