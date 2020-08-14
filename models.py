from __future__ import annotations
from otree.api import (
    models, BaseSubsession, BasePlayer,
)
from otree_redwood.models import Group as RedwoodGroup
from jsonfield import JSONField
from django.utils import timezone
from django.contrib.contenttypes.fields import GenericRelation

from .exchange.cda_exchange import CDAExchange
from .exchange.base import Order, Trade

SINGLE_ASSET_NAME = 'A'
'''the name of the only asset when in single-asset mode'''

class Subsession(BaseSubsession):

    class Meta(BaseSubsession.Meta):
        abstract = True

    def asset_names(self):
        '''this method describes the asset structure of an experiment.
        if defined, it should return an array of names for each asset. one exchange will be created for each asset name
        represented in this array. if not defined, one exchange is created and the game is configured for a single asset'''
        return [SINGLE_ASSET_NAME]
    
    def create_exchanges(self):
        asset_names = self.asset_names()

        for group in self.get_groups():
            for name in asset_names:
                group.exchanges.create(asset_name=name)
        for player in self.get_players():
            player.set_endowments()

    def creating_session(self):
        self.create_exchanges()


class Group(RedwoodGroup):

    class Meta(RedwoodGroup.Meta):
        abstract = True

    exchange_class = CDAExchange
    '''the class used to create the exchanges for this group.
    change this property to swap out a different exchange implementation'''
    exchanges = GenericRelation(exchange_class)
    '''a queryset of all the exchanges associated with this group'''

    def get_remaining_time(self):
        '''gets the total amount of time remaining in the round'''
        period_length = self.period_length()
        if period_length is None:
            return None
        if self.ran_ready_function:
            return period_length - (timezone.now() - self.ran_ready_function).total_seconds()
        else:
            return period_length

    def get_player(self, pcode) -> Player:
        '''get a player object given its participant code. can be overridden to return None for certain pcodes.
        this may be useful for bots or other situations where fake players are needed'''
        for player in self.get_players():
            if player.participant.code == pcode:
                return player
        raise ValueError('invalid player code: "{}"'.format(pcode))

    def _on_enter_event(self, event):
        '''handle an enter message sent from the frontend'''
        enter_msg = event.value
        player = self.get_player(enter_msg['pcode'])
        asset_name = enter_msg['asset_name'] if enter_msg['asset_name'] else SINGLE_ASSET_NAME

        if player and not player.check_available(enter_msg['is_bid'], enter_msg['price'], enter_msg['volume'], asset_name):
            if enter_msg['is_bid']:
                self._send_error(enter_msg['pcode'], 'Order rejected: insufficient available cash')
            if not enter_msg['is_bid']:
                if len(self.subsession.asset_names()) == 1:
                    self._send_error(enter_msg['pcode'], 'Order rejected: insufficient available assets')
                else:
                    self._send_error(enter_msg['pcode'], 'Order rejected: insufficient available amount of asset {}'.format(asset_name))
            return

        exchange = self.exchanges.get(asset_name=asset_name)
        order_id = exchange.enter_order(
            enter_msg['price'],
            enter_msg['volume'],
            enter_msg['is_bid'],
            enter_msg['pcode'],
        )
    
    def _on_cancel_event(self, event):
        '''handle a cancel message sent from the frontend'''
        canceled_order_dict = event.value
        assert canceled_order_dict['pcode'] == event.participant.code, 'a player attempted to cancel another player\'s order'

        exchange = self.exchanges.get(asset_name=canceled_order_dict['asset_name'])
        exchange.cancel_order(canceled_order_dict['order_id'])

    def _on_accept_event(self, event):
        '''handle an immediate accept message sent from the frontend'''
        accepted_order_dict = event.value
        sender_pcode = event.participant.code
        player = self.get_player(sender_pcode)

        if player and not player.check_available(not accepted_order_dict['is_bid'], accepted_order_dict['price'], accepted_order_dict['volume'], accepted_order_dict['asset_name']):
            if accepted_order_dict['is_bid']:
                if len(self.subsession.asset_names()) == 1:
                    self._send_error(sender_pcode, 'Cannot accept order: insufficient available assets')
                else:
                    self._send_error(sender_pcode, 'Cannot accept order: insufficient available amount of asset {}'.format(accepted_order_dict['asset_name']))
            else:
                self._send_error(sender_pcode, 'Cannot accept order: insufficient available cash')
            return

        exchange = self.exchanges.get(asset_name=accepted_order_dict['asset_name'])
        exchange.accept_immediate(
            accepted_order_dict['order_id'],
            sender_pcode,
        )

    def confirm_enter(self, order: Order):
        '''send an order entry confirmation to the frontend. this function is called
        by the exchange when an order is successfully entered'''
        player = self.get_player(order.pcode)
        if player:
            player.update_holdings_available(order, False)
            player.save()

        self.send('confirm_enter', order.as_dict())

    def confirm_trade(self, trade: Trade):
        '''send a trade confirmation to the frontend. this function is called by the exchange when a trade occurs'''

        taking_player = self.get_player(trade.taking_order.pcode)
        for making_order in trade.making_orders.all():
            making_player = self.get_player(making_order.pcode)
            volume = making_order.traded_volume
            price = making_order.price
            if making_player:
                # need to update making players' available cash and assets
                # since these were adjusted when their order was entered, they need to be adjusted back so they're not double counted
                making_player.update_holdings_available(making_order, True)
                making_player.update_holdings_trade(price, volume, making_order.is_bid, trade.exchange.asset_name)
                making_player.save()
            if taking_player:
                taking_player.update_holdings_trade(price, volume, trade.taking_order.is_bid, trade.exchange.asset_name)
        if taking_player:
            taking_player.save()

        self.send('confirm_trade', trade.as_dict())
    
    def confirm_cancel(self, order: Order):
        '''send an order cancel confirmation to the frontend. this function is called
        by the exchange when an order is successfully canceled'''
        player = self.get_player(order.pcode)
        if player:
            player.update_holdings_available(order, True)
            player.save()

        self.send('confirm_cancel', order.as_dict())
    
    def _send_error(self, pcode, message):
        '''send an error message to a player'''
        self.send('error', {
            'pcode': pcode,
            'message': message,
        })


class Player(BasePlayer):

    class Meta(BasePlayer.Meta):
        abstract = True

    settled_assets = JSONField()
    available_assets = JSONField()

    settled_cash = models.IntegerField()
    available_cash = models.IntegerField()

    def asset_endowment(self):
        '''this method defines each player's initial endowment of each asset. in single-asset mode, this should return
        a single value for the single asset. in multiple-asset mode, this should return a dict mapping asset names to
        endowments'''
        raise NotImplementedError

    def cash_endowment(self):
        '''this method defines each player's initial cash endowment. it should return an integer for this
        player's endowment of cash'''
        raise NotImplementedError

    def set_endowments(self):
        '''sets all of this player's cash and asset endowments'''

        asset_endowment = self.asset_endowment()
        if not isinstance(asset_endowment, dict):
            asset_endowment = { SINGLE_ASSET_NAME: asset_endowment }

        self.settled_assets = asset_endowment
        self.available_assets = asset_endowment

        cash_endowment = self.cash_endowment()
        self.settled_cash = cash_endowment
        self.available_cash = cash_endowment

        self.save()
    
    def update_holdings_available(self, order, removed):
        '''update this player's available holdings (cash or assets) when they enter or remove an order.
        param order is the changed order belonging to this player.
        param removed is true when the changed order was removed and false when the changed order was added'''
        sign = 1 if removed else -1
        if order.is_bid:
            self.available_cash += order.price * order.volume * sign
        else:
            self.available_assets[order.exchange.asset_name] += order.volume * sign

    def update_holdings_trade(self, price, volume, is_bid, asset_name):
        '''update this player's holdings (cash and assets) after a trade occurs.
        params price, volume, is_bid, and asset_name reflect the type/amount that was transacted'''
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
    
    def check_available(self, is_bid, price, volume, asset_name):
        '''check whether this player has enough available holdings to enter an order'''
        if is_bid and self.available_cash < price * volume:
            return False
        elif not is_bid and self.available_assets[asset_name] < volume:
            return False
        return True

    # jsonfield doesn't work correctly with save-the-change, it needs this hack
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
