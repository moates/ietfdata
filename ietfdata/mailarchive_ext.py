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

import ietfdata.datatracker as dt
import email.utils
import time

from datetime             import datetime, timedelta
from ietfdata.mailarchive import *

# =================================================================================================

class MessageMetadata:
    from_name          : str
    from_addr          : str
    person             : Optional[dt.Person]
    timestamp          : datetime
    mailing_list_name  : str
    msg_id             : int
    msg                : Message

    def __init__(self, mailing_list_name: str, msg_id: int, message: Message, datatracker: dt.DataTracker, cache_dir: Path):
        cache_filepath = Path(cache_dir, "mailing-lists-metadata", mailing_list_name, f"{msg_id:06d}.json")
        if cache_filepath.exists():
            with open(cache_filepath, "r") as cache_file:
                msg_json = json.load(cache_file)
                self.from_name         = msg_json["from_name"]
                self.from_addr         = msg_json["from_addr"]
                self.person            = datatracker.person(dt.PersonURI(msg_json["person_uri"])) if msg_json["person_uri"] != "" else None
                self.timestamp         = datetime.fromisoformat(msg_json["timestamp"])
                self.mailing_list_name = msg_json["mailing_list_name"]
                self.msg_id            = msg_json["msg_id"]
                self.msg               = message
        else:
            self.from_name, self.from_addr = email.utils.parseaddr(message["From"])
            self.mailing_list_name = mailing_list_name
            self.msg_id = msg_id
            self.msg = message
            self.person = datatracker.person_from_email(self.from_addr)
            self.timestamp = datetime.fromtimestamp(time.mktime(email.utils.parsedate(message["Date"])))
            self._cache_obj(cache_dir)


    def _cache_obj(self, cache_file: Path) -> None:
        cache_dir = Path(cache_file, "mailing-lists-metadata", self.mailing_list_name)
        cache_dir.mkdir(parents=True, exist_ok=True)
        cache_filepath = Path(cache_dir, f"{self.msg_id:06d}" + ".json")
        with open(cache_filepath, "w+") as cache_file:
            json.dump({"from_name"          : self.from_name,
                       "from_addr"          : self.from_addr,
                       "person_uri"         : self.person.resource_uri.uri if self.person is not None else "",
                       "mailing_list_name"  : self.mailing_list_name,
                       "msg_id"             : self.msg_id,
                       "timestamp"          : self.timestamp.isoformat()},
                      cache_file)

    # Formal messages that can be searched for:
    # - "I-D Action:"
    # - "Document Action:"
    # - "Protocol Action:"
    # - "WG Action:"
    # - "WG Review:"
    # - "Last Call:"
    # - "<wg name> Virtual Meeting"
    # - "RFCxxxx on"
    # - RFC errata announcements
    # - <directorate> last call review
    # - <directorate> telechat review
    # - IESG ballot position announcements
    # (all sometime preceded by "Correction:" or "REVISED")
    # From: addresses have varied over time
    # many of these will need to be implemented in a helper class, that
    # has access to the datatracker, RFC index, and mailing list archives.

# =================================================================================================================================

class MailingListExt(MailingList):
    """
    The `MailingListExt` class extends the `MailingList` with methods that
    augment the mailing list with metadata from the Datatracker.
    """
    _datatracker : dt.DataTracker

    def __init__(self, cache_dir: Path, list_name: str):
        super().__init__(cache_dir, list_name)
        self._datatracker = dt.DataTracker(cache_dir)


    def messages_metadata(self,
                          person : Optional[dt.Person] = None) -> Iterator[MessageMetadata]:
        for msg_path in sorted(self._cache_folder.glob("*.msg")):
            msg_id = int(str(msg_path)[str(msg_path).rfind('/')+1:-4])
            msg_m  = MessageMetadata(self._list_name, msg_id, self.message(msg_id), self._datatracker, self._cache_dir)
            if person is None or msg_m.person == person:
                yield msg_m

# =================================================================================================================================

class MailArchiveExt(MailArchive):
    """
    The `MailArchiveExt` class extends the `MailArchive` with methods that
    augment the mail archive with metadata from the Datatracker.
    """
    _datatracker   : dt.DataTracker
    _mailing_lists : Dict[str,MailingListExt]

    def __init__(self, cache_dir: Path):
        super().__init__(cache_dir)
        self._datatracker = dt.DataTracker(cache_dir)


    def mailing_list(self, mailing_list_name: str) -> MailingListExt:
        if not mailing_list_name in self._mailing_lists:
            self._mailing_lists[mailing_list_name] = MailingListExt(self._cache_dir, mailing_list_name)
        return self._mailing_lists[mailing_list_name]

    # dt.Group -> Iterator[MailingListExt] 

# =================================================================================================================================
# vim: set tw=0 ai:
