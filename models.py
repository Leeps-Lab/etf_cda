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

    # list of capital letters A..Z
    asset_names = [chr(i) for i in range(65, 91)]

    # the columns of the config CSV and their types
    # this dict is used by ConfigManager
    config_fields = {
        'period_length': int,
        'num_assets': int,
        'asset_endowments': str,
        'cash_endowment': int,
        'allow_short': bool,
    }

class Subsession(BaseSubsession):
    
    @property
    def config(self):
        config_addr = 'otree_markets/configs/' + self.session.config['config_file']
        return ConfigManager(config_addr, self.round_number, Constants.config_fields)

    # get a dict mapping asset names to their initial endowments
    def _get_asset_endowments(self):
        endowments = list(map(int, self.config.asset_endowments.split()))
        if len(endowments) != self.config.num_assets:
            raise ValueError('invalid config: num_assets and asset_names must agree')
        return dict(zip(Constants.asset_names, endowments))

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
        elif msg['type'] == 'accept_immediate':
            validate.validate_accept_immediate(msg['payload'])
            self._handle_accept_immediate(msg['payload'], event.participant.code)
        else:
            raise ValueError('invalid inbound message type: "{}"'.format(msg['type']))

    def _handle_enter(self, enter_msg):
        '''handle an enter message sent from the frontend'''
        player = self._get_player(enter_msg['pcode'])

        if not self.subsession.config.allow_short:
            if enter_msg['is_bid'] and player.available_cash < enter_msg['price'] * enter_msg['volume']:
                self._send_error(enter_msg['pcode'], 'Order rejected: insufficient available cash')
                return
            if not enter_msg['is_bid'] and player.available_assets[enter_msg['asset_name']] < enter_msg['volume']:
                self._send_error(enter_msg['pcode'], 'Order rejected: insufficient available amount of asset {}'.format(enter_msg['asset_name']))
                return

        exchange = self.exchanges.get(asset_name=enter_msg['asset_name'])
        order_id = exchange.enter_order(
            enter_msg['price'],
            enter_msg['volume'],
            enter_msg['is_bid'],
            enter_msg['pcode'],
        )
    
    def _handle_cancel(self, canceled_order, sender_pcode):
        '''handle a cancel message sent from the frontend'''
        if canceled_order['pcode'] != sender_pcode:
            print('cancel rejected: players can\t cancel others\' orders')
            return
        
        exchange = self.exchanges.get(asset_name=canceled_order['asset_name'])
        exchange.cancel_order(
            canceled_order['is_bid'],
            canceled_order['order_id'],
        )

    def _handle_accept_immediate(self, accepted_order, sender_pcode):
        '''handle an immediate accept message sent from the frontend'''
        player = self._get_player(sender_pcode)

        if not self.subsession.config.allow_short:
            if accepted_order['is_bid'] and player.available_cash < accepted_order['price'] * accepted_order['volume']:
                self._send_error(accepted_order['pcode'], 'Cannot accept order: insufficient available cash')
                return
            if not accepted_order['is_bid'] and player.available_assets[accepted_order['asset_name']] < accepted_order['volume']:
                self._send_error(accepted_order['pcode'], 'Cannot accept order: insufficient available amount of asset {}'.format(accepted_order['asset_name']))
                return

        exchange = self.exchanges.get(asset_name=accepted_order['asset_name'])
        exchange.accept_immediate(
            accepted_order['is_bid'],
            accepted_order['order_id'],
            sender_pcode,
        )

    def confirm_enter(self, order_dict):
        '''send an order entry confirmation to the frontend. this function is called
        by the exchange when an order is successfully entered'''
        player = self._get_player(order_dict['pcode'])
        if order_dict['is_bid']:
            player.available_cash -= order_dict['price'] * order_dict['volume']
        else:
            player.available_assets[order_dict['asset_name']] -= order_dict['volume']
        player.save()

        confirm_msg = {
            'type': 'confirm_enter',
            'payload': order_dict,
        }
        self.send('chan', confirm_msg)

    def handle_trade(self, timestamp, asset_name, taking_order, making_orders):
        '''send a trade confirmation to the frontend. this function is called by the exchange when a trade occurs'''

        taking_player = self._get_player(taking_order['pcode'])
        for making_order in making_orders:
            making_player = self._get_player(making_order['pcode'])
            # need to update making players' available cash and assets
            # since these were adjusted when their order was entered, they need to be adjusted back so they're not double counted
            if making_order['is_bid']:
                making_player.available_cash += making_order['price'] * making_order['volume']
            else:
                making_player.available_assets[making_order['asset_name']] += making_order['volume']

            volume = making_order['traded_volume']
            price = making_order['price']
            making_player.update_holdings(price, volume, making_order['is_bid'], making_order['asset_name'])
            taking_player.update_holdings(price, volume, taking_order['is_bid'], taking_order['asset_name'])

            making_player.save()
        taking_player.save()

        confirm_msg = {
            'type': 'confirm_trade',
            'payload': {
                'timestamp': timestamp,
                'asset_name': asset_name,
                'taking_order': taking_order,
                'making_orders': making_orders,
            }
        }
        self.send('chan', confirm_msg)
    
    def confirm_cancel(self, order_dict):
        '''send an order cancel confirmation to the frontend. this function is called
        by the exchange when an order is successfully canceled'''
        player = self._get_player(order_dict['pcode'])
        if order_dict['is_bid']:
            player.available_cash += order_dict['price'] * order_dict['volume']
        else:
            player.available_assets[order_dict['asset_name']] += order_dict['volume']
        player.save()

        confirm_msg = {
            'type': 'confirm_cancel',
            'payload': order_dict,
        }
        self.send('chan', confirm_msg)
    
    def _send_error(self, pcode, message):
        '''send an error message to a player'''
        error_msg = {
            'type': 'error',
            'payload': {
                'pcode': pcode,
                'message': message,
            }
        }
        self.send('chan', error_msg)

class Player(BasePlayer):

    settled_assets = JSONField()
    available_assets = JSONField()

    settled_cash   = models.IntegerField()
    available_cash   = models.IntegerField()

    def set_endowment(self, asset_endowments, cash_endowment):
        self.settled_assets = asset_endowments
        self.available_assets = asset_endowments

        self.settled_cash   = cash_endowment
        self.available_cash   = cash_endowment
        self.save()

    def update_holdings(self, price, volume, is_bid, asset_name):
        '''update this player's holdings (cash and assets) after a trade occurs.
        params price, volume and is_bid reflect the transacted order belonging to this player'''
        if is_bid:
            self.available_assets[asset_name] += volume
            self.settled_assets[asset_name] += volume
            
            self.available_cash -= price * volume
            self.settled_cash -= price * volume
        else:
            self.available_assets[asset_name] -= volume
            self.settled_assets[asset_name] -= volume
            
            self.available_cash += price * volume
            self.settled_cash += price * volume

    # jsonfield is broken, it needs this special hack to get saved correctly
    # for more info see https://github.com/Leeps-Lab/otree-redwood/blob/master/otree_redwood/models.py#L167
    def save(self, *args, **kwargs):
        super().save(*args, **kwargs)
        if self.pk is not None:
            update_fields = kwargs.get('update_fields')
            json_fields = {}
            for field in self._meta.get_fields():
                if isinstance(field, JSONField) and (update_fields is None or field.attname in update_fields):
                    json_fields[field.attname] = getattr(self, field.attname)
            self.__class__._default_manager.filter(pk=self.pk).update(**json_fields)
