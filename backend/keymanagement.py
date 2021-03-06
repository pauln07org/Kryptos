import re
import pgpy
import secrets

from hashlib import sha256
from pgpy.constants import PubKeyAlgorithm, KeyFlags, HashAlgorithm, SymmetricKeyAlgorithm, CompressionAlgorithm

# Depricated
def generate_seed(length=16):
    with open("backend/db/words.txt", "r") as f:
        words = f.read().strip().split("\n")

    out = []
    for i in range(length):
        out.append(secrets.choice(words))

    return out

# Generate a PGP key with atached data
def generate_key(name="DefaultName", colour="", protection=""):
    key = pgpy.PGPKey.new(PubKeyAlgorithm.RSAEncryptOrSign, 4096)

    uid = pgpy.PGPUID.new(validate_name(name), comment=validate_hex(colour))

    key.add_uid(uid, usage={KeyFlags.Sign, KeyFlags.EncryptCommunications, KeyFlags.EncryptStorage},
                hashes=[HashAlgorithm.SHA256, HashAlgorithm.SHA384, HashAlgorithm.SHA512, HashAlgorithm.SHA224],
                ciphers=[SymmetricKeyAlgorithm.AES256, SymmetricKeyAlgorithm.AES192, SymmetricKeyAlgorithm.AES128],
                compression=[CompressionAlgorithm.ZLIB, CompressionAlgorithm.BZ2, CompressionAlgorithm.ZIP, CompressionAlgorithm.Uncompressed])

    key.protect(protection, SymmetricKeyAlgorithm.AES256, HashAlgorithm.SHA256)

    return str(key)

# Depricated
def id_from_priv(key):
    return id_from_pub(get_pub(key))
# Depricated
def id_from_pub(key):
    key, _ = pgpy.PGPKey.from_blob(key)
    return sha256(str(key.encrypt(pgpy.PGPMessage.new("id"))).encode()).hexdigest()

# make sure a hexstring color is validif not compensate
def validate_hex(data): # verify valid hex colour
    data = data[0:7] # remove alpha value
    if re.search(r'^#(?:[0-9a-fA-F]{3}){1,2}$', data):
        return data
    else:
        return "#eeeeee"

# make sure a username is acceptable
def validate_name(data): # verify username length
    return data[0:32] # TODO: add to config

# get uername and color from a bubliuc key
def get_info(key):
    key, _ = pgpy.PGPKey.from_blob(key)
    return (validate_name(key.userids[0].name), validate_hex(key.userids[0].comment))

# change the info on a private key
def change_info(key, name, colour, auth):
    old = get_info(key) # only update new shit
    name = old[0] if name == None else validate_name(name)
    colour = old[1] if colour == None else validate_hex(colour)

    privkey, _ = pgpy.PGPKey.from_blob(key)
    with privkey.unlock(auth):
        privkey.del_uid(old[0])
        uid = pgpy.PGPUID.new(name, comment=colour)

        privkey.add_uid(uid, usage={KeyFlags.Sign, KeyFlags.EncryptCommunications, KeyFlags.EncryptStorage},
                    hashes=[HashAlgorithm.SHA256, HashAlgorithm.SHA384, HashAlgorithm.SHA512, HashAlgorithm.SHA224],
                    ciphers=[SymmetricKeyAlgorithm.AES256, SymmetricKeyAlgorithm.AES192, SymmetricKeyAlgorithm.AES128],
                    compression=[CompressionAlgorithm.ZLIB, CompressionAlgorithm.BZ2, CompressionAlgorithm.ZIP, CompressionAlgorithm.Uncompressed])

    return str(privkey)

# get the public key from a privat key
def get_pub(key):
    key, _ = pgpy.PGPKey.from_blob(key)
    return str(key.pubkey)

# sign data with a private key
def sign(key, data):
    key, _ = pgpy.PGPKey.from_blob(key)
    h = sha256(data.encode()).hexdigest()

    return str(key.sign(h))

# verify signed data with a public key
def verify(key, data, signature):
    key, _ = pgpy.PGPKey.from_blob(key)
    h = sha256(data.encode()).hexdigest()
    a = key.verify(h, pgpy.PGPSignature.from_blob(signature))
    return a.__bool__()

# specificaly verify a message with public key
def verify_msg(key, message):
    key, _ = pgpy.PGPKey.from_blob(key)
    msg = pgpy.PGPMessage.from_blob(message)
    a = key.verify(msg)
    return a.__bool__()

# Depricated
def get_msg_id(fromuser, touser, data):
    return sha256(("{}:{}:::{}".format(fromuser, touser, data)).encode()).hexdigest()

# encrypts data in textsafe format
def encrypt(privkey, pubkey, data, auth=""):
    privkey, _ = pgpy.PGPKey.from_blob(privkey)
    with privkey.unlock(auth):
        pubkey, _ = pgpy.PGPKey.from_blob(pubkey)

        msg = pgpy.PGPMessage.new(data)
        msg |= privkey.sign(msg)
        msg = pubkey.encrypt(msg)
    return str(msg)

# get key id
def get_id(pubkey):
    pubkey, _ = pgpy.PGPKey.from_blob(pubkey)

    return pubkey.fingerprint

# check if a pin works for the key
def checkpin(privkey, auth):
    try:
        privkey, _ = pgpy.PGPKey.from_blob(privkey)
        with privkey.unlock(auth):
            return True
    except pgpy.pgp.PGPDecryptionError:
        return False
# decrypt data with the private key
def decrypt(privkey, pubkey, data, auth):
    privkey, _ = pgpy.PGPKey.from_blob(privkey)
    with privkey.unlock(auth):
        pubkey, _ = pgpy.PGPKey.from_blob(pubkey)

        # handle message errors
        try:
            msg = privkey.decrypt(pgpy.PGPMessage.from_blob(data))
        except Exception as e:
            return "Message decryption error."
        try:
            if not pubkey.verify(msg).__bool__(): return "Message authenticity error."
        except Exception as e:
            return "Message authenticity error."

    return msg.message if isinstance(msg.message, str) else msg.message.decode() # TODO: handle non convertable charecters

# extract data from a contact string
def contact_data(contactstring):
    try:
        d1 = contactstring.split("-", 1)[1].split("-")
        address = "-".join(d1[0:-1])
        id = d1[-1]
        return address, id
    except: # i blame the user for fucking something up; a catchall is always good practise lol
        return False