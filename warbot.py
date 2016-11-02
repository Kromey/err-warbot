from errbot import BotPlugin, botcmd
import random

class WarBot(BotPlugin):
    """Let Errbot run word wars"""
    min_err_version = '3.0.5' # Optional, but recommended

    _in_progress = False
    _start = 0
    _duration = 0
    _countdown = 0
    _wordwar_room = None

    @botcmd
    def wordwar(self, msg, args):
        """Start a wordwar"""
        if self._in_progress:
            return "Cannot start a word war while one is already in progress!"
        elif msg.type != "groupchat":
            return "Word wars must be run in group chats!"
        elif args and args.isnumeric():
            mins = int(args)
            self._duration = mins
            self._countdown = 5
            self._in_progress = True

            self._wordwar_room = self.query_room(msg.frm.room)

            self.start_poller(60, self._start_wordwar)
            return "{:d} minute word war will begin in {:d} minutes".format(mins, self._countdown)
        else:
            return "You gotta tell me how long it'll go!"

    @botcmd(admin_only=True)
    def cancel_wordwar(self, msg, args):
        if not self._in_progress:
            return "No word war to cancel"

        self._in_progress = False

        response = []

        try:
            self.stop_poller(self._start_wordwar)
            response.append("Stopped countdown poller")
        except ValueError:
            response.append("No countdown to stop")

        try:
            self.stop_poller(self._end_wordwar)
            response.append("Stopped wordwar poller")
        except ValueError:
            response.append("No wordwar to stop")

        self._announce("Word war has been cancelled by {}!", msg.frm.nick)

        response.append("Word war cancelled!")

        return "\n".join(response)

    def _announce(self, msg, *args, **kwargs):
        self.send(
                self._wordwar_room,
                msg.format(*args, **kwargs),
                )

    def _start_wordwar(self):
        self._countdown -= 1
        if self._countdown <= 0:
            self.stop_poller(self._start_wordwar)
            self._announce("Word war for {:d} minutes begins now!", self._duration)
            self.start_poller(60 * self._duration, self._end_wordwar)
        else:
            self._announce("Word war begins in {:d} minutes!", self._countdown)

    def _end_wordwar(self):
        self._in_progress = False
        self._announce("Word war over!")
        self.stop_poller(self._end_wordwar)

