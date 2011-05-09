"""
Functions to output information about py360 types
document_image processes an entire disk image
"""

import time, os, sys
from py360 import xdbf, partition, account, stfs, xboxmagic, xboxtime
from cStringIO import StringIO

def print_account(acc):
    """ Prints out information from an Account block """
    
    print "\n*********************"
    print acc
    print "*********************"
    print "XUID: %s" % acc.xuid
    if acc.live_account:
        print "Account Type: %s" % acc.live_type
    else:
        print "Account Type: Local"
    print "Console Type: %s" % acc.console_type
    if acc.passcode:
        print "Passcode: %s" % acc.passcode
    

def print_xtaf(part):
    """ Prints out information about an XTAF partition """
    print "\n*********************"
    print part
    print "*********************"
    print "\nFILE LISTING"
    for filename in part.allfiles:
        fi = part.allfiles[filename]
        if fi.fr:
            print "File: %s\t%d" % (filename, fi.fr.fsize)
            print "%s\t%s\t%s\n" % (time.ctime(xboxtime.fat2unixtime(fi.fr.mtime, fi.fr.mdate)),\
                                        time.ctime(xboxtime.fat2unixtime(fi.fr.atime, fi.fr.adate)),\
                                        time.ctime(xboxtime.fat2unixtime(fi.fr.ctime, fi.fr.cdate)))
                                        
def print_stfs(stf):
    """ Prints out information contained in the provided STFS object """
    print "\n*********************"
    print stf
    print "*********************"
    #TODO: Include some of the header data
    print "Name: ", stf.display_name
    print "Description: ", stf.display_description
    print "\nFILE LISTING"
    for filename in stf.allfiles:
        fl = stf.allfiles[filename]
        print "%s\t%s\t %d\t %s " % (time.ctime(xboxtime.fat2unixtime(fl.utime, fl.udate)),\
                                    time.ctime(xboxtime.fat2unixtime(fl.atime, fl.adate)),\
                                    fl.size, filename)
                                

def print_xdbf(gpd):
    """ Prints out all the information contained in the provided XDBF object
        TODO: Write images to disk if requested
    """
    print "\n*********************"
    print gpd
    print "*********************"
    print "Version: %d" % gpd.version
    print "Entries: %d" % gpd.entry_count
    print "Images: %d" % len(gpd.images)
    print "Titles: %d" % len(gpd.titles)
    print "Strings: %d" % len(gpd.strings)
    print "Achievements: %d" % len(gpd.achievements)

    print "\nSETTINGS"
    for idnum in gpd.settings:
        sett = gpd.settings[idnum]
        print "0x%x %s" % (idnum, str(sett))

    print "\nIMAGES"
    for idnum in gpd.images:
        print "Image id 0x%x size: %d" % (idnum, len(gpd.images[idnum]))

    print "\nTITLES"
    for idnum in gpd.titles:
        title = gpd.titles[idnum]
        try:
            print "0x%x: %s" % (idnum, str(title))
        except UnicodeEncodeError:
            print "0x%s: GPD Title %s %s" % (idnum, title.name.replace('\x00', ''), hex(title.title_id))
        print "Achievements unlocked %d / %d" % (title.achievement_unlocked, title.achievement_count)
        print "Gamerscore %d / %d" % (title.gamerscore_unlocked, title.gamerscore_total)
        print "Last Played: %s\n" % (time.ctime(xboxtime.filetime2unixtime(title.last_played)))

    print "\nSTRINGS"
    for idnum in gpd.strings:
        print "String id 0x%x" % idnum
        try:
            print "String: %s" % (unicode(gpd.strings[idnum], 'utf-16-be', "ignore"))
        except UnicodeEncodeError:
            print "String: %s" % (gpd.strings[idnum].replace('\x00', ''))

    print "\nACHIEVEMENTS"
    for idnum in gpd.achievements:
        ach = gpd.achievements[idnum]
        if ach.achievement_id == None or ach.name == None or ach.image_id == None:
            continue
        try:
            print "0x%x: %s" % (idnum, str(ach))
        except UnicodeEncodeError:
            print "0x%x: %s %s %s" % (idnum, "GPD Achievement", hex(ach.achievement_id), ach.name.replace('\x00', ''))
        try:
            print "Locked Description: %s" % (ach.get_locked_desc())
            print "Unlocked Description: %s" % (ach.get_unlocked_desc())
        except UnicodeEncodeError:
            print "Locked Description: %s" % (ach.locked_desc.replace('\x00', ''))
            print "Unlocked Description: %s" % (ach.unlocked_desc.replace('\x00', ''))
            #print "Locked Description: %s" % "".join([x for x in ach.get_locked_desc() if x >= 0x20 and x < 0x7F])
            #print "Unlocked Description: %s" % "".join([x for x in ach.get_unlocked_desc() if x >= 0x20 and x < 0x7F])

        print "Image ID: 0x%x" % ach.image_id
        print "Gamerscore: %d" % ach.gamer_score
        if ach.unlock_time == 0:
            print "Not Unlocked"
        else:
            print "Unlocked time: %s" % (time.ctime(xboxtime.filetime2unixtime(ach.unlock_time)))
        print " "

def document_image(filename, image_directory = None):
    """
        Processes an XTAF image including STFS files and embedded GPD and Account files
    """

    print >> sys.stderr, "Opening %s" % filename
    x = partition.Partition(filename)
    print_xtaf(x)

    # Find STFS files
    print >> sys.stderr, "Processing all files"
    for filename in x.allfiles:
        try:
            if xboxmagic.find_type(data = x.read_file(filename, size=0x10)) == "STFS":
                print >> sys.stderr, "Processing STFS file %s" % filename
                s = stfs.STFS(filename, fd=x.open_fd(filename))
                print_stfs(s)
                
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
                            print >> sys.stderr, "Processing GPD File %s" % stfsfile  
                            # Maybe STFS needs an equivalent to Partition.open_fd(filename)
                            g = xdbf.XDBF(stfsfile, fd=StringIO(s.read_file(s.allfiles[stfsfile])))
                            print_xdbf(g)
                            if image_directory != None: # Extract all the images
                                for gpdimage in g.images:
                                    with open("%s/%s-%x-%s" %\
                                            (image_directory, os.path.basename(filename), gpdimage,\
                                             stfsfile[1:].replace('/', '-')), 'w') as fd:
                                        fd.write(g.images[gpdimage])
                                    
                        # Decrypt and print Account blob                       
                        if magic == 'Account':
                            print >> sys.stderr, "Processing Account Blob"
                            a = account.Account(s.read_file(s.allfiles[stfsfile]))
                            print_account(a)
                        
                        # Extract all the images
                        if magic == 'PNG' and image_directory != None:
                            print >> sys.stderr, "Processing Image File %s" % stfsfile  
                            with open("%s/%s-%s.png" %\
                                     (image_directory, os.path.basename(filename), stfsfile[1:].replace('/', '-')),\
                                     'w') as fd:
                                fd.write(s.read_file(s.allfiles[stfsfile]))
                    except (IOError, OverflowError, AssertionError) as e: # GPD / Account error
                        print >> sys.stderr, "GPD/Account Error: %s %s %s" % (stfsfile, type(e), e)
                        continue

        except (IOError, OverflowError, AssertionError) as e: # STFS Error
            print >> sys.stderr, "STFS Error: %s %s %s" % (filename, type(e), e)
            continue
                    
        
if __name__ == '__main__':
    if len(sys.argv) < 2:
        print "Usage: report360.py XFATIMAGE.bin [path to write images to]"
        sys.exit(1)

    if len(sys.argv) == 2:
        document_image(sys.argv[1])
    else:
        document_image(sys.argv[1], sys.argv[2])
    
