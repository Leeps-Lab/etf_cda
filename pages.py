from otree.api import Currency as c, currency_range
from . import models
from ._builtin import Page, WaitPage
from .models import Constants
import json

class TextInterface(Page):

    def vars_for_template(self):
        bids = []
        asks = []
        trades = []
        for exchange in self.group.exchanges.all():
            for bid_order in exchange._get_bids_qset():
                bids.append({
                    'timestamp': bid_order.timestamp.timestamp(),
                    'price': bid_order.price,
                    'pcode': bid_order.pcode,
                    'order_id': bid_order.id,
                    'asset_name': exchange.asset_name,
                })
            for ask_order in exchange._get_asks_qset():
                asks.append({
                    'timestamp': bid_order.timestamp.timestamp(),
                    'price': ask_order.price,
                    'pcode': ask_order.pcode,
                    'order_id': ask_order.id,
                    'asset_name': exchange.asset_name,
                })
            for trade in exchange._get_trades_qset():
                trades.append({
                    'timestamp': trade.timestamp.timestamp(),
                    'price': trade.price,
                    'bid_pcode': trade.bid_order.pcode,
                    'ask_pcode': trade.ask_order.pcode,
                })
        return {
            'bids': json.dumps(bids),
            'asks': json.dumps(asks),
            'trades': json.dumps(trades),
            'assets': json.dumps(self.player.assets),
            'cash': self.player.cash,
        }

    def is_displayed(self):
        return self.round_number < self.subsession.config.num_rounds


class ResultsWaitPage(WaitPage):

    def is_displayed(self):
        return self.round_number < self.subsession.config.num_rounds


class Results(Page):

    def is_displayed(self):
        return self.round_number < self.subsession.config.num_rounds

page_sequence = [
    TextInterface,
    ResultsWaitPage,
    Results
]
