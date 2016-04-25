from commitish import Commitish
import datetime
import time
from geogig.tools.utils import relativeDate

NULL_ID = "0" * 40

class Commit(Commitish):

    _commitcache = {}

    ''' A geogig commit'''

    def __init__(self, repo, commitid, treeid, parents, message, authorname,
                 authordate, committername, committerdate, added, removed, modified):
        Commitish.__init__(self, repo, commitid)
        self.repo = repo
        self.commitid = commitid
        self.treeid = treeid
        self._parents = parents or [NULL_ID]
        self.message = message
        self.authorname = authorname
        self.authordate = authordate
        self.committername = committername
        self.committerdate = committerdate
        self.added = added
        self.removed = removed
        self.modified = modified

    @staticmethod
    def fromref(repo, ref):
        '''
        Returns a Commit corresponding to a given id.
        ref is passed as a string.
        '''
        if ref == NULL_ID:
            return Commitish(repo, NULL_ID)
        else:
            cid = repo.revparse(ref)
            if (repo.url, cid) not in Commit._commitcache:
                log = repo.log(until = cid, limit = 1)
                Commit._commitcache[(repo.url, cid)] = log[0]
            return Commit._commitcache[(repo.url, cid)]

    @property
    def parents(self):
        '''Returns a list of commits with commits representing the parents of this commit'''
        commits =  [self.fromref(self.repo, p) for p in self._parents]
        return commits

    @property
    def parent(self):
        '''
        Returns the parent commit, assuming a linear history.
        It's similar to the tilde(~) operator
        '''
        return self.parents[0]

    def diff(self, path = None):
        '''Returns a list of DiffEntry with all changes introduced by this commitish'''
        if self._diff is None:
            self._diff = self.repo.diff(self.parent.ref, self.ref, path)
        return self._diff

    def humantext(self):
        '''Returns a nice human-readable description of the commit'''
        headid = self.repo.revparse(self.repo.HEAD)
        if headid == self.id:
            return "Current last commit"
        epoch = time.mktime(self.committerdate.timetuple())
        offset = datetime.datetime.fromtimestamp (epoch) - datetime.datetime.utcfromtimestamp (epoch)
        d = self.committerdate + offset
        return self.message + d.strftime(" (%m/%d/%y %H:%M)")

    def committerprettydate(self):
        return relativeDate(self.committerdate)

    def authorprettydate(self):
        return relativeDate(self.authordate)

    def __str__(self):
        try:
            msg = unicode(self.message, errors = "ignore")
        except TypeError:
            msg = self.message
        s = "id " + self.commitid + "\n"
        s += "parents " + str(self._parents) + "\n"
        s += "tree " + self.treeid + "\n"
        s += "author " + self.authorname + " " + str(self.authordate) + "\n"
        s += "message " + msg + "\n"

        return s