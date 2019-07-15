from otree.api import (
    models, BaseConstants, BaseSubsession, BasePlayer,
)
from otree_redwood.models import Group as RedwoodGroup
from .exchange import Exchange
from .utils import ConfigManager

class Constants(BaseConstants):
    name_in_url = 'etf_cda'
    players_per_group = None
    num_rounds = 99 

    config_fields = {
        'period_length': int,
    }

class Subsession(BaseSubsession):

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        # initialize ConfigManager in init so that it can be accessed
        # from views, before creating_session is called
        config_addr = 'etf_cda/configs/' + self.session.config['config_file']
        self.config = ConfigManager(config_addr, self.round_number, Constants.config_fields)

    def creating_session(self):
        if self.round_number > self.config.num_rounds:
            return

        for group in self.get_groups():
            Exchange.objects.create(group=group, name='A')


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
