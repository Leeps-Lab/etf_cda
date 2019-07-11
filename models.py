from otree.api import (
    models, BaseConstants, BaseSubsession, BasePlayer,
)
from otree_redwood.models import Group as RedwoodGroup
from .exchange import Exchange

class Constants(BaseConstants):
    name_in_url = 'etf_cda'
    players_per_group = None
    num_rounds = 1


class Subsession(BaseSubsession):

    def creating_session(self):

        for group in self.get_groups():
            Exchange.objects.create(group=group)


class Group(RedwoodGroup):

    # group has a field 'exchanges' which is a related name from a ForeignKey on Exchange
    # this field is a queryset of all the exchange objectes associated with this group

    def _handle_message(self, msg):
        exchange = self.exchanges.first()
        if msg['type'] == 'enter':
            exchange.enter_order(
                msg['price'],
                msg['is_bid'],
                msg['pcode'],
            )

    def handle_trade(self, price=None, bid_pcode=None, ask_pcode=None):
        print('trade: {} sold to {} for {}'.format(ask_pcode, bid_pcode, price))


class Player(BasePlayer):
    pass
