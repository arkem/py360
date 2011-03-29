import sys

# This was used to grab png files from Profile STFS files before extractor360.py
# It still might be useful but you're probably after xdbf.py

PNG_HEADER = "\x89PNG\x0D\x0A\x1A\x0A"
PNG_FOOTER = "\x00\x00\x00\x00IEND\xAE\x42\x60\x82"

if len(sys.argv) < 3:
    print "Usage: [output_prefix] [file_to_carve] <file_to_carve2...>"
    print "Carves png files out of a parent file. This is useful if xdbf.py has failed."
    sys.exit(1)

for filename in sys.argv[2:]:
    data = open(filename).read()
    files_found = 0
    png_start = -1
    for c in range(0, len(data)):
        if png_start == -1:
            if data[c:c+len(PNG_HEADER)] == PNG_HEADER:
                png_start = c
                inside_png = True
        else:
            if data[c:c+len(PNG_FOOTER)] == PNG_FOOTER:
                fd = open("%s.%0.4d.png" % (sys.argv[1], files_found), 'w')
                fd.write(data[png_start:c+len(PNG_FOOTER)])
                fd.close()
                png_start = -1
                files_found += 1
