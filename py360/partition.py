#!/usr/bin/python

""" 
    This module has the classes associated with parsing XTAF parititions
    To use this class try something like:
    from partition import *
    xtafpart = Partition('/mnt/data/201010.bin') 
"""

import sys
import mmap
import struct
from threading import Lock
from cStringIO import StringIO

# TODO: Optional thread safety
class XTAFFD(object):
    """ A File-like object for representing FileObjs """
    def __init__(self, partition, fileobj):
        self.pointer = 0
        self.fileobj = fileobj
        self.partition = partition

    def read(self, length=-1):
        buf = self.partition.read_file(fileobj = self.fileobj, size=length, offset=self.pointer)
        self.pointer += len(buf)
        return buf

    def seek(self, offset, whence=0):
        if whence == 0:
            self.pointer = offset
        if whence == 1:
            self.pointer = self.pointer + offset
        if whence == 2:
            self.pointer = self.fileobj.fr.fsize - offset

        if self.pointer > self.fileobj.fr.fsize:
            self.pointer = self.fileobj.fr.fsize
        if self.pointer < 0:
            self.pointer = 0

    def tell(self):
        return self.pointer

class FileRecord(object):
    """FileRecord is straight off of the disk (but with everything in host byte order)"""
    def __str__(self):
        return "XTAF FileRecord: %s" % self.filename

    def __init__(self, **kwargs):
        self.fnsize = kwargs["fnsize"]
        self.attribute = kwargs["attribute"]
        self.filename = kwargs["filename"]
        self.cluster = kwargs["cluster"]
        self.fsize = kwargs["fsize"]
        self.mtime = kwargs["mtime"]
        self.mdate = kwargs["mdate"]
        self.ctime = kwargs["ctime"]
        self.cdate = kwargs["cdate"]
        self.atime = kwargs["atime"]
        self.adate = kwargs["adate"]

    def isDirectory(self):
        if self.fsize == 0:
            return True
        return False

class FileObj(object):
    """ FileObj is a container with a FileRecord and a list of clusters """
    def __str__(self):
        return "XTAF File: %s" % self.fr

    def __init__(self, fr, clusters):
        self.fr = fr
        self.clusters = clusters

    def isDirectory(self):
        return False

class Directory(FileObj):
    """ Directory is a FileObj with a dict of FileObj """
    def __str__(self):
        return "%s (Directory)" % (super(Directory, self).__str__())

    def __init__(self, fr, clusters):
        super(Directory, self).__init__(fr, clusters)
        self.files = {}
        self.root = False

    def isDirectory(self):
        return True

class Partition(object):
    """
        Main class representing the partition
        The allfiles member has a dictionary of all the files in the partition
        The rootfile member contains a directory object that represents the root directory 
    """
    def __str__(self):
        return "XTAF Partition: %s" % self.filename

    def __init__(self, filename, threadsafe=False, precache=False):
        self.filename = filename
        self.threadsafe = threadsafe
        self.SIZE_OF_FAT_ENTRIES = 4

        #TODO: Error checking
        fd = open(filename, 'r') # The 'r' is very imporant
        if fd.read(4) != 'XTAF':
            start = 0x130EB0000L # TODO: Improve this detection mechanism
        else:
            start = 0
        fat = start + 0x1000L
        fd.seek(0, 2)
        end = fd.tell()
        rootdir = -(-((end - start) >> 12L) & -0x1000L) + fat #TODO: Understand this better
        size = end - rootdir
        fatsize = size >> 14L

        # This doesn't work because unlike the C version of mmap you can't give it a 64 bit offset
        #fatfd = mmap.mmap(fd.fileno(), fatsize, mmap.PROT_READ, mmap.PROT_READ, offset=fat)
        # So we have to keep the whole FAT in memory during processing
        fd.seek(fat, 0)
        fatdata = fd.read(fatsize * 4)
        fd.seek(0, 0)

        # Setup internal variables
        self.root_dir_cluster = 1
        self.start = start
        self.fat = fat
        self.root_dir = rootdir
        self.size = size
        self.fat_num = fatsize
        self.fd = fd
        self.fat_data = fatdata # <- FAT is in BIG ENDIAN
        self.allfiles = {}
        self.lock = Lock()
        #self.rootfile = self.parse_directory()
        self.rootfile = self.init_root_directory(recurse = precache)

    def read_cluster(self, cluster, length=0x4000, offset=0L):
        """ Given a cluster number returns that cluster """
        if length + offset <= 0x4000: #Sanity check
            diskoffset = (cluster - 1 << 14L) + self.root_dir + offset
            # Thread safety is optional because the extra function calls are a large burden
            if self.threadsafe:
                self.lock.acquire() 

            try:
                self.fd.seek(diskoffset)
                buf = self.fd.read(length)
            except IOError:
                buf = ""

            if self.threadsafe:
                self.lock.release()
            return buf
        else:
            return ""

    #TODO: Refactor into something smaller
    def read_file(self, filename=None, fileobj=None, size=-1, offset=0):
        """ Reads an entire file given a filename or fileobj """
        #TODO: Error checking
        if not fileobj: 
            fileobj = self.get_file(filename)

        if size == -1:
            if fileobj.isDirectory():
                size = 2**32 # Read the whole directory (all the clusters)
            else:
                size = fileobj.fr.fsize # Read the whole file (skip the slack space)

        if len(fileobj.clusters) == 0: # Initialise cluster list if necessary
            fileobj.clusters = self.get_clusters(fileobj.fr)
            if len(fileobj.clusters) == 0: # Check the return of get_clusters
                print "Reading Empty File"
                return ""

        clusters_to_skip = offset // 0x4000
        offset %= 0x4000
        buf = StringIO() 
        try:
            readlen = min(0x4000, size)
            buf.write(self.read_cluster(fileobj.clusters[clusters_to_skip], readlen, offset))
            size -= readlen
            for cl in fileobj.clusters[clusters_to_skip+1:]:
                if size <= 0:
                    break # If we're finished, stop reading clusters
                readlen = min(0x4000, size)
                buf.write(self.read_cluster(cl, readlen, 0))
                size -= readlen
            return buf.getvalue()
        except IndexError:
            print "Read overflow?", len(fileobj.clusters), clusters_to_skip
            return buf.getvalue()

    def get_clusters(self, fr):
        """ Builds a list of the clusters a file hash by parsing the FAT """
        if fr.cluster == 0:
            print "Empty file"
            return []
        clusters = [fr.cluster]
        cl = 0x0
        cl = fr.cluster
        cldata = ''
        while cl & 0xFFFFFFF != 0xFFFFFFF:
            cl_off = cl * self.SIZE_OF_FAT_ENTRIES 
            cldata = self.fat_data[cl_off:cl_off + self.SIZE_OF_FAT_ENTRIES]
            if len(cldata) == 4:
                cl = struct.unpack(">I", cldata)[0] 
                if cl & 0xFFFFFFF != 0xFFFFFFF:
                    clusters.append(cl)
            else:
                if fr.filename[0] != '~':
                    print "get_clusters fat offset warning %s %x vs %x, %x" %\
                          (fr.filename, cl_off, len(self.fat_data), len(cldata))
                cl = 0xFFFFFFF
        return clusters

    def open_fd(self, filename):
        f = self.get_file(filename)
        """ Return an XTAFFD object for a file """
        if f != None:
            return XTAFFD(self, f)
        else:
            return None

    def parse_file_records(self, data):
        """
            While not end of file records
            Create a file record object
            Return list of file records
            Date format: 
        """
        file_records = []
        pos = 0
        while pos + 64 < len(data): # FileRecord struct offsets
            fnlen = data[pos]
            flags = data[pos+1]
            if ord(fnlen) == 0xE5: # Handle deleted files
                name = '~' + data[pos+2:pos+2+42].strip("\xff\x00")
            elif ord(fnlen) > 42: # Technically >42 should be an error condition
                break
            elif ord(fnlen) == 0: # A vacant entry, maybe the end of the directory?
                pos += 64
                continue
            else: 
                name = data[pos+2:pos+2+42].strip("\xff\x00") # Ignoring fnlen is a bit wasteful
            cl = struct.unpack(">I", data[pos+0x2c:pos+0x2c+4])[0]
            size = struct.unpack(">I", data[pos+0x30:pos+0x30+4])[0]
            creation_date = struct.unpack(">H", data[pos+0x34:pos+0x34+2])[0]
            creation_time = struct.unpack(">H", data[pos+0x36:pos+0x36+2])[0]
            access_date = struct.unpack(">H", data[pos+0x38:pos+0x38+2])[0]
            access_time = struct.unpack(">H", data[pos+0x3A:pos+0x3A+2])[0]
            update_date = struct.unpack(">H", data[pos+0x3C:pos+0x3C+2])[0]
            update_time = struct.unpack(">H", data[pos+0x3E:pos+0x3E+2])[0]

            #if not (fnlen == '\xff' and flags == '\xff') and not fnlen == '\x00':
            if (ord(fnlen) < 43 and ord(fnlen) != 0) or (ord(fnlen) == 0xE5):
                file_records.append(FileRecord(fnsize=fnlen, attribute=flags, filename=name, cluster=cl,\
                                               fsize=size, mtime=update_time, mdate=update_date,\
                                               adate=access_date, atime=access_time,\
                                               cdate=creation_date, ctime=creation_time))
            else:
                pass

            pos += 64

        return file_records


    def walk(self, path = '/'):
        """ A generator that will return every fileobj on a system below path.
            This is designed to be used instead of iterating over self.allfiles. 
            self.allfiles can still be used if the partition is created with precache = True
            Using this will eliminate much of the advantage of precache = False.
            The only remaining speedup will be the lazy caching of file cluster lists
        """
        f = self.get_file(path)
        if f == None or not f.isDirectory():
            return
        files = [f]

        while len(files) > 0:
            f = files.pop(0)
            if f.isDirectory():
                if not f.root and len(f.clusters) == 0:
                    f = self.parse_directory(f) 
                files = files + f.files.values()
            yield f.fullpath

        return 

            


    def get_file(self, filename):
        """ Returns a fileobj from a filename. 
            Checks allfiles and if it isn't present starts walking the allfiles directory.
            Not the same as self.allfiles[filename] anymore. """
        if filename in self.allfiles: 
            currentfile = self.allfiles[filename]
            if currentfile.isDirectory() and not currentfile.root and len(currentfile.clusters) == 0:
                # If we're asked for a directory, initialise it before returning
                currentfile = self.parse_directory(currentfile) 
            return currentfile # A previously accessed file
        else:
            return self.walk_for_file(filename)

    def walk_for_file(self, filename):
        """ Walks the file system parsing directories where necessary looking for a fileobj """
        # Parse subdirectories looking for the requested file
        file_components = filename[1:].split("/") # Skip first slash
        currentfile = self.rootfile
        for component in file_components:
            #print "f:%s\t c:%s\t" % (filename, component),  currentfile, self.rootfile
            if currentfile == None:
                break
            # If this is a directory (that isn't root) and it has no clusters listed, try to initialise it
            if currentfile.isDirectory() and not currentfile.root and len(currentfile.clusters) == 0:
                currentfile = self.parse_directory(currentfile)
            try:
                currentfile = currentfile.files[component]
            except KeyError:
                currentfile = None

        if currentfile != None and currentfile.isDirectory():
            print "Initialising: %s" % filename
            currentfile = self.parse_directory(currentfile) # If we're asked for a directory, initialise it before returning

        return currentfile


    def init_root_directory(self, recurse = False):
        """ Creates the root directory object and calls parse_directory on it """
        directory = Directory(None, [self.root_dir_cluster])
        directory.root = True
        directory.fullpath = '/'
        self.allfiles[directory.fullpath] = directory
        directory = self.parse_directory(directory, recurse = recurse)
        return directory 

    #TODO: Refactor this to something smaller
    def parse_directory(self, directory = None, recurse = False):
        """ Parses a single directory, optionally it can recurse into subdirectories.
            It populates the allfile dict and parses the directories and file records of the directory """
        dirs_to_process = []
        if directory == None:
            return None
        else:
            dirs_to_process.append(directory)

        # For each directory to process (will be only one unless recurse is True)
        while len(dirs_to_process) > 0:
            d = dirs_to_process.pop(0)
            if d.root:
                directory_data = self.read_cluster(self.root_dir_cluster)
            else:
                directory_data = self.read_file(fileobj = d)

            # Parse the file records returned and optionally requeue subdirectories
            file_records = self.parse_file_records(directory_data)
            for fr in file_records:
                if fr.isDirectory():
                    d.files[fr.filename] = Directory(fr, [])
                    if recurse:
                        dirs_to_process.append(d.files[fr.filename])
                else:
                    d.files[fr.filename] = FileObj(fr, [])
                if d.root:
                    d.files[fr.filename].fullpath = d.fullpath + fr.filename
                else:
                    d.files[fr.filename].fullpath = d.fullpath + '/' + fr.filename
                self.allfiles[d.files[fr.filename].fullpath] = d.files[fr.filename]
        return directory

