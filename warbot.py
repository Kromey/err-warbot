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
    # Figure out when
    \s(?:
        # "in" tells us how many minutes from now
        (?:(?:in\s)?
            (?P<in>[\d]+)(?:\smin(ute)?s?)?
        )
        |
        # "at" may tell us the top-of-the-hour to start at...
        (?:at\s
            (?P<at_hour>[012]?[\d])
        )
        |
        # ...or a more specific time to start at
        (?:(?:at\s)?
            (?P<at_time>[012]?[\d]:[0-5][\d])
        )
        |
        # Or start it immediately!
        (?P<at_now>now)
    )?
    $
"""


class WarBot(BotPlugin):
    """Let Errbot run word wars"""
    min_err_version = '4.3.0' # Optional, but recommended

    _wars = {}

    _poller_interval = 3
    _max_countdown = 60

    def activate(self):
        super().activate()
        self._wars = {}
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

        war = {'active':True}

        try:
            if self._wars[room]['active']:
                return "We're already word warring!"
        except KeyError:
            pass

        war['duration'] = int(duration)
        war['room'] = self.query_room(room)

        # Default to a 5-minute countdown
        countdown = 5

        if args['at_hour'] or args['at_time']:
            today = datetime.today()
            now = datetime.now().time()
            if args['at_time']:
                hour, minute = args['at_time'].split(':')
                start = time(hour=int(hour), minute=int(minute))
            else:
                start = time(hour=int(args['at_hour']))

            now = datetime.combine(today,now)
            start = datetime.combine(today,start)

            # 12-hour intervals let us quickly "flip" from am to pm and back
            delta = timedelta(hours=12)

            # Since we don't require "am/pm" nor 24-hour notation, let's try to
            # deduce which -- or if we need to cross to tomorrow
            while start < now:
                start = start + delta

            # Just in case we misinterpreted a time (e.g. interpreted as "noon"
            # when user meant "midnight"), wind the clock backwards if we can
            while start > now + delta:
                start = start - delta

            diff = start - now
            countdown = math.ceil(diff.total_seconds()/60)
        elif args['at_now']:
            # Start right away
            countdown = 0
        elif args['in']:
            countdown = int(args['in'])

        if countdown > self._max_countdown:
            return "That's a long ways away, let's set that up later instead, okay?"

        war['countdown'] = countdown
        self._wars[room] = war

        if countdown > 0:
            return "Sounds like fun! I'll time you!"
        else:
            return "What are you waiting for? {:d}-minute word war starts right now!".format(int(duration))

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

