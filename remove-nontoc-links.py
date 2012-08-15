#!/usr/bin/env python2

import re
import sys

PLACEHOLDER = '#### SoMeThInG uNuSuAl ####'

if __name__ == '__main__':
    if len(sys.argv) < 2:
        print '\nUsage:', argv[0], 'file.html\n'
        sys.exit(1)

    htmlFile = sys.argv[1]
    inp = open(htmlFile, 'r')
    html = inp.read()
    inp.close()

    matches = re.findall('<table id="toc" class="toc">.*?</table>', html, re.DOTALL)
    if len(matches) > 0:
        toc = matches[0]
        html = html.replace(toc, PLACEHOLDER)
        html = html.replace('<a ', '<span ')
        html = html.replace('</a>', '</span>')
        html = html.replace(PLACEHOLDER, toc)

        out = open(htmlFile, 'w')
        out.write(html)
        out.close()
    else:
        print 'Could not detect TOC'
