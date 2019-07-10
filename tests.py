from otree.api import Currency as c, currency_range
from . import views
from ._builtin import Bot
from .models import Constants

class PlayerBot(Bot):

    def play_round(self):

        msg = {
            'price': 100,
            'is_bid': True,
            'pcode': self.participant.code,
        }
        self.group.exchanges.first().handle_msg_in(msg)
        msg = {
            'price': 101,
            'is_bid': True,
            'pcode': self.participant.code,
        }
        self.group.exchanges.first().handle_msg_in(msg)
        msg = {
            'price': 100,
            'is_bid': False,
            'pcode': self.participant.code,
        }
        self.group.exchanges.first().handle_msg_in(msg)
        msg = {
            'price': 101,
            'is_bid': False,
            'pcode': self.participant.code,
        }
        self.group.exchanges.first().handle_msg_in(msg)


        yield (views.MyPage)
        yield (views.Results)
