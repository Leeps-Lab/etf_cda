from otree.api import Currency as c, currency_range
from . import views
from ._builtin import Bot
from .models import Constants

class PlayerBot(Bot):

    def play_round(self):

        if self.player.id_in_group == 1:
            self.p1_round()
        else:
            self.p2_round()

        yield (views.MyPage)
        yield (views.Results)
    
    def p1_round(self):
        msg = {
            'type': 'enter',
            'price': 100,
            'is_bid': False,
            'pcode': self.participant.code,
        }
        self.group._handle_message(msg)
        msg = {
            'type': 'enter',
            'price': 90,
            'is_bid': False,
            'pcode': self.participant.code,
        }
        self.group._handle_message(msg)
    
    def p2_round(self):
        msg = {
            'type': 'enter',
            'price': 100,
            'is_bid': True,
            'pcode': self.participant.code,
        }
        self.group._handle_message(msg)
