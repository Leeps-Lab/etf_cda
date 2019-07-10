from otree.api import (
    models, widgets, BaseConstants, BaseSubsession, BaseGroup, BasePlayer,
    Currency as c, currency_range
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
    pass


class Player(BasePlayer):
    pass
