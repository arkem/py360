"""
These classes handles XDBF files (Xbox 360 Database Files) such as the Gamer Profile Data (GPD) files.
TODO: Support SPA files as well as GPD files
TODO: Handle Sync Lists
TODO: Sort out unicode problems
"""

import struct
import xboxtime
import time
from constants import GPDID, GamerTagConstants

class Setting(object):
    """ Represents a Setting entry
        Some values can be resolved by matching them against constant objects
        See contents.GPDID, contents.GamerTagConstants    
    """
    def __str__(self):
        result = ["GPD Setting"]
        if self.setting_id in GPDID.types:
            result.append("%s" % GPDID.types[self.setting_id])
        else:
            result.append(hex(self.setting_id))

        if self.content_id > 0 and self.content_id < 6:
            try:
                if GPDID.types[self.setting_id] == 'Region':
                    result.append(GamerTagConstants.Region[self.data])
                elif GPDID.types[self.setting_id] == 'GamerZone':
                    result.append(GamerTagConstants.GamerZone[self.data])
                else:
                    result.append(str(self.data))
            except KeyError:
                result.append(str(self.data))

        if self.content_id == 7:
            result.append(time.ctime(xboxtime.filetime2unixtime(self.data)))
        return " ".join(result)

    def __init__(self, data, byte_order = '>'):
        self.content_id = ord(data[8])
        self.setting_id = struct.unpack(byte_order + 'I', data[0:4])[0]

        if self.content_id == 0: # Context
            self.data = struct.unpack(byte_order + "I", data[16:20])[0]

        elif self.content_id == 1: #Unsigned Integer
            self.data = struct.unpack(byte_order + "I", data[16:20])[0]

        elif self.content_id == 2: #Long long
            self.data = struct.unpack(byte_order + "Q", data[16:24])[0]
        
        elif self.content_id == 3: #Double
            self.data = struct.unpack(byte_order + "d", data[16:24])[0]

        elif self.content_id == 4: #UTF16-BE
            length = struct.unpack(byte_order + "I", data[16:20])[0]
            self.data = unicode(data[24:24+length], 'utf-16-be')

        elif self.content_id == 5: #Float
            self.data = struct.unpack(byte_order + "f", data[16:20])[0]

        elif self.content_id == 6: #Binary
            length = struct.unpack(byte_order + "I", data[16:20])[0]
            self.data = data[24:24+length]

        elif self.content_id == 7: #Timestamp
            self.data = struct.unpack(byte_order + "Q", data[16:24])[0]

        else: #Null
            self.data = data[9:17]

class Title(object):
    """ Represents a title entry
        Includes the name, last played time and achievement stats
    """
    def __str__(self):
        result = ["GPD Title"]
        result.append(self.get_name())
        result.append(hex(self.title_id))
        return " ".join(result)
        
    def __init__(self, data, byte_order = '>'):
        self.title_id = struct.unpack(byte_order + 'I', data[0:4])[0]
        self.achievement_count = struct.unpack(byte_order + 'i', data[4:8])[0]
        self.achievement_unlocked = struct.unpack(byte_order + 'i', data[8:12])[0]
        self.gamerscore_total = struct.unpack(byte_order + 'i', data[12:16])[0]
        self.gamerscore_unlocked = struct.unpack(byte_order + 'i', data[16:20])[0]
        self.unknown1 = struct.unpack(byte_order + 'q', data[20:28])[0]
        self.unknown2 = struct.unpack(byte_order + 'i', data[28:32])[0]
        self.last_played = struct.unpack(byte_order + 'q', data[32:40])[0]
        end_name = 40 + data[40:].find('\x00\x00')
        self.name = data[40:end_name]

    # Due to intermittent unicode problems I decided to store the data raw and convert it only when needed
    def get_name(self):
        """ Convert the name from utf-16-be data in a raw string to a unicode object """
        if self.name:
            return unicode(self.name, 'utf-16-be')
        else:
            return u''

class Achievement(object):
    """ Achievement entry object
        Includes name, descriptions and unlock time
    """
    def __str__(self):
        result = ["GPD Achievement"]
        if self.achievement_id:
            result.append(hex(self.achievement_id))
        result.append(self.get_name())
        return " ".join(result)

    def __init__(self, data, byte_order = '>'):
        self.achievement_id = None
        self.image_id = None
        self.gamer_score = None
        self.flags = None
        self.unlock_time = None
        self.name = None
        self.locked_desc = None
        self.unlocked_desc = None
        self.magic = struct.unpack(byte_order + 'I', data[0:4])[0]
        if self.magic != 28 or len(data) < 28:
            return
        self.achievement_id = struct.unpack(byte_order + 'I', data[4:8])[0]
        self.image_id = struct.unpack(byte_order + 'I', data[8:12])[0]
        self.gamer_score = struct.unpack(byte_order + 'I', data[12:16])[0]
        self.flags = struct.unpack(byte_order + 'I', data[16:20])[0]
        self.unlock_time = xboxtime.filetime2unixtime(struct.unpack(byte_order + 'q', data[20:28])[0])

        end_name = 28 + data[28:].find('\x00\x00')
        self.name = data[28:end_name]
        end_locked_desc = end_name + 2 + data[end_name+2:].find('\x00\x00') #+2 to skip previous null
        self.locked_desc = data[end_name+2:end_locked_desc]
        end_unlocked_desc = end_locked_desc + 2 + data[end_locked_desc+2:].find('\x00\x00')
        self.unlocked_desc = data[end_locked_desc+2:end_unlocked_desc]

    def get_name(self):
        """ Convert the name from utf-16-be data in a raw string to a unicode object """
        if self.name:
            return unicode(self.name, 'utf-16-be')
        else:
            return u''

    def get_locked_desc(self):
        """ Convert the locked description from utf-16-be data in a raw string to a unicode object """
        if self.locked_desc:
            return unicode(self.locked_desc, 'utf-16-be')
        else:
            return u''

    def get_unlocked_desc(self):
        """ Convert the unlocked description from utf-16-be data in a raw string to a unicode object """
        if self.unlocked_desc:
            return unicode(self.unlocked_desc, 'utf-16-be')
        else:
            return u''

