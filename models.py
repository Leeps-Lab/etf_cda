from otree.api import (
    models, BaseConstants, BaseSubsession, BasePlayer,
)
from otree_redwood.models import Group as RedwoodGroup
from .exchange import Exchange
from .configmanager import ConfigManager
from . import validate
from jsonfield import JSONField

class Constants(BaseConstants):
    name_in_url = 'otree_markets'
    players_per_group = None
    num_rounds = 99 

    asset_names = ['A']

    # the columns of the config CSV and their types
    # this dict is used by ConfigManager
    config_fields = {
        'period_length': int,
        'num_assets': int,
        'asset_endowments': str,
        'cash_endowment': int,
    }

class Subsession(BaseSubsession):
    
    @property
    def config(self):
        config_addr = 'otree_markets/configs/' + self.session.config['config_file']
        return ConfigManager(config_addr, self.round_number, Constants.config_fields)

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
    # this field is a queryset of all the exchange objects associated with this group

    def _get_player(self, pcode):
        '''get a player object given its participant code'''
        for player in self.get_players():
            if player.participant.code == pcode:
                return player
        raise ValueError('invalid player code: "{}"'.format(pcode))
    
    def _on_chan_event(self, event):
        '''the entry point for all incoming (frontend -> backend) messages.
        dispatches messages to their appropriate handler using their type field'''
        msg = event.value
        if msg['type'] == 'enter':
            validate.validate_enter(msg['payload'])
            self._handle_enter(msg['payload'])
        elif msg['type'] == 'cancel':
            validate.validate_cancel(msg['payload'])
            self._handle_cancel(msg['payload'], event.participant.code)
        else:
            raise ValueError('invalid inbound message type: "{}"'.format(msg['type']))

    def _handle_enter(self, enter_msg):
        '''handle an enter message sent from the frontend'''
        player = self._get_player(enter_msg['pcode'])
        player.refresh_from_db()

        if enter_msg['is_bid'] and player.cash < enter_msg['price']:
            print('{}\'s order rejected: insufficient cash'.format(enter_msg['pcode']))
            return
        if not enter_msg['is_bid'] and player.assets[enter_msg['asset_name']] < 1:
            print('{}\'s order rejected: insufficient amount of asset {}'.format(enter_msg['pcode'], enter_msg['asset_name']))
            return

        exchange = self.exchanges.get(asset_name=enter_msg['asset_name'])
        order_id = exchange.enter_order(
            enter_msg['price'],
            enter_msg['is_bid'],
            enter_msg['pcode'],
        )
    
    def _handle_cancel(self, cancel_msg, sender_pcode):
        '''handle a cancel message sent from the frontend'''
        if cancel_msg['pcode'] != sender_pcode:
            print('cancel rejected: players can\t cancel others\' orders')
            return
        
        exchange = self.exchanges.get(asset_name=cancel_msg['asset_name'])
        exchange.cancel_order(
            cancel_msg['is_bid'],
            cancel_msg['order_id'],
        )

    def confirm_enter(self, timestamp, price, is_bid, pcode, asset_name, order_id):
        '''send an order entry confirmation to the frontend. this function is called
        by the exchange when an order is successfully entered'''
        confirm_msg = {
            'type': 'confirm_enter',
            'payload': {
                'timestamp': timestamp,
                'price': price,
                'is_bid': is_bid,
                'pcode': pcode,
                'asset_name': asset_name,
                'order_id': order_id,
            }
        }
        self.send('chan', confirm_msg)

    def handle_trade(self, timestamp, price, bid_pcode, ask_pcode, bid_order_id, ask_order_id, asset_name):
        '''send a trade confirmation to the frontend. this function is called by the exchange when a trade occurs'''
        print('trade: {} sold asset {} to {} for {}'.format(ask_pcode, asset_name, bid_pcode, price))
        bid_player = self._get_player(bid_pcode)
        ask_player = self._get_player(ask_pcode)

        bid_player.cash -= price
        bid_player.assets[asset_name] += 1
        bid_player.save()

        ask_player.cash += price
        ask_player.assets[asset_name] -= 1
        ask_player.save()

        confirm_msg = {
            'type': 'confirm_trade',
            'payload': {
                'timestamp': timestamp,
                'price': price,
                'bid_pcode': bid_pcode,
                'ask_pcode': ask_pcode,
                'bid_order_id': bid_order_id,
                'ask_order_id': ask_order_id,
                'asset_name': asset_name,
            }
        }
        self.send('chan', confirm_msg)
    
    def confirm_cancel(self, order_id, is_bid, asset_name, pcode):
        '''send an order cancel confirmation to the frontend. this function is called
        by the exchange when an order is successfully canceled'''
        confirm_msg = {
            'type': 'confirm_cancel',
            'payload': {
                'order_id': order_id,
                'is_bid': is_bid,
                'asset_name': asset_name,
                'pcode': pcode,
            }
        }
        self.send('chan', confirm_msg)


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
