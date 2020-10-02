from otree.models import Session
from otree.session import SESSION_CONFIGS_DICT
from otree.common import get_models_module
from django.template.response import TemplateResponse
from django.http import HttpResponse
from django.shortcuts import get_object_or_404
from django.urls import path
import vanilla
from importlib import import_module

from .models import Group as MarketGroup
from .output import DefaultJSONMarketOutputGenerator

def make_export_path(config_name, output_generator_class):
    class MarketOutputExportView(vanilla.View):

        def get(self, request, *args, **kwargs):
            session = get_object_or_404(Session, code=kwargs['session_code'])
            output_generator = output_generator_class(session)

            response = HttpResponse(content_type=output_generator.get_mime_type())
            filename = output_generator.get_filename()
            response['Content-Disposition'] = f'attachment; filename="{filename}"'
            output_generator.write_output(response)

            return response
    
    url_pattern = f'markets_export/{config_name}/{output_generator_class.__name__}/<str:session_code>/'
    url_name = f'markets_export_{config_name}_{output_generator_class.__name__}'
    return path(url_pattern, MarketOutputExportView.as_view(), name=url_name)

def make_sessions_view(session_config, output_generators):
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
                'session_config': session_config,
                'sessions': sessions,
                'output_types': [
                    {
                        'url_name': f'markets_export_{session_config["name"]}_{generator_class.__name__}',
                        'link_text': generator_class.download_link_text,
                    }
                    for generator_class in output_generators
                ]
            }
            return TemplateResponse(request, 'otree_markets/MarketOutputSessionsView.html', context)

    return MarketOutputSessionsView

markets_export_views = []
markets_export_urls = []
for session_config in SESSION_CONFIGS_DICT.values():
    # if there aren't any markets apps in the app sequence, don't make an output page for them
    if not any(issubclass(get_models_module(app_name).Group, MarketGroup) for app_name in session_config['app_sequence']):
        continue

    # output_generators is a list of subclasses of output.BaseMarketOutputGenerator
    # if no output generators are provided by an app, just include the default json generator
    output_generators = []
    for app_name in session_config['app_sequence']:
        try:
            output_module = import_module(f'{app_name}.output')
            output_generators.extend(output_module.output_generators)
        except (ImportError, AttributeError):
            continue
    if not output_generators:
        output_generators.append(DefaultJSONMarketOutputGenerator)

    markets_export_views.append(make_sessions_view(session_config, output_generators))
    for output_generator in output_generators:
        markets_export_urls.append(make_export_path(session_config['name'], output_generator))
