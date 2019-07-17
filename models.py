from otree.api import (
    models, BaseConstants, BaseSubsession, BasePlayer,
)
from otree_redwood.models import Group as RedwoodGroup
from django.db import transaction
from django.db.models import F
from .exchange import Exchange
from .utils import ConfigManager
from jsonfield import JSONField

class Constants(BaseConstants):
    name_in_url = 'etf_cda'
    players_per_group = None
    num_rounds = 99 

    asset_names = ['A', 'B', 'C', 'D']

    # the columns of the config CSV and their types
    # this dict is used by ConfigManager
    config_fields = {
        'period_length': int,
        'num_assets': int,
        'asset_endowments': str,
        'cash_endowment': int,
    }

class Subsession(BaseSubsession):

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        # initialize ConfigManager in init so that it can be accessed
        # from views, before creating_session is called
        config_addr = 'etf_cda/configs/' + self.session.config['config_file']
        self.config = ConfigManager(config_addr, self.round_number, Constants.config_fields)

    # get a dict mapping asset names to their initial endowments
    def _get_asset_endowments(self):
        names = Constants.asset_names[:self.config.num_assets]
        endowments = map(int, self.config.asset_endowments.split())
        return dict(zip(names, endowments))

    def creating_session(self):
        if self.round_number > self.config.num_rounds:
            return

        # create one exchange for each asset
        for i in range(self.config.num_assets):
            name = Constants.asset_names[i]
            for group in self.get_groups():
                group.exchanges.create(asset_name=name)
        
        # initialize players' cash and assets
        asset_endowments = self._get_asset_endowments()
        for player in self.get_players():
            player.set_endowment(asset_endowments, self.config.cash_endowment)


class Group(RedwoodGroup):

    # group has a field 'exchanges' which is a related name from a ForeignKey on Exchange
    # this field is a queryset of all the exchange objectes associated with this group

    # get a player object given their participant code
    def _get_player(self, pcode):
        for player in self.get_players():
            if player.participant.code == pcode:
                return player
        return None
    
    def _on_orders_event(self, event):
        print(event.payload)
    
    def _handle_message(self, msg):
        if msg['type'] == 'enter':
            self._handle_enter(msg)

    def _handle_enter(self, msg):
        player = self._get_player(msg['pcode'])
        player.refresh_from_db()

        if msg['is_bid'] and player.cash < msg['price']:
            print('{}\'s order rejected: insufficient cash'.format(msg['pcode']))
            return
        if not msg['is_bid'] and player.assets[msg['asset_name']] < 1:
            print('{}\'s order rejected: insufficient amount of asset {}'.format(msg['pcode'], msg['asset_name']))
            return

        exchange = self.exchanges.get(asset_name=msg['asset_name'])
        exchange.enter_order(
            msg['price'],
            msg['is_bid'],
            msg['pcode'],
        )

    def handle_trade(self, price, bid_pcode, ask_pcode, asset_name):
        print('trade: {} sold asset {} to {} for {}'.format(ask_pcode, asset_name, bid_pcode, price))
        bid_player = self._get_player(bid_pcode)
        ask_player = self._get_player(ask_pcode)

        # update cash with an F-expression for atomicity
        bid_player.cash = F('cash') - price
        bid_player.save(update_fields=['cash'])

        # can't use F-expressions with jsonfield so we have to lock
        with transaction.atomic():
            ask_player_locked = (
                Player.objects
                      .select_for_update()
                      .get(pk=ask_player.pk)
            )
            ask_player_locked.assets[asset_name] -= 1
            ask_player_locked.save(update_fields=['assets'])


class Player(BasePlayer):

    assets = JSONField()
    cash   = models.IntegerField()

    def set_endowment(self, asset_endowments, cash_endowment):
        self.assets = asset_endowments
        self.cash   = cash_endowment
        self.save()

    # jsonfield is broken, it needs this special hack to get saved correctly
    # for more info see https://github.com/Leeps-Lab/otree-redwood/blob/master/otree_redwood/models.py#L160
    def save(self, *args, **kwargs):
        super().save(*args, **kwargs)
        if self.pk is not None:
            update_fields = kwargs.get('update_fields')
            json_fields = {}
            for field in self._meta.get_fields():
                if isinstance(field, JSONField) and (update_fields is None or field.attname in update_fields):
                    json_fields[field.attname] = getattr(self, field.attname)
            self.__class__._default_manager.filter(pk=self.pk).update(**json_fields)
