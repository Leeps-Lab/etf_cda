from . import pages 
from otree.api import Bot, Submission

class PlayerBot(Bot):

    def print_assets(self):
        for player in self.group.get_players():
            print(player.participant.code + ':')
            print(player.assets, player.cash)

    def play_round(self):
        if self.round_number > self.subsession.config.num_rounds:
            return

        if self.player.id_in_group == 1:
            self.p1_round()
        else:
            self.p2_round()

        exchange = self.group.exchanges.get(asset_name='A')
        print('orders:')
        print(exchange)
        print('trades:')
        print('\n'.join(str(e) for e in exchange._get_trades_qset()))

        yield Submission(pages.TextInterface, check_html=False)
        yield Submission(pages.Results, check_html=False)
    
    def p1_round(self):
        msg = {
            'price': 10,
            'volume': 1,
            'is_bid': True,
            'pcode': self.participant.code,
            'asset_name': 'A',
        }
        self.group._handle_enter(msg)
        msg = {
            'price': 9,
            'volume': 1,
            'is_bid': True,
            'pcode': self.participant.code,
            'asset_name': 'A',
        }
        self.group._handle_enter(msg)
    
    def p2_round(self):
        msg = {
            'price': 10,
            'volume': 2,
            'is_bid': False,
            'pcode': self.participant.code,
            'asset_name': 'A',
        }
        self.group._handle_enter(msg)
