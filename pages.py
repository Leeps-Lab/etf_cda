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
                bids.append(bid_order.as_dict())
            for ask_order in exchange._get_asks_qset():
                asks.append(ask_order.as_dict())
            for trade in exchange._get_trades_qset():
                trades.append({
                    'timestamp': trade.timestamp.timestamp(),
                    'asset_name': exchange.asset_name,
                    'taking_order': trade.taking_order.as_dict(),
                    'making_orders': trade.get_making_orders_dicts(),
                })
        return {
            'bids': json.dumps(bids),
            'asks': json.dumps(asks),
            'trades': json.dumps(trades),
            'assets': json.dumps(self.player.assets),
            'cash': self.player.cash,
        }

    def is_displayed(self):
        return self.round_number <= self.subsession.config.num_rounds


class ResultsWaitPage(WaitPage):

    def is_displayed(self):
        return self.round_number <= self.subsession.config.num_rounds


class Results(Page):

    def is_displayed(self):
        return self.round_number <= self.subsession.config.num_rounds

page_sequence = [
    TextInterface,
    ResultsWaitPage,
    Results
]
