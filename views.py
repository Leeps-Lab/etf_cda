from otree.models import Session
from otree.session import SESSION_CONFIGS_DICT
from otree.common import get_models_module
from django.template.response import TemplateResponse
from django.http import HttpResponse, JsonResponse
from django.shortcuts import get_object_or_404
from django.urls import path
from importlib import import_module
import vanilla
import csv
import datetime
from .models import Group as MarketGroup
from .exchange.base import OrderStatusEnum

def make_json_export_path(session_config):
    class MarketOutputJsonExportView(vanilla.View):

        def get(self, request, *args, **kwargs):
            session = get_object_or_404(Session, code=kwargs['session_code'])
            group_data = []
            for subsession in session.get_subsessions():
                for group in subsession.get_groups():
                    if not isinstance(group, MarketGroup):
                        continue
                    data = self.get_group_data(group)
                    if data['exchange_data']:
                        group_data.append(data)

            response = JsonResponse(group_data, safe=False)
            filename = '{} Market Data - session {} (accessed {}).json'.format(
                session_config['display_name'],
                kwargs['session_code'],
                datetime.date.today().isoformat()
            )
            response['Content-Disposition'] = f'attachment; filename="{filename}"'
            return response
        
        def order_to_output_dict(self, order):
            return {
                'time_entered': order.timestamp,
                'price': order.price,
                'volume': order.volume,
                'is_bid': order.is_bid,
                'pcode': order.pcode,
                'traded_volume': order.traded_volume,
                'id': order.id,
                'status': OrderStatusEnum(order.status).name,
                'time_inactive': order.time_inactive,
            }
        
        def trade_to_output_dict(self, trade):
            return {
                'timestamp': trade.timestamp,
                'taking_order_id': trade.taking_order.id,
                'making_order_ids': [ o.id for o in trade.making_orders.all() ],
            }
        
        def get_group_data(self, group: MarketGroup):
            exchange_data = {}
            exchange_query = group.exchanges.all().prefetch_related('orders', 'trades')
            for exchange in exchange_query:
                orders = [self.order_to_output_dict(e) for e in exchange.orders.all()]
                trades = [self.trade_to_output_dict(e) for e in exchange.trades.all()]
                exchange_data[exchange.asset_name] = {
                    'orders': orders,
                    'trades': trades,
                }
            return {
                'round_number': group.round_number,
                'id_in_subsession': group.id_in_subsession,
                'exchange_data': exchange_data,
            }
    
    app_name = session_config['name']
    url_pattern = f'markets_export_json/{app_name}/<str:session_code>/'
    url_name = f'markets_export_json_{app_name}'
    return path(url_pattern, MarketOutputJsonExportView.as_view(), name=url_name)

def make_csv_export_path(session_config, csv_gen_func):
    class MarketOutputCsvExportView(vanilla.View):

        def get(self, request, *args, **kwargs):
            session = get_object_or_404(Session, code=kwargs['session_code'])

            response = HttpResponse(content_type='text/csv')
            filename = '{} Market Data (accessed {}).csv'.format(
                session_config['display_name'],
                datetime.date.today().isoformat()
            )
            response['Content-Disposition'] = f'attachment; filename="{filename}"'

            w = csv.writer(response)
            w.writerows(csv_gen_func(session))

            return response
    
    app_name = session_config['name']
    url_pattern = f'markets_export_csv/{app_name}/<str:session_code>/'
    url_name = f'markets_export_csv_{app_name}'
    return path(url_pattern, MarketOutputCsvExportView.as_view(), name=url_name)

def make_sessions_view(session_config, includes_csv_output):
    class MarketOutputSessionsView(vanilla.View):
        url_name = f'markets_sessions_{session_config["name"]}'
        url_pattern = f'^{url_name}/$'
        display_name = f'{session_config["display_name"]} Trading Output'

        def get(request, *args, **kwargs):
            # this is pretty bad ..
            # we can't just filter on session config since changing any params means that the session's config
            # will be different from the config in SESSION_CONFIGS_DICT. what we want to do is filter on config['name']
            # but we can't do that because Session.config is that weird PickleField thing which is stored as base64 text in the DB.
            #
            # the only option I came up with is to load EVERY session into memory and filter by config['name'] in python. the values_list
            # thing is to avoid loading all of every session, this way we just get the config and id for every session, then we can
            # go back and query again for the full session objects we want. this is probably real slow and will not scale well.
            # if someone smarter than me and better at database is reading this, please fix this.
            session_ids = (
                session_id
                for config, session_id
                in Session.objects.values_list('config', 'id')
                if config['name'] == session_config['name']
            )
            sessions = Session.objects.filter(id__in=session_ids)
            context = {
                'sessions': sessions,
                'session_config': session_config,
                'includes_csv_output': includes_csv_output,
            }
            return TemplateResponse(request, 'otree_markets/MarketOutputSessionsView.html', context)

    return MarketOutputSessionsView

markets_export_views = []
markets_export_urls = []
for session_config in SESSION_CONFIGS_DICT.values():
    # if there aren't any markets apps in the app sequence, don't make an output page for them
    if not any(issubclass(get_models_module(app_name).Group, MarketGroup) for app_name in session_config['app_sequence']):
        continue

    # this isn't right, need to fix later
    csv_gen_func = None
    for app_name in session_config['app_sequence']:
        try:
            output_module = import_module(f'{app_name}.output')
            csv_gen_func = output_module.get_csv_output
        except (ImportError, AttributeError):
            pass

    includes_csv_output = csv_gen_func is not None
    markets_export_views.append(make_sessions_view(session_config, includes_csv_output))
    markets_export_urls.append(make_json_export_path(session_config))
    if includes_csv_output:
        markets_export_urls.append(make_csv_export_path(session_config, csv_gen_func))
