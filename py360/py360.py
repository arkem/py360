# py360.py is the FUSE interface for XTAF Filesystems.
# To mount a filesystem run this file or the mount.py360 shell script
# To programmatically interact with XTAF Filesystems check the partition module.
#
# FIXME: When running stfs.py against a mounted xtaf fs some blocks appear to be emtpy.
#        This can be worked around by reading other blocks first (which is a bit weird)



from fuse import Fuse
from partition import Partition
import time, fuse
import xboxtime
import sys, stat, errno

fuse.fuse_python_api = (0, 2)

if not hasattr(fuse, '__version__'):
    raise RuntimeError, \
        "your fuse-py doesn't know of fuse.__version__, probably it's too old."

# Stat class for file information
class MyStat(fuse.Stat):
    def __init__(self):
        self.st_mode = 0
        self.st_ino = 0
        self.st_dev = 0
        self.st_nlink = 0
        self.st_uid = 0
        self.st_gid = 0
        self.st_size = 0
        self.st_atime = 0
        self.st_mtime = 0
        self.st_ctime = 0

# Main FUSE class
class Py360(Fuse):
    def __init__(self, *args, **kw):
        filename = kw.pop('filename')
        Fuse.__init__(self, *args, **kw)
        self.partition = Partition(filename, threadsafe = False)


    def getattr(self, path):
        st = MyStat()
        fileobj = self.partition.get_file(path)
        if fileobj:
            if fileobj.isDirectory():
                st.st_mode = stat.S_IFDIR | 0555
                st.st_nlink = len(fileobj.files)
            else:
                st.st_mode = stat.S_IFREG | 0444
            if not fileobj.isDirectory() or not fileobj.root:
                st.st_size = fileobj.fr.fsize
                st.st_ino = fileobj.fr.cluster
                st.st_atime = xboxtime.fat2unixtime(fileobj.fr.atime, fileobj.fr.adate)
                st.st_mtime = xboxtime.fat2unixtime(fileobj.fr.mtime, fileobj.fr.mdate)
                st.st_ctime = xboxtime.fat2unixtime(fileobj.fr.ctime, fileobj.fr.cdate)
            context = self.GetContext()
            st.st_uid = context['uid']
            st.st_gid = context['gid']

            return st
        else:
            return -errno.ENOENT

    def readdir(self, path, offset): #Why does this have an offset?
        fileobj = self.partition.get_file(path)
        if fileobj and fileobj.isDirectory():
            dirlist = [fuse.Direntry('.'), fuse.Direntry('..')]
            for f in fileobj.files:
                dirlist.append(fuse.Direntry(f)) 
            return dirlist
        else:
            return -errno.ENOENT

    def read(self, path, size, offset):
        fileobj = self.partition.get_file(path)
        if fileobj:
            return self.partition.read_file(fileobj = fileobj, size = size, offset = offset)
        else:
            return -errno.ENOENT

def main():
    usage="""
Python FUSE file system for Xbox 360 hard drives (XFAT)

%prog [imagefile] [mountpoint] [options]
""" 
    server = Py360(filename = sys.argv.pop(1), version="%prog " + fuse.__version__,
                     usage=usage,
                     dash_s_do='setsingle')

    # While Partition is (now) thread safe, testing showed that single threaded
    # mode was 6 times faster. This is because only one cluster could be read
    # at a time regardless of number of threads. With a file object pool or a
    # file cache this might swing the other way.
    # If implementing this remember Fuse loves to read in 128kb chunks.
    # 
    # Partition is only optionally threadsafe
    server.multithreaded = False 
    server.parse(errex=1)
    server.main()

if __name__ == '__main__':
    if len(sys.argv) < 3:
        print "Usage: py360.py [imagefile] [mountpoint] [options]"
        sys.exit(1)
    main()