class Entry(object):
    """ Entry object which describes where to find the data inside the file and its payload type 
        The namespace class member maps namespace numbers to data type
    """
    namespaces = {1: 'Achievement', 2: 'Image', 3:'Setting', 4:'Title', 5:'String', 6:'Achievement Security'}

    def __str__(self):
        return "GPD Entry: %s %s" % (hex(self.idnum), Entry.namespaces[self.namespace]) 

    def __init__(self, data, global_offset, fd, byte_order = '>'):
        self.namespace = struct.unpack(byte_order + 'H', data[0:2])[0]
        self.idnum = struct.unpack(byte_order + 'Q', data[2:10])[0]
        self.offset = struct.unpack(byte_order + 'I', data[10:14])[0]
        self.length = struct.unpack(byte_order + 'I', data[14:18])[0]
        self.payload = None


        if self.namespace not in Entry.namespaces or\
        self.length <= 0:
            return

        # TODO: Get paydata
        fd.seek(self.offset + global_offset)
        paydata = fd.read(self.length) 
        if Entry.namespaces[self.namespace] == 'Achievement':
            if len(paydata) > 28:
                self.payload = Achievement(paydata, byte_order)
            else:
                return
        elif Entry.namespaces[self.namespace] == 'Title': 
            if len(paydata) > 40:
                self.payload = Title(paydata, byte_order)
            else:
                return
        elif Entry.namespaces[self.namespace] == 'Setting':
            if len(paydata) > 20:
                self.payload = Setting(paydata, byte_order)
            else:
                return
        else:
            self.payload = paydata

class XDBF(object):
    """ 
        Main object representing a GPD/XDBF archive
        Contains dictionaries that map id numbers to entries
        achievements, images, strings, titles, settings
        These can also be accessed via the list of Entry objects and their payload member
    """
    def __str__(self):
        return "XDBF (%s - %d)" % (self.filename, len(self.entries))

    def __init__(self, filename, fd=None):
        self.filename = filename
        if not fd:
            self.fd = open(filename)
        else:
            self.fd = fd
        data = self.fd.read(0x18)
        
        if data[:4] == "\x58\x44\x42\x46": #XDBF
            self.byte_order = '>'
        elif data[:4] == "\x46\x42\x44\x58": #FBDX
            self.byte_order = '<'
        else:
            raise AssertionError("XDBF Magic Not Found")

        self.version = struct.unpack(self.byte_order + 'I', data[4:8])[0]
        self.table_len = struct.unpack(self.byte_order + 'I', data[8:12])[0]
        self.entry_count = struct.unpack(self.byte_order + 'I', data[12:16])[0]
        self.free_len = struct.unpack(self.byte_order + 'I', data[16:20])[0]
        self.free_count = struct.unpack(self.byte_order + 'I', data[20:24])[0]
        self.global_offset = self.table_len * 0x12 + self.free_len * 0x8 + 0x18


        self.entries = []
        self.achievements = {}
        self.images = {}
        self.settings = {}
        self.titles = {}
        self.strings = {}
        self.process_entries()
        self.fd.close()

    def process_entries(self):
        """ Populates the entries list and the various payload dictionaries """
        for c in xrange(0, self.entry_count):
            self.fd.seek(0x18 + 0x12 * c, 0) 
            data = self.fd.read(0x12)
            e = Entry(data, self.global_offset, self.fd, self.byte_order)
            self.entries.append(e)

            if e.payload: 
                ns = Entry.namespaces[e.namespace]
                if ns == 'Achievement':
                    self.achievements[e.idnum] = e.payload
                elif ns == 'Title':
                    self.titles[e.idnum] = e.payload
                elif ns == 'Setting':
                    self.settings[e.idnum] = e.payload
                elif ns == 'Image':
                    self.images[e.idnum] = e.payload
                elif ns == 'String':
                    self.strings[e.idnum] = e.payload

def print_xdbf(argv):
    if len(argv) < 2:
        print "USAGE: xdbf.py options [file.gpd] <file2.gpd> ... <filen.gpd>"
        print "Options:"
        print "\t\t-p [directory]\t dump images to directory as filename-ID.png"
        return

    dump_png = False
    if argv[1] == '-p' and len(argv) > 2:
        dump_png = True
        directory = argv.pop(2)
        argv.pop(1)

    for fname in argv[1:]:
        print "Processing %s" % fname
        x = XDBF(fname)
        print x
        for e in x.entries:
            print e
        for t in x.titles:
            print x.titles[t]
        for a in x.achievements:
            try:
                print x.achievements[a]
            except UnicodeEncodeError:
                print "Unicode error: Achievement %s" % x.achievements[a].name
        for s in x.settings:
            print x.settings[s]
        for st in x.strings:
            try:
                print "String 0x%x: %s" % (st, unicode(x.strings[st], 'utf-16-be').strip('\x00'))
            except UnicodeEncodeError:
                print "Unicode error: String %s:" % x.strings[st]
        for i in x.images:
            print "Image 0x%x" % i
            if dump_png:
                outfile = "%s/%s-%s.png" % (directory, os.path.basename(fname), hex(i))
                print "Dumping image to %s" % (outfile)
                open(outfile, 'w').write(x.images[i])

if __name__ == '__main__':
    import sys, os
    print_xdbf(sys.argv)
