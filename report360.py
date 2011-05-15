"""
A class to output information about py360 types
Report360.document_image processes an entire disk image
This is a quick conversion from the previous solution of a few functions.
This version allows function reuse and swaps prints with a call to Report360.output to allow preprocessing
"""

import time, os, sys
from py360 import xdbf, partition, account, stfs, xboxmagic, xboxtime
from cStringIO import StringIO

class Report360:
    """ A class to output information about py360 types """
    def __init__(self, filename = None, image_directory = None, out = sys.stdout, err = sys.stderr):
        self.filename = filename
        self.image_directory = image_directory
        self.outfd = out
        self.errfd = err
    
    def output(self, string, fd = None):

        if fd == None:
            fd = self.outfd

        if type(string) != type(""):
            string = str(string)

        # This is my ugly hack for ensuring output is in UTF-8. The underlying unicode problem remains.
        fd.write("%s\n" % "".join([x for x in string if (ord(x)>=32 and ord(x)<127) or x == '\t' or x == '\n']))

    def print_account(self, acc):
        """ Prints out information from an Account block """
        
        self.output("\n*********************")
        self.output(acc)
        self.output("*********************")
        self.output("XUID: %s" % acc.xuid)
        if acc.live_account:
            self.output("Account Type: %s" % acc.live_type)
        else:
            self.output("Account Type: Local")
        self.output("Console Type: %s" % acc.console_type)
        if acc.passcode:
            self.output("Passcode: %s" % acc.passcode)
        

    def print_xtaf(self, part):
        """ Prints out information about an XTAF partition """
        self.output("\n*********************")
        self.output(part)
        self.output("*********************")
        self.output("\nFILE LISTING")
        #for filename in part.allfiles:
        for filename in part.walk():
            fi = part.get_file(filename)
            if fi.fr:
                self.output("File: %s\t%d" % (filename, fi.fr.fsize))
                self.output("%s\t%s\t%s\n" % (time.ctime(xboxtime.fat2unixtime(fi.fr.mtime, fi.fr.mdate)),\
                                            time.ctime(xboxtime.fat2unixtime(fi.fr.atime, fi.fr.adate)),\
                                            time.ctime(xboxtime.fat2unixtime(fi.fr.ctime, fi.fr.cdate))))
                                            
    def print_stfs(self, stf):
        """ Prints out information contained in the provided STFS object """
        self.output("\n*********************")
        self.output(stf)
        self.output("*********************")
        #TODO: Include some of the header data
        self.output("Name: %s" % str(stf.display_name))
        self.output("Description: %s" % str(stf.display_description))
        self.output("\nFILE LISTING")
        for filename in stf.allfiles:
            fl = stf.allfiles[filename]
            self.output("%s\t%s\t %d\t %s " % (time.ctime(xboxtime.fat2unixtime(fl.utime, fl.udate)),\
                                        time.ctime(xboxtime.fat2unixtime(fl.atime, fl.adate)),\
                                        fl.size, filename))
                                    
    def print_xdbf(self, gpd):
        """ Prints out all the information contained in the provided XDBF object
            TODO: Write images to disk if requested
        """
        self.output("\n*********************")
        self.output(gpd)
        self.output("*********************")
        self.output("Version: %d" % gpd.version)
        self.output("Entries: %d" % gpd.entry_count)
        self.output("Images: %d" % len(gpd.images))
        self.output("Titles: %d" % len(gpd.titles))
        self.output("Strings: %d" % len(gpd.strings))
        self.output("Achievements: %d" % len(gpd.achievements))

        self.output("\nSETTINGS")
        for idnum in gpd.settings:
            sett = gpd.settings[idnum]
            self.output("0x%x %s" % (idnum, str(sett)))

        self.output("\nIMAGES")
        for idnum in gpd.images:
            self.output("Image id 0x%x size: %d" % (idnum, len(gpd.images[idnum])))

        self.output("\nTITLES")
        for idnum in gpd.titles:
            title = gpd.titles[idnum]
            try:
                self.output("0x%x: %s" % (idnum, str(title)))
            except UnicodeEncodeError:
                self.output("0x%s: GPD Title %s %s" % (idnum, title.name.replace('\x00', ''), hex(title.title_id)))
            self.output("Achievements unlocked %d / %d" % (title.achievement_unlocked, title.achievement_count))
            self.output("Gamerscore %d / %d" % (title.gamerscore_unlocked, title.gamerscore_total))
            self.output("Last Played: %s\n" % (time.ctime(xboxtime.filetime2unixtime(title.last_played))))

        self.output("\nSTRINGS")
        for idnum in gpd.strings:
            self.output("String id 0x%x" % idnum)
            try:
                self.output("String: %s" % (unicode(gpd.strings[idnum], 'utf-16-be', "ignore")))
            except UnicodeEncodeError:
                self.output("String: %s" % (gpd.strings[idnum].replace('\x00', '')))

        self.output("\nACHIEVEMENTS")
        for idnum in gpd.achievements:
            ach = gpd.achievements[idnum]
            if ach.achievement_id == None or ach.name == None or ach.image_id == None:
                continue
            try:
                self.output("0x%x: %s" % (idnum, str(ach)))
            except UnicodeEncodeError:
                self.output("0x%x: %s %s %s" % (idnum, "GPD Achievement", hex(ach.achievement_id), ach.name.replace('\x00', '')))
            try:
                self.output("Locked Description: %s" % (ach.get_locked_desc()))
                self.output("Unlocked Description: %s" % (ach.get_unlocked_desc()))
            except UnicodeEncodeError:
                self.output("Locked Description: %s" % (ach.locked_desc.replace('\x00', '')))
                self.output("Unlocked Description: %s" % (ach.unlocked_desc.replace('\x00', '')))
                #self.output("Locked Description: %s" % "".join([x for x in ach.get_locked_desc() if x >= 0x20 and x < 0x7F])
                #self.output("Unlocked Description: %s" % "".join([x for x in ach.get_unlocked_desc() if x >= 0x20 and x < 0x7F])

            self.output("Image ID: 0x%x" % ach.image_id)
            self.output("Gamerscore: %d" % ach.gamer_score)
            if ach.unlock_time == 0:
                self.output("Not Unlocked")
            else:
                self.output("Unlocked time: %s" % (time.ctime(xboxtime.filetime2unixtime(ach.unlock_time))))
            self.output(" ")


    def document_image(self):
        """
            Processes an XTAF image including STFS files and embedded GPD and Account files
        """

        if self.filename == None:
            return

        self.output("Opening %s" % self.filename, self.errfd)
        x = partition.Partition(self.filename)
        self.print_xtaf(x)

        # Find STFS files
        self.output("Processing all files", self.errfd)
        for filename in x.allfiles:
            try:
                if xboxmagic.find_type(data = x.read_file(filename, size=0x10)) == "STFS":
                    self.output("Processing STFS file %s" % filename, self.errfd)
                    s = stfs.STFS(filename, fd=x.open_fd(filename))
                    self.print_stfs(s)
                    
                    # Check to see if this is a gamertag STFS  
                    for stfsfile in s.allfiles:
                        try:
                            if stfsfile.endswith("Account"):
                                magic = xboxmagic.find_type(data = s.read_file(s.allfiles[stfsfile], size=404))
                            elif stfsfile.upper().endswith(("PNG", "GPD")): 
                                magic = xboxmagic.find_type(data = s.read_file(s.allfiles[stfsfile], size=0x10))
                            else:
                                magic = 'Unknown'

                            # Process GPD files
                            if magic == 'XDBF':
                                self.output("Processing GPD File %s" % stfsfile, self.errfd)
                                # Maybe STFS needs an equivalent to Partition.open_fd(filename)
                                g = xdbf.XDBF(stfsfile, fd=StringIO(s.read_file(s.allfiles[stfsfile])))
                                self.print_xdbf(g)
                                if self.image_directory != None: # Extract all the images
                                    for gpdimage in g.images:
                                        with open("%s/%s-%x-%s" %\
                                                (self.image_directory, os.path.basename(filename), gpdimage,\
                                                stfsfile[1:].replace('/', '-')), 'w') as fd:
                                            fd.write(g.images[gpdimage])
                                        
                            # Decrypt and print Account blob                       
                            if magic == 'Account':
                                self.output("Processing Account Blob", self.errfd)
                                a = account.Account(s.read_file(s.allfiles[stfsfile]))
                                self.print_account(a)
                            
                            # Extract all the images
                            if magic == 'PNG' and self.image_directory != None:
                                self.output("Processing Image File %s" % stfsfile, self.errfd)  
                                with open("%s/%s-%s.png" %\
                                        (self.image_directory, os.path.basename(filename), stfsfile[1:].replace('/', '-')),\
                                        'w') as fd:
                                    fd.write(s.read_file(s.allfiles[stfsfile]))
                        except (IOError, OverflowError, AssertionError) as e: # GPD / Account error
                            self.output("GPD/Account Error: %s %s %s" % (stfsfile, type(e), e), self.errfd)
                            continue

            except (IOError, OverflowError, AssertionError) as e: # STFS Error
                self.output("STFS Error: %s %s %s" % (filename, type(e), e), self.errfd)
                continue
                        
            
if __name__ == '__main__':
    if len(sys.argv) < 2:
        print "Usage: report360.py XFATIMAGE.bin [path to write images to]"
        sys.exit(1)

    if len(sys.argv) == 2:
        reporter = Report360(sys.argv[1])
    else:
        reporter = Report360(sys.argv[1], sys.argv[2])

    reporter.document_image()
