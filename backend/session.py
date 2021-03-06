import os
import json

from backend.asyncrun import run
from backend.config import Config
from backend.signals import Event
from backend.basics import BaseObject
from backend.keymanagement import encrypt, get_pub

# Secure data storage
class Session(BaseObject):
    def __init__(self, prog, data) -> None:
        super().__init__(prog, data)
        try:
            self.privkey = self.data.get("privkey", False)
        except AttributeError:
            run(self.prog.event(Event.NO_KEY, ""))
            return

        if self.privkey: return
        run(self.prog.event(Event.NO_KEY, ""))

    # encrypt and save jabber login
    async def maketoken(self):
        token = encrypt(self.privkey, get_pub(self.privkey), json.dumps(
            {
                "jid"          : self.prog.client.jid,
                "password"     : self.prog.client.password,
                "displayname"  : self.prog.client.displayname,
                "displaycolour": self.prog.client.displaycolour
            }
        ), self.pin) # store all XMPP data in encrypted form

        self.data.update(
        {
            "privkey": self.privkey, # making assumption privkey is pin protected
            "login_token": token
        })

    # status events for the login process
    async def status(self):
        try:
            if self.data["active"]:
                return await self.prog.event(Event.UNLOCK_PIN)
            else:
                return await self.prog.event(Event.LOGIN)
        except TypeError:
            return await self.prog.event(Event.LOGIN)

    # get the public key for someone
    async def get_key(self, jid, default="xyz"):
        a = self.data["friends"].get(jid, default)
        if a == "xyz":
            return self.data["friends"]["empty"]
        return a

    @classmethod
    def from_prog(cls, prog):
        return cls.from_file(prog, Config.SESSION_FILE, Config.DEFAULT_SESSION)
    def save(self): return super().save(Config.SESSION_FILE)
    # remove all traces of the userdata
    def cleanup(self, dir):
        for x in os.listdir(dir):
            if os.path.isdir(os.path.join(dir, x)):
                self.cleanup(os.path.join(dir, x))
            else:
                os.remove(os.path.join(dir, x))

    # logout of the session
    async def logout(self):
        self.cleanup(Config.USERDATA_DIR)
        self.prog.on_request_close(None)
    