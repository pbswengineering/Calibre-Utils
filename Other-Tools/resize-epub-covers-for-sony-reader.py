#!/usr/bin/env python

# This simple script attempts to resize every EPUB file cover inside a
# Sony Reader device to make it fit the screen without the need for resizing
# (the default Sony Reader resizing looks ugly)
#
# KNOWN ISSUES:
# 
# - It ignores EPUBS that don't contain a content.opf file
# - The resize on periodics doesn't bring great results: since they have a 
#   top and bottom bars that take away some pixels, their cover size should be
#   slightly shorter, but the script isn't aware of this.
#
# By Paolo Bernardi <villa.lobos@tiscali.it>
# This script is licensed under the Apache 2 License terms.


# The following parameters fits my Sony PRS-650...
COVER_WIDTH = 590
COVER_HEIGHT = 754

import os
import re
import shutil
import subprocess
import sys
import tempfile
from xml.dom import minidom
import zipfile


def run(cmd, show_output=True):
    '''Runs The command cmd and returns its exit status. Depending on the
    show_output parameters it shows the standard output or not.'''

    if show_output:
        p = subprocess.Popen(cmd, shell=True)
    else:
        p = subprocess.Popen(cmd, shell=True, stdout=subprocess.PIPE)
    sts = os.waitpid(p.pid, 0)[1]
    return sts


def popen(cmd):
    '''Returns the standard output text caused by cmd's execution'''

    pipe = subprocess.Popen(cmd, shell=True, stdout=subprocess.PIPE).stdout
    return pipe.read().strip()


def command_in_path(cmd):
    '''Returns True if cmd is available in the system PATH, False otherwise.'''

    return run('which ' + cmd, show_output=False) == 0


def mount():
    '''Returns the mounted devices with their associated directories.
    The result is a list if tuples in the form of (device, directory)'''

    result = []
    # Each line is something like 'proc on /proc type proc (rw)'
    for line in popen('mount').split('\n'):
        try:
            v = line.split(' on ')
            device = v[0]
            directory = v[1].split(' ')[0]
            result.append((device, directory))
        except:
            pass

    return result


def find_file(base_path, matching_function):
    '''Return a list of files inside base_path that match the matching function 
    (including its subdirectories). matching_function can be a lamda 
    expression.'''

    result = []
    for f in [ os.path.join(base_path, x) for x in os.listdir(base_path) ]:
        if matching_function(f):
            result.append(f)
        if os.path.isdir(f):
            result.extend(find_file(f, matching_function))
    return result


def find_sony_reader():
    '''Tries to find if a Sony ebook reader is currently mounted on the system.
    If there's one, it returns its mount directory, otherwise returns False.'''

    mount_dirs = [ x[1] for x in mount() ]
    for d in mount_dirs:
        target_dir = os.path.join(d, 'database', 'media', 'books')
        if os.path.exists(target_dir):
            return d
    return False


def resize_image(img_file, width, height, keep_proportions=False):
    '''Resizes img_file to the specified new size. By default it doesn't
    respect the previous img_file size proportion; this can be changed with the
    keep_proportions parameter.'''

    force = keep_proportions and '' or '!'
    cmd = 'mogrify -resize %sx%s%s \'%s\'' % (width, height, force, img_file)
    run(cmd)


def is_image_file(file_name):
    '''Returns True if file_name is an image file name, False otherwise.'''

    f = file_name.lower()
    return f.endswith('.jpg') or \
            f.endswith('.jpeg') or \
            f.endswith('.png') or \
            f.endswith('.gif')


