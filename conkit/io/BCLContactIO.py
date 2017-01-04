"""
Parser module specific to BCL::Contact predictions
"""

__author__ = "Felix Simkovic"
__date__ = "12 Dec 2016"
__version__ = "0.1"

from conkit.core import Contact
from conkit.core import ContactMap
from conkit.core import ContactFile
from conkit.io._ParserIO import _ContactFileParser

import re

RE_SPLIT = re.compile(r'\s+')


class BCLContactParser(_ContactFileParser):
    """Class to parse a BCL::Contact contact file
    """
    def __init__(self):
        super(BCLContactParser, self).__init__()

    def read(self, f_handle, f_id="bclcontact"):
        """Read a contact file

        Parameters
        ----------
        f_handle
           Open file handle [read permissions]
        f_id : str, optional
           Unique contact file identifier

        Returns
        -------
        :obj:`conkit.core.ContactFile`

        """

        hierarchy = ContactFile(f_id)
        contact_map = ContactMap("map_1")
        hierarchy.add(contact_map)

        for line in f_handle:
            line = line.rstrip()

            if not line:
                continue

            else:
                res1_seq, res1, res2_seq, res2, _, _, _, _, _, raw_score = RE_SPLIT.split(line)

                contact = Contact(
                    int(res1_seq),
                    int(res2_seq),
                    float(raw_score)
                )
                contact.res1 = res1
                contact.res2 = res2
                contact_map.add(contact)

        hierarchy.method = 'Contact map predicted using BCL::Contact'

        return hierarchy

    def write(self, f_handle, hierarchy):
        """Write a contact file instance to to file

        Parameters
        ----------
        f_handle
           Open file handle [write permissions]
        hierarchy : :obj:`conkit.core.ContactFile`, :obj:`conkit.core.ContactMap` or :obj:`conkit.core.Contact`

        Raises
        ------
        RuntimeError
           Not available

        """
        raise RuntimeError("Not available")