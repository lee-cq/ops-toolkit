#! /usr/bin/env python

import re
import xml.etree.ElementTree as ET
import zipfile
import os
from pathlib import Path


class Docx2Text(object):
    nsmap = {'w': 'http://schemas.openxmlformats.org/wordprocessingml/2006/main'}

    def qn(self, tag):
        """
        Stands for 'qualified name', a utility function to turn a namespace
        prefixed tag name into a Clark-notation qualified tag name for lxml. For
        example, ``qn('p:cSld')`` returns ``'{https://schemas.../main}cSld'``.
        Source: https://github.com/python-openxml/python-docx/
        """
        prefix, tagroot = tag.split(':')
        uri = self.nsmap[prefix]
        return '{{{}}}{}'.format(uri, tagroot)


    def xml2text(self, xml):
        """
        A string representing the textual content of this run, with content
        child elements like ``<w:tab/>`` translated to their Python
        equivalent.
        Adapted from: https://github.com/python-openxml/python-docx/
        """
        text = u''
        root = ET.fromstring(xml)
        for child in root.iter():
            if child.tag == self.qn('w:t'):
                t_text = child.text
                text += t_text if t_text is not None else ''
            elif child.tag == self.qn('w:tab'):
                text += '\t'
            elif child.tag in (self.qn('w:br'), self.qn('w:cr')):
                text += '\n'
            elif child.tag == self.qn("w:p"):
                text += '\n\n'
        return text


    def process(self, docx, img_dir=None):
        text = u''

        # unzip the docx in memory
        zipf = zipfile.ZipFile(docx)
        filelist = zipf.namelist()

        # get header text
        # there can be 3 header files in the zip
        header_xmls = 'word/header[0-9]*.xml'
        for f_name in filelist:
            if re.match(header_xmls, f_name):
                text += self.xml2text(zipf.read(f_name))

        # get main text
        doc_xml = 'word/document.xml'
        text += self.xml2text(zipf.read(doc_xml))

        # get footer text
        # there can be 3 footer files in the zip
        footer_xmls = 'word/footer[0-9]*.xml'
        for f_name in filelist:
            if re.match(footer_xmls, f_name):
                text += self.xml2text(zipf.read(f_name))

        if img_dir is not None:
            # extract images
            for f_name in filelist:
                _, extension = os.path.splitext(f_name)
                if extension in [".jpg", ".jpeg", ".png", ".bmp"]:
                    Path(img_dir).joinpath(
                        zipfile.Path(f_name).name
                    ).write_bytes(zipf.read(f_name))
                    # dst_f_name = os.path.join(img_dir, os.path.basename(f_name))
                    # with open(dst_f_name, "wb") as dst_f:
                    #     dst_f.write(zipf.read(f_name))

        zipf.close()
        return text.strip()

