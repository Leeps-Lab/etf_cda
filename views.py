from otree.models import Session
from otree.session import SESSION_CONFIGS_DICT
from django.template.response import TemplateResponse
from django.http import HttpResponse, JsonResponse
from django.shortcuts import get_object_or_404
from django.urls import path
from importlib import import_module
import vanilla
import csv
import datetime
from .models import Group as MarketGroup

def make_json_export_path(session_config):
    class MarketOutputJsonExportView(vanilla.View):

        def get(self, request, *args, **kwargs):
            session = get_object_or_404(Session, code=kwargs['session_code'])
            group_data = []
            for subsession in session.get_subsessions():
                for group in subsession.get_groups():
                    group_data.append(self.get_group_data(group))

            response = JsonResponse(group_data, safe=False)
            filename = '{} Market Data (accessed {}).json'.format(
                session_config['display_name'],
                datetime.date.today().isoformat()
            )
            response['Content-Disposition'] = f'attachment; filename="{filename}"'
            return response
        
        def get_group_data(self, group: MarketGroup):
            exchange_data = {}
            exchange_query = group.exchanges.all().prefetch_related('orders', 'trades')
            for exchange in exchange_query:
                orders = [e.as_dict() for e in exchange.orders.all()]
                trades = [
                    {
                        'timestamp': e.timestamp.timestamp(),
                        'taking_order': e.taking_order.id,
                        'making_orders': [i.id for i in e.making_orders.all()],
                    }
                    for e in exchange.trades.all()
                ]
                exchange_data[exchange.asset_name] = {
                    'orders': orders,
                    'trades': trades,
                }
            return {
                'id_in_subsession': group.id_in_subsession,
                'exchange_data': exchange_data,
            }
    
    app_name = session_config['name']
    url_pattern = f'markets_export_json/{app_name}/<str:session_code>/'
    url_name = f'markets_export_json_{app_name}'
    return path(url_pattern, MarketOutputJsonExportView.as_view(), name=url_name)

def make_csv_export_path(session_config):
    class MarketOutputCsvExportView(vanilla.View):

        def get(self, request, *args, **kwargs):
            session = get_object_or_404(Session, code=kwargs['session_code'])
            tables = []
            for subsession in session.get_subsessions():
                for group in subsession.get_groups():
                    tables.append(self.get_output_table(group))

            response = HttpResponse(content_type='text/csv')
            filename = '{} Market Data (accessed {}).csv'.format(
                self.session_config['display_name'],
                datetime.date.today().isoformat()
            )
            response['Content-Disposition'] = f'attachment; filename="{filename}"'

            w = csv.writer(response)
            w.writerow(self.get_output_table_header())
            for rows in tables:
                w.writerows(rows)

            return response

        def get_output_table_header(self):
            return [
                'timestamp',
                'asset_name',
            ]
        
        def get_output_table(self, group):
            raise NotImplementedError()
    
    app_name = session_config['name']
    url_pattern = f'markets_export_csv/{app_name}/<str:session_code>/'
    url_name = f'markets_export_csv_{app_name}'
    return path(url_pattern, MarketOutputCsvExportView.as_view(), name=url_name)

def make_sessions_view(session_config):
    class MarketOutputSessionsView(vanilla.View):
        url_name = f'markets_sessions_{session_config["name"]}'
        url_pattern = f'^{url_name}/$'
        display_name = f'{session_config["display_name"]} Trading Output'

        def get(request, *args, **kwargs):
            sessions = Session.objects.filter(config=session_config)
            context = {
                'sessions': sessions,
                'session_config': session_config,
            }
            return TemplateResponse(request, 'otree_markets/MarketOutputSessionsView.html', context)

    return MarketOutputSessionsView

markets_export_views = []
markets_export_urls = []
for session_config in SESSION_CONFIGS_DICT.values():
    app_name = session_config['name']
    try:
        models_module = import_module(f'{app_name}.models')
        group_cls = models_module.Group
    except (ImportError, AttributeError):
        continue
    if issubclass(group_cls, MarketGroup):
        markets_export_views.append(make_sessions_view(session_config))
        export_urls.append(make_csv_export_path(session_config))
        export_urls.append(make_json_export_path(session_config))
