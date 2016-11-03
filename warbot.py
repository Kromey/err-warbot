from datetime import datetime
import random


from errbot import BotPlugin, botcmd, re_botcmd

class WarBot(BotPlugin):
    """Let Errbot run word wars"""
    min_err_version = '4.3.0' # Optional, but recommended

    _wars = {}

    _poller_interval = 3

    def activate(self):
        super().activate()
        self.start_poller(self._poller_interval, self._run_wordwar)

    @re_botcmd(
            pattern=r'^word ?war (for )?(?P<duration>[\d]+)( min(ute)?s?)? ?(in (?P<in>[\d]+)( min(ute)?s?)?)?(at (?P<at_hour>[\d]+)(:(?P<at_minute>[\d]+))?)?',
            name="word war",
            )
    def word_war(self, msg, match):
        """Start a wordwar"""
        if msg.type != "groupchat":
            return "Sorry, I only run word wars in chat rooms"

        args = match.groupdict()
        room = str(msg.frm.room)

        try:
            if self._wars[room]['active']:
                return "We're already word warring!"
        except KeyError:
            self._wars[room] = {'active':False}

        self._wars[room]['duration'] = int(args['duration'])
        self._wars[room]['room'] = self.query_room(room)

        if args['at_hour']:
            return "Sorry, I haven't been coded for that format just yet."
        else:
            if not args['in']:
                args['in'] = 5

            self._wars[room]['countdown'] = int(args['in'])

        self._wars[room]['active'] = True

        return "{:d} minute word war will begin in {:d} minutes".format(
                self._wars[room]['duration'],
                self._wars[room]['countdown'],
                )

    @botcmd(admin_only=True)
    def war_cancel(self, msg, args):
        if args == '--all':
            self._wars = {}
            return "All word wars cancelled"

        try:
            self._wars[args]['active'] = False
            self._announce(
                    self._wars[args]['room'],
                    "Word war cancelled by {}!",
                    msg.frm.nick,
                    )
            return "Word war cancelled"
        except KeyError:
            return "No matching word war found"

    @botcmd(admin_only=True)
    def war_list(self, msg, args):
        yield "The following wars are active:"
        for war in self._wars:
            if self._wars[war]['active']:
                yield war

    def _announce(self, room, msg, *args, **kwargs):
        self.send(
                room,
                msg.format(*args, **kwargs),
                )

    def _run_wordwar(self):
        if datetime.now().second >= self._poller_interval:
            return

        for room in self._wars:
            war = self._wars[room]

            if not war['active']:
                continue

            if war['countdown'] > 0:
                war['countdown'] -= 1

                if war['countdown'] <= 0:
                    self._announce(war['room'], "Word war for {:d} minutes begins now!", war['duration'])
                else:
                    self._announce(war['room'], "Word war starts in {:d} minutes", war['countdown'])
            else:
                war['duration'] -= 1

                if war['duration'] <= 0:
                    war['active'] = False
                    self._announce(war['room'], "Word war over!")

