# -*- coding: utf-8 -*-
import dbselectors
import redeclipse
import time
caches = {}
classes = []


class base:

    def __init__(self, sel):
        self.sel = sel
        self.cache = {}
        self.need = []
        self.lasttime = 0

    def calcall(self):
        if time.time() - self.lasttime > 60 * 5:
            self.lasttime = time.time()
            for need in self.need:
                self.calc(*need)

    def get(self, what, days=0):
        idx = '%s%d' % (what, days)
        if idx not in self.cache:
            self.calc(what, days)
            self.need.append((what, days))
        return self.cache[idx]


class spm(base):

    def makelist(self, key, days=0, sortkey=lambda x: -x[1]):
        players = {}
        d = {}
        gs = dbselectors.GameSelector(self.sel)
        gs.minimal = 'basicplayer2'
        if days:
            gs.gamefilter = """
            (%d - time) < (60 * 60 * 24 * %d)
            AND mode != %d""" % (time.time(), days, redeclipse.modes["race"])
        else:
            gs.gamefilter = """mode != %d""" % (redeclipse.modes["race"])
        for game in list(gs.getdict().values()):
            for player in game["players"]:
                if player["handle"]:
                    if player["handle"] not in players:
                        players[player["handle"]] = 0
                    players[player["handle"]] += key[0](player)
                    if player["handle"] not in d:
                        d[player["handle"]] = 0
                    d[player["handle"]] += key[1](player)
        for p in players:
            players[p] /= max(1, d[p])
            players[p] = round(players[p])
        return sorted(list(players.items()), key=sortkey)

    def calc(self, what, days):
        idx = '%s%d' % (what, days)
        self.cache[idx] = self.makelist({
            'dpm': (lambda x: x['damage'], lambda x: x['timealive'] / 60),
            'fpm': (lambda x: x['frags'], lambda x: x['timealive'] / 60),
            'spm': (lambda x: x['score'], lambda x: x['timealive'] / 60),
            }[what], days)


class plsingle(base):

    def makelist(self, key, days=0, sortkey=lambda x: -x[1]):
        players = {}
        gs = dbselectors.GameSelector(self.sel)
        if days:
            gs.gamefilter = """
            (%d - time) < (60 * 60 * 24 * %d)
            AND mode != %d""" % (time.time(), days, redeclipse.modes["race"])
        else:
            gs.gamefilter = """mode != %d""" % (redeclipse.modes["race"])
        for game in list(gs.getdict().values()):
            for player in game["players"]:
                if player["handle"]:
                    if player["handle"] not in players:
                        players[player["handle"]] = 0
                    players[player["handle"]] += key(player)
        return sorted(list(players.items()), key=sortkey)

    def calc(self, what, days):
        idx = '%s%d' % (what, days)
        self.cache[idx] = self.makelist({
            'games': lambda x: 1,
            'score': lambda x: x['score'],
            'captures': lambda x: len(x['captures']),
            'bombings': lambda x: len(x['bombings']),
            }[what], days)


def make(sel):
    classes.append((spm(sel), "spm"))
    classes.append((plsingle(sel), "plsingle"))
    for c in classes:
        caches[c[1]] = c[0]