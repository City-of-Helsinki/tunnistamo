from django.core.management.base import BaseCommand
from ruamel.yaml import YAML

from auth_backends.models import SuomiFiAccessLevel, SuomiFiUserAttribute


class Command(BaseCommand):
    help = 'Create Suomi.fi user attribute groups from YAML file'

    def add_arguments(self, parser):
        parser.add_argument('-l', '--load', action='store', dest='yaml', required=True,
                            help='YAML file with attribute mappings')

    def handle(self, *args, **options):
        def flatten(l):
            return [item for sublist in l for item in sublist]

        yaml = YAML()
        with open(options['yaml']) as yamlfile:
            data = yaml.load(yamlfile)

        for attribute in flatten(data['attributes'].values()):
            SuomiFiUserAttribute.objects.update_or_create(
                friendly_name=attribute['friendly_name'],
                uri=attribute['uri'],
                name=attribute['name'],
                description=attribute['description']
            )

        for level, details in data['access_levels'].items():
            access_level, created = SuomiFiAccessLevel.objects.update_or_create(shorthand=level)
            for language, name in details['name'].items():
                access_level.set_current_language(language)
                access_level.name = name
            for language, description in details['description'].items():
                access_level.set_current_language(language)
                access_level.description = description
            for attribute in flatten(details['fields']):
                access_level.attributes.add(SuomiFiUserAttribute.objects.get(friendly_name=attribute['friendly_name']))
            access_level.save()
