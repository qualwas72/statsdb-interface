# -*- coding: utf-8 -*-
import dbselectors
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
            AND uniqueplayers >= 2
            AND mode != re_mode(id, 'race')""" % (time.time(), days)
        else:
            gs.gamefilter = """mode != re_mode(id, 'race')"""
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
            if len(key) == 2:
                players[p] = round(players[p])
            else:
                players[p] = round(players[p], key[2])
        return sorted(list(players.items()), key=sortkey)

    def calc(self, what, days):
        idx = '%s%d' % (what, days)
        self.cache[idx] = self.makelist({
            'dpm': (lambda x: x['damage'], lambda x: x['timealive'] / 60),
            'fpm': (lambda x: x['frags'], lambda x: x['timealive'] / 60),
            'spm': (lambda x: x['score'], lambda x: x['timealive'] / 60),
            'spf': (lambda x: x['score'], lambda x: x['frags'], 1),
            }[what], days)


class plsingle(base):

    def makelist(self, key, days=0, sortkey=lambda x: -x[1]):
        players = {}
        gs = dbselectors.GameSelector(self.sel)
        if days:
            gs.gamefilter = """
            (%d - time) < (60 * 60 * 24 * %d)
            AND uniqueplayers >= %d
            AND %s""" % (time.time(), days,
                key[0], "mode != re_mode(id, 'race')" if key[0] else "1")
        else:
            gs.gamefilter = """uniqueplayers >= %d AND %s""" % (
                key[0],
                "mode != re_mode(id, 'race')" if key[0] else "1")
        for game in list(gs.getdict().values()):
            for player in game["players"]:
                if player["handle"]:
                    if player["handle"] not in players:
                        players[player["handle"]] = 0
                    players[player["handle"]] += key[1](player)
        return sorted(list(players.items()), key=sortkey)

    def calc(self, what, days):
        idx = '%s%d' % (what, days)
        self.cache[idx] = self.makelist({
            'games': (0, lambda x: 1),
            'captures': (4, lambda x: len(x['captures'])),
            'bombings': (4, lambda x: len(x['bombings'])),
            }[what], days)


class mvp(base):

    def makelist(self, key, days=0):
        players = {}
        gs = dbselectors.GameSelector(self.sel)
        gs.gamefilter = """
        ((%d - time) < (60 * 60 * 24 * %d) OR %d = 0)
        AND uniqueplayers >= %d
        AND mode != re_mode(id, 'race') AND %s
        """ % (time.time(),
            days, days,
            4,
            {'affmvp': '''(NOT (mutators & re_mut(id, 'survivor'))
            OR (mutators & re_mut(id, 'duel')))
            AND mode in (re_mode(id, 'ctf'), re_mode(id, 'bb'))''',

            'dmmvp': '''(NOT (mutators & re_mut(id, 'ffa'))
            OR (mutators & re_mut(id, 'duel'))
            OR (mutators & re_mut(id, 'survivor')))
            AND mode = re_mode(id, 'dm')'''}[key])
        for game in list(gs.getdict().values()):
            for player in game["players"]:
                if player["handle"]:
                    if player["handle"] not in players:
                        players[player["handle"]] = 0
                    players[player["handle"]] += player["score"]
        return sorted(list(players.items()),
            key=lambda x: -x[1])

    def calc(self, what, days):
        idx = '%s%d' % (what, days)
        self.cache[idx] = self.makelist(what, days)


class plwinner(base):

    def makelist(self, key, days=0):
        players = {}
        gs = dbselectors.GameSelector(self.sel)
        gs.gamefilter = """
        ((%d - time) < (60 * 60 * 24 * %d) OR %d = 0)
        AND uniqueplayers >= %d
        AND mode != re_mode(id, 'race') AND %s
        """ % (time.time(),
            days, days,
            {'ffa': 2,
            'ffasurv': 2,
            'mvp': 4}[key],
            {'ffa': "(mutators & re_mut(id, 'ffa'))",
            'mvp': '''(NOT (mutators & re_mut(id, 'ffa'))
            OR (mutators & re_mut(id, 'survivor'))
            OR (mutators & re_mut(id, 'duel')))
            AND mode in (re_mut(id, 'dm'), re_mut(id, 'ctf'),
                re_mut(id, 'dac'), re_mut(id, 'bb'))''',
            'ffasurv': '''(mutators & re_mut(id, 'ffa'))
            AND (mutators & re_mut(id, 'survivor'))'''}[key])
        for game in list(gs.getdict().values()):
            best = sorted(
                game["players"], key=lambda x: -x["score"])[0]["score"]
            for player in game["players"]:
                if player["handle"]:
                    if player["handle"] not in players:
                        players[player["handle"]] = [0, 0]
                    if player["score"] >= best:
                        players[player["handle"]][0] += 1
                    else:
                        players[player["handle"]][1] += 1
        return sorted(list(players.items()),
            key=lambda x: -(x[1][0] / max(x[1][1], 1)))

    def calc(self, what, days):
        idx = '%s%d' % (what, days)
        self.cache[idx] = self.makelist(what, days)


class plweapon(base):

    def makelist(self, key, days=0):
        gs = dbselectors.GameSelector(self.sel)
        if days:
            gs.gamefilter = """
            (%d - time) < (60 * 60 * 24 * %d)
            AND uniqueplayers >= 0
            """ % (time.time(),
                days)
        else:
            gs.gamefilter = """
            AND uniqueplayers >= 2
            """
        players = {}
        d = {}
        for game in list(gs.getdict(True).values()):
            for p in game["players"]:
                if p['handle']:
                    if p['handle'] not in players:
                        players[p['handle']] = 0
                    if p['handle'] not in d:
                        d[p['handle']] = 0
                    d[p['handle']] += p['timealive'] / 60
                    if key[1] == 0:
                        players[p['handle']] += (
                            p['weapons'][key[0]]['damage1']
                            + p['weapons'][key[0]]['damage2']
                            + ((p['weapons'][key[0]]['frags1']
                            + p['weapons'][key[0]]['frags2']) * 100))
                    else:
                        players[p['handle']] += (
                            p['weapons'][key[0]]['damage%d' % key[1]]
                            + ((p['weapons'][key[0]][
                                'frags%d' % key[1]]) * 100))
        for p in players:
            players[p] /= max(1, d[p])
            players[p] = round(players[p])
        return sorted(list(players.items()), key=lambda x: -x[1])

    def calc(self, what, days):
        idx = '%s%d' % (what, days)
        self.cache[idx] = self.makelist(what, days)


def make(sel):
    classes.append((spm(sel), "spm"))
    classes.append((plsingle(sel), "plsingle"))
    classes.append((plwinner(sel), "plwinner"))
    classes.append((plweapon(sel), "plweapon"))
    classes.append((mvp(sel), "mvp"))
    for c in classes:
        caches[c[1]] = c[0]