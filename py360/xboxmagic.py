"""
    Functions for determining the file type of buf / file objects passed in.
    Only handles Xbox 360 related file formats and PNG
    Returns a string denoting file type
"""

from py360 import *
PNG_HEADER = "\x89PNG\x0D\x0A\x1A\x0A"
XTAF_HEADER = "XTAF"
XDBF_HEADER = "XDBF"
STFS_HEADERS = ("CON ", "PIRS", "LIVE")
ACCOUNT_SIZE = 404

def is_png(data):
    if data[:len(PNG_HEADER)] == PNG_HEADER:
        return True
    return False

def is_xtaf(data):
    if data[:len(XTAF_HEADER)] == XTAF_HEADER:
        return True
    return False

def is_xdbf(data):
    if data[:len(XDBF_HEADER)] == XDBF_HEADER:
        return True
    return False

def is_stfs(data):
    for header in STFS_HEADERS:
        if data[:len(header)] == header:
            return True
    return False

def is_account(length):
    if length == ACCOUNT_SIZE:
        return True # This is very tentative
    return False

def find_type(data = None, fd = None):
    if (data == None and fd == None) or (data != None and fd != None):
        return "Error"

    if data == None and fd != None:
        data = fd.read(max(len(STFS_HEADERS[0]), len(XDBF_HEADER), len(PNG_HEADER), len(XTAF_HEADER)))
        fd.seek(0, 2)
        length = fd.tell()
        fd.seek(0)
    elif data != None:
        length = len(data)

    if is_png(data):
        return "PNG"
    if is_xdbf(data):
        return "XDBF"
    if is_stfs(data):
        return "STFS"
    if is_account(length):
        return "Account"
    if is_xtaf(data):
        return "XTAF"
    if fd != None and length > 0x130EB0000l:
        fd.seek(0x130EB0000)
        data = fd.read(len(XTAF_HEADER))
        if is_xtaf(data):
            return "XTAF"
    return "Unknown"

