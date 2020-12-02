# Copyright (C) 2020 University of Glasgow
#
# Redistribution and use in source and binary forms, with or without
# modification, are permitted provided that the following conditions
# are met:
#
# 1. Redistributions of source code must retain the above copyright notice,
#    this list of conditions and the following disclaimer.
#
# 2. Redistributions in binary form must reproduce the above copyright
#    notice, this list of conditions and the following disclaimer in the
#    documentation and/or other materials provided with the distribution.
#
# THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS "AS IS"
# AND ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT LIMITED TO, THE
# IMPLIED WARRANTIES OF MERCHANTABILITY AND FITNESS FOR A PARTICULAR PURPOSE
# ARE DISCLAIMED. IN NO EVENT SHALL THE COPYRIGHT HOLDER OR CONTRIBUTORS BE
# LIABLE FOR ANY DIRECT, INDIRECT, INCIDENTAL, SPECIAL, EXEMPLARY, OR
# CONSEQUENTIAL DAMAGES (INCLUDING, BUT NOT LIMITED TO, PROCUREMENT OF
# SUBSTITUTE GOODS OR SERVICES; LOSS OF USE, DATA, OR PROFITS; OR BUSINESS
# INTERRUPTION) HOWEVER CAUSED AND ON ANY THEORY OF LIABILITY, WHETHER IN
# CONTRACT, STRICT LIABILITY, OR TORT (INCLUDING NEGLIGENCE OR OTHERWISE)
# ARISING IN ANY WAY OUT OF THE USE OF THIS SOFTWARE, EVEN IF ADVISED OF THE
# POSSIBILITY OF SUCH DAMAGE.

import os
import sys

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from pathlib              import Path
from ietfdata.datatracker import *
from ietfdata.rfcindex    import *

from itertools import islice, combinations 
import csv
from random import choice
from re import sub
# =============================================================================

dt = DataTracker(cache_dir=Path("cache"))
ri = RFCIndex()

def print_submission(draft):
    for submission_uri in draft.submissions:
        submission = dt.submission(submission_uri)
        if submission.replaces is not "":
            for replaces_draft in submission.replaces.split(","):
                replaces = dt.document_from_draft(replaces_draft)
                if (replaces is not None) and (replaces.name != draft.name):
                    print_submission(replaces)
        print("   dt.submission   | {} | {} | {} | {}".format(rfc.doc_id, submission.name, submission.rev, submission.document_date))


def print_dt_person(rfc, person):
    print("   dt.author       | {} | {:6d} | {}".format(rfc, person.id, person.name))


def print_dt_info(rfc, doc):
    print("   dt.date         | {} | {}".format(rfc, doc.time))
    for author in dt.document_authors(doc):
        person = dt.person(rfc, author.person)
        print_dt_person(person)
        print("   dt.author_info  | {} | {:6d} | {} | {}".format(rfc, person.id, author.country, author.affiliation))
    print("   dt.revision     | {} | {}".format(rfc, doc.rev))
    print_submission(doc)

####
# extend the Person class to make our life easier!
class IncompletePerson():

    def __init__(self, id=None, name=None):
        self.id     =  id if id is not None else 0
        self.name   =  name if name is not None else ''
        self.affiliation = "?"

    def __hash__(self): return hash(self.id)
    #    name_from_draft : str
    #    resource_uri    : Optional[PersonURI]
    #    ascii           : str
    #    ascii_short     : Optional[str]
    #    user            : str
    #    time            : datetime
    #    photo           : str
    #    photo_thumb     : str
    #    biography       : str
    #    consent         : bool    


#####
# util funcs

def get_names(author):
    rfc_initial = author[0]
    rfc_surname = author.split()[-1]
    matching = []
    for person in dt.people(name_contains=rfc_surname):
        if person.name.startswith("Dr. "):
            dt_initial = person.name[4]
        else: 
            dt_initial = person.name[0]
        dt_surname = person.name.split()[-1]
        
        if(dt_initial == rfc_initial) and (dt_surname == rfc_surname):
            matching.append(person)

    return matching

####
# writing csv

node_file = "rfc-nodes.csv"
edge_file = "rfc-edges.csv"
authors_file = "rfc_authors.txt"

node_headers = ["id","label","affiliation"]
edge_headers = ["target", "source", "weight", "year", "RFCnum","stream","title", "draft"]

with open(node_file, 'w') as nodef:
    with open(edge_file, 'w') as edgef:

        nodecsv = csv.DictWriter(nodef, node_headers, restval="?")
        edgecsv = csv.DictWriter(edgef, edge_headers, restval="?")

        nodecsv.writeheader()
        edgecsv.writeheader()

        all_authors = {}

        #for rfc in islice(ri.rfcs(), 800, 830):
        for rfc in islice(ri.rfcs(), 100, 1000):
            authors = []
            node = {}
            edge = {}
            
            for author in rfc.authors:
                name = "?"
                personID = "?"

                matches = get_names(author)
                if len(matches) == 0: # Doesn't match any names in DT
                    print("Missing author {} for RFC {}".format(
                        author, rfc.doc_id))
                    pattern = r'[.,\-\s]'
                    personID = sub(pattern, '', author)+'?' # weird hack. id needs an int. so convert the name to ascii literal as int
                    authors.append(IncompletePerson(id=personID, name=author))
                elif len(matches) == 1: # confident match in DT
                    person = matches[0]
                    authors.append(person)
                else: # multiple possible matches
                    print("Matches for {} in RFC {}:\n{}".format(
                        author, rfc.id, matches))
                    person = random.choice(matches) # For now, just pick a random match
                    authors.append(person)
           

            edge = {"title" : rfc.title,
                    "weight": 1,
                    "year"  : rfc.year,
                    "RFCnum": rfc.doc_id,
                    "stream": rfc.stream,
                    "draft" : rfc.draft,
                    "target": "self",
                    "source": "self"
                    }

            # Add an edge for each pair of authors
            for authorpair in combinations([author.id for author in authors], 2):
                edge["target"] = authorpair[0]
                edge["source"] = authorpair[1]
                edgecsv.writerow(edge)

            # Add edge for self! @TODO
            for author in authors:
                edge["target"] = author.id
                edge["source"] = author.id
                edgecsv.writerow(edge)
            
                all_authors[author.id] = author 


        # Add a node for all our authors!
        for pid, person in all_authors.items():
            node = {"id": pid,
                    "label": person.name,
                    "affiliation": "?"
                    }

            nodecsv.writerow(node)
            
#for rfc in islice(ri.rfcs(), 800, 830):
#    output(rfc.doc_id)
#   print("  rfc.title        | {} | {}".format(rfc.doc_id, rfc.title))
#    print("  rfc.draft        | {} | {}".format(rfc.doc_id, rfc.draft))
#    for kw in rfc.keywords:
#          print("  rfc.keyword      | {} | {}".format(rfc.doc_id, kw))
#     print("  rfc.date         | {} | {} {}".format(rfc.doc_id, rfc.month, rfc.year))
#     print("  rfc.stream       | {} | {}".format(rfc.doc_id, rfc.stream))
#     print("  rfc.wg           | {} | {}".format(rfc.doc_id, rfc.wg))
#     print("  rfc.area         | {} | {}".format(rfc.doc_id, rfc.area))
#     print("  rfc.publ_status  | {} | {}".format(rfc.doc_id, rfc.publ_status))
#     print("  rfc.curr_status  | {} | {}".format(rfc.doc_id, rfc.curr_status))
#     print("  rfc.april_fool   | {} | {}".format(rfc.doc_id, rfc.day is not None))
#     print("  rfc.page_count   | {} | {}".format(rfc.doc_id, rfc.page_count))
#     for doc in rfc.updates:
#         print("  rfc.updates      | {} | {}".format(rfc.doc_id, doc))
#     for doc in rfc.updated_by:
#         print("  rfc.updated-by   | {} | {}".format(rfc.doc_id, doc))
#     for doc in rfc.obsoletes:
#         print("  rfc.obsoletes    | {} | {}".format(rfc.doc_id, doc))
#     for doc in rfc.obsoleted_by:
#         print("  rfc.obsoleted-by | {} | {}".format(rfc.doc_id, doc))
#     for a in rfc.authors:
#         print("  rfc.author       | {} | {}".format(rfc.doc_id, a))
# 
#     draft = None
#     if rfc.draft is not None:
#         draft = dt.document_from_draft(rfc.draft[:-3])
#         if draft is None:
#             draft = dt.document_from_rfc(rfc.doc_id)
#     else:
#         draft = dt.document_from_rfc(rfc.doc_id)
#     if draft is not None:
#         print_dt_info(rfc.doc_id, draft)
#     else:
#         # Can't find information about the Internet-draft, try to look up
#         # authors individually:
#         for author in rfc.authors:
#             rfc_initial = author[0]
#             rfc_surname = author.split()[-1]
#             matching = []
#             for person in dt.people(name_contains = rfc_surname):
#                 if person.name.startswith("Dr. "):
#                     dt_initial = person.name[4]
#                 else:
#                     dt_initial = person.name[0]
#                 dt_surname = person.name.split()[-1]
#                 if (dt_initial == rfc_initial) and (dt_surname == rfc_surname):
#                     matching.append(person)
#             if len(matching) == 0:
#                 # No matching authors
#                 pass
#             elif len(matching) == 1:
#                 print_dt_person(rfc.doc_id, matching[0])
#             else:
#                 # Multiple people in the datatracker with the same initial
#                 # and surname
#                 pass



# =============================================================================
