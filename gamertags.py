# An example of using py360 to extract all the GamerTags present on an image.

# Where does this data live?
# GamerTags are inside the Account block of a user's STFS container located on
# the XTAF partition. 

# How do you find user STFS containers?
# Gamer profiles are located in the /Content directory in subdirectories named
# with 16 hex characters starting with an 'E' such as E00012DD5A4FAEE5 
# The STFS container is located in the FFFE07D1/00010000 subdirectory and is named the
# same as the profile directory.
# For example /Content/E00012DD5A4FAEE5/FFFE07D1/00010000/E00012DD5A4FAEE5 

from py360 import partition, stfs, account
import sys

# First, open the xbox 360 image
part = partition.Partition(sys.argv[1])

# Second, find profile STFS containers
content = part.get_file('/Content')
if content == None:
    print "Error getting content directory"
    sys.exit(1) # Error condition

for directory in content.files:
    if len(directory) == 16 and directory[0] == 'E':
        try:
            # Open each STFS container and look for the Account block
            
            # The STFS class can take either an actual file or a file-like object,
            # we're using an file-like object to avoid having to use a temp file.
            path = '/Content/%s/FFFE07D1/00010000/%s' % (directory, directory)

            # This test is to exclude deleted profiles and defunct directories
            if None != part.get_file(path):
                profile = stfs.STFS(filename = None, fd = part.open_fd(path))

                # The account block is always at /Account in the STFS archive
                # we'll read it in, decode it and then print out the gamertag
                acc = account.Account(profile.read_file(profile.allfiles['/Account']))
                print "Gamertag: %s, Type: %s" % (acc.get_gamertag(), acc.live_type)
        except (AssertionError, IOError):
            print "Error reading: %s" % directory # If something breaks we just skip it
