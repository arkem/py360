"""
    Module for processing encrypted Account blocks

 From various xbox 360 forums and code examples (including DJ Shepherd's Le Fluffie)
 Most of the offsets had to be adjusted which makes me wonder if there's a small problem in the decryption

 Decrypted Data
 0x00: Account flags? (5th bit is Live/Local Account (possibly), 4th bit is passcode enabled?)
 0x01: Passcode 4 bytes (or at position 0x38?)
 0x10: GamerTag (utf-16-be, 15 characters)
 0x30: XUID (8 bytes)
 0x3c: Account type "PROD" or "PART"
 0x39: Membership type 1 byte (0x30 is Silver, 0x60 is Gold)

 Passcode
 Null = 0, Up = 1, Down = 2, Left = 3, Right = 4, X = 5, Y = 6, 
 Left Trigger = 9, Right Trigger = 0xA, Left Bumper = 0xB, Right Bumper = 0xC
 Speculation: A = 7, B = 8
"""
import hashlib
import hmac
import struct
from Crypto.Cipher import ARC4

class Account(object):
    """ Account object, decrypts the buf and populates its members """
    def __str__(self):
        return "Xbox 360 Account: %s, type: %s" % (self.get_gamertag(), self.live_type)

    def __init__(self, encrypted):
        self.key = ["\xE1\xBC\x15\x9C\x73\xB1\xEA\xE9\xAB\x31\x70\xF3\xAD\x47\xEB\xF3", # PROD KEY
                    "\xDA\xB6\x9A\xD9\x8E\x28\x76\x4F\x97\x7E\xE2\x48\x7E\x4F\x3F\x68"] # OTHER KEY

        self.passcode_map = {0x00: "Null", 0x01: "Up", 0x02: "Down", 0x03: "Left", 0x04: "Right", 0x05: "X", 
                             0x06: "Y", 0x07: "A?", 0x08: "B?", 0x09: "Left Trigger", 0x0A: "Right Trigger",
                             0x0B: "Left Bumper", 0x0C: "Right Bumper"}

        assert len(encrypted) == 404, "Account block of an incorrect length" 
        self.data = self.decrypt(encrypted)

        if ord(self.data[0]) >> 5 & 0x01 == 0x01:
            self.live_account = True
            self.xuid = "".join(["%.2x" % ord(c) for c in self.data[0x30:0x38]])
        else:
            self.live_account = False
            self.xuid = '\x00'

        self.gamertag = self.data[0x10:0x2e]

        try:
            self.passcode = " ".join([self.passcode_map[x] for x in self.data[0x01:0x05]])
        except:
            self.passcode = None

        live_type = ord(self.data[0x39])
        if live_type == 0x30:
            self.live_type = "Silver (Free)"
        elif live_type == 0x60:
            self.live_type = "Gold (Paid)"
        else:
            self.live_type = "Offline"

        self.console_type = self.data[0x3c:0x40]
        
    def decrypt(self, data, key=None):
        if not key:
            key = self.key[0]
        hmackey = hmac.new(key, data[:16], hashlib.sha1).digest()[0:0x10]
        return ARC4.new(hmackey[0:0x16]).decrypt(data[16:])

    def get_gamertag(self):
        """ Return the gamertag name from this account block """
        return unicode(self.gamertag, 'utf-16-be').strip('\x00')
        