def find_epub_cover_file(content_opf):
    '''Returns the EPUB cover file name; it looks for it inside the content.opf
    file. If no cover is found returns None.'''

    # The process goes like this:
    # 1. See if there's any "meta" tag with "cover" as name
    # 2. If there's one, look at its "content" attribute
    # 3. Look if there's any "item" tag with the id= to the "content" attribute
    # 4. If so, return the "item" "href" attribute
    # 5. If there's no "meta" cover, try to find an "item" with "id" = cover
    # 6. If there's one, return its "href"

    xml = minidom.parse(content_opf)
    cover_elements = [ x for x in xml.getElementsByTagName('meta') \
                        if x.getAttribute('name') == 'cover' ]

    # Is there any "meta-cover"?
    if len(cover_elements) > 0: 
        cover_element = cover_elements[0]
        content = cover_element.getAttribute('content')

        item_elements = xml.getElementsByTagName('item')
        item_cover_elements = [ e for e in item_elements \
                                   if e.getAttribute('id') == content ]
        if len(item_cover_elements) > 0:
            return item_cover_elements[0].getAttribute('href')

        elif is_image_file(content): 
            return content

    # No "meta-cover"? Let's try for an "item-cover"
    else:
        item_elements = xml.getElementsByTagName('item') 
        item_cover_elements = [ e for e in item_elements \
                                   if e.getAttribute('id') == 'cover' ]
        if len(item_cover_elements) > 0:
            return item_cover_elements[0].getAttribute('href')


if __name__ == '__main__':
    # Do I have ImageMagick?
    if not command_in_path('mogrify'):
        print 'Couldn\'t find the mogrify command.'
        print 'You need to install the ImageMagick package.'
        sys.exit(1)

    # Do I have zip?
    if not command_in_path('zip'):
        print 'Couldn\'t find the zip command.'
        print 'You need to install the zip package.'
        sys.exit(1)

    # Is there a mounted Sony Reader?
    sony_dir = find_sony_reader()
    if not sony_dir:
        print 'Couldn\'t find a Sony Reader device mounted on the system.'
        sys.exit(1)

    # Let's find the EPUB files!
    epub_test = lambda x: os.path.isfile(x) and x.endswith('.epub')
    epubs = find_file(sony_dir, epub_test)

    # The stage is set...
    tmp_dir = tempfile.mkdtemp()
    print 'Working inside', tmp_dir, '\n'

    # And now, let's resize!
    print 'Processing', len(epubs), 'EPUB files\n'

    for epub_file in epubs:
        epub_name = os.path.basename(epub_file)
        print 'Processing', epub_name
        zip_name = epub_name[:-4] + 'zip' # Changes extension from epub to zip
        zip_file = os.path.join(tmp_dir, zip_name)

        # Moves the file to the temporary directory changing its extension to zip.
        shutil.copyfile(epub_file, zip_file)

        # Unzips the EPUB
        zip_tmp_dir = os.path.join(tmp_dir, 'pippo')
        os.mkdir(zip_tmp_dir)
        with zipfile.ZipFile(zip_file) as myzip:
            myzip.extractall(zip_tmp_dir)
        os.unlink(zip_file)

        # Is there a cover image?
        cover_file = None
        content_opf_test = lambda x: os.path.basename(x) == 'content.opf'
        content_opfs = find_file(zip_tmp_dir, content_opf_test)
        if len(content_opfs) > 0:
            content_opf_file = os.path.join(zip_tmp_dir, content_opfs[0])
            cover_file = find_epub_cover_file(content_opf_file)

        # Resizes the cover, if any
        if cover_file and os.path.isfile(cover_file):
            print "Cover found!"
            resize_image(cover_file, COVER_WIDTH, COVER_HEIGHT)
            # Rebuilds the zip file with the new cover
            rezip_cmd = 'cd \'%s\' && zip -r \'%s\' *' % (zip_tmp_dir, zip_file)
            run(rezip_cmd, show_output=False)
            # Puts the EPUB back in place
            shutil.move(zip_file, epub_file)

        # Removes the temporary directory anyway
        shutil.rmtree(zip_tmp_dir)
    
    # Final clean-up
    os.rmdir(tmp_dir)

    print '\nThat\'s all, folks!\n'
