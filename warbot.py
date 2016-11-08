from datetime import datetime,time,timedelta
import math
import random,re


from errbot import BotPlugin, botcmd, re_botcmd


_WarCommandPattern = r"""
    (?:
        word\s?war\s
        (?:for\s)?
        (?P<duration1>[\d]+)?(?:[- ]?min(ute)?s?)?
        |
        (?P<duration2>[\d]+)?(?:[- ]?min(ute)?s?)?
        \sword\s?war
    )
    (?:\sbeginning|begins?)?
    # "in" sets up an X-minute countdown
    (?:\sin\s
        (?P<in>[\d]+)(?:\smin(ute)?s?)?
    )?
    # "at" will calculate the countdown to start at the specified time
    (?:\sat\s
        (?P<at_hour>[012]?[\d])
        (?::(?P<at_minute>\d\d))?
    )?
"""


class WarBot(BotPlugin):
    """Let Errbot run word wars"""
    min_err_version = '4.3.0' # Optional, but recommended

    _wars = {}

    _poller_interval = 3
    _max_countdown = 60

    def activate(self):
        super().activate()
        self.start_poller(self._poller_interval, self._run_wordwar)

    @re_botcmd(
            pattern=_WarCommandPattern,
            flags=re.X,
            name="word war",
            )
    def word_war(self, msg, match):
        """Start a wordwar

        This command aims to be flexible and natural:
          * word war for 5 minutes in 12 minutes
          * word war 6 [in 5 minutes]
          * wordwar for 5 mins in 1 min
        etc.
        """
        if msg.type != "groupchat":
            return "Sorry, I only run word wars in chat rooms"

        args = match.groupdict()
        room = str(msg.frm.room)
        duration = args['duration1'] or args['duration2']

        try:
            if self._wars[room]['active']:
                return "We're already word warring!"
        except KeyError:
            self._wars[room] = {'active':False}

        self._wars[room]['duration'] = int(duration)
        self._wars[room]['room'] = self.query_room(room)

        if args['at_hour']:
            today = datetime.today()
            now = datetime.now().time()
            if args['at_minute']:
                then = time(hour=int(args['at_hour']), minute=int(args['at_minute']))
            else:
                then = time(hour=int(args['at_hour']))

            now = datetime.combine(today,now)
            then = datetime.combine(today,then)

            while then < now:
                then = then + timedelta(hours=12)

            diff = then - now
            countdown = math.ceil(diff.total_seconds()/60)
        else:
            countdown = args['in'] or 5

        if int(countdown) > self._max_countdown:
            return "That's a long ways away, let's set that up later instead, okay?"

        self._wars[room]['countdown'] = int(countdown)
        self._wars[room]['active'] = True

        return "Sounds like fun! I'll time you!"

    @botcmd(admin_only=True)
    def war_cancel(self, msg, args):
        """Cancel a word war.

        With the argument '--all', this will forcibly and silently cancel ALL
        word wars; otherwise, the argument is expected to be the name of the
        room with an active word war, which will be cancelled with a message to
        the room blaming you."""
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
        """List active word wars"""
        yield "The following wars are active:"
        for war in self._wars:
            if self._wars[war]['active']:
                yield "{war}: {duration} min(s) in {countdown} min(s)".format(
                        war=war,
                        duration=self._wars[war]['duration'],
                        countdown=self._wars[war]['countdown'],
                        )

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
                    self._announce(war['room'], "{:d}-minute word war! Go go go!", war['duration'])
                    self._announce(war['room'], "Good luck everyone!")
                else:
                    if war['countdown'] == 1:
                        self._announce(war['room'], "Get ready! {:d}-minute word war in 1 minute!", war['duration'])
                    elif war['countdown'] == 5:
                        self._announce(war['room'], "5-minute warning for our {:d}-minute word war!", war['duration'])
                    elif war['countdown'] == 2:
                        self._announce(war['room'], "2 minutes to go!")
                    elif war['countdown'] <= 3:
                        self._announce(war['room'], "Our word war starts in {:d} minutes!", war['countdown'])
            else:
                war['duration'] -= 1

                if war['duration'] <= 0:
                    war['active'] = False
                    self._announce(war['room'], "Word war over!")

