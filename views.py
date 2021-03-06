import datetime

from inspect import currentframe, getframeinfo

from django.apps import apps
from django.contrib import messages
from django.core.exceptions import FieldError
from django.db.models import Q
from django.forms import ValidationError
from django.http import QueryDict
from django.shortcuts import render

from .models import Vista

def make_vista(user, queryset, querydict=QueryDict(), vista_name='', make_default=False, settings = {}, do_save=True ):

    def make_type(field_name, field_value):

        try:
            field_type = settings['fields'][field_name]['type']
        except KeyError:
            field_type = ''

        if field_type in ['date', 'DateField', 'DateTimeField']:
            try:
                field_value = datetime.date.fromisoformat(field_value)
            except ValueError:
                try:
                    field_value = datetime.datetime.strptime(field_value, '%Y%m%d')
                except ValueError:
                    field_value = datetime.datetime.now()
        elif field_type in ['boolean', 'BooleanField']:
            if field_value:
                if field_value in ['False', 'false', '0']:
                    field_value = False
                else:
                    field_value = True
            else:
                field_value = False

        if field_value == '[None]':
            field_value = None
        elif '[[None]]' in str(field_value):
            field_value = field_value.replace('[[None]]', '[None]')

        return field_value


    def queryset_filter(queryset, querydict, indx = None):

        fieldnamekey = 'filter__fieldname'
        opkey = 'filter__op'
        valuekey = 'filter__value'

        if indx is not None:
            [fieldnamekey, opkey, valuekey] = [key + '__' + str(indx) for key in [fieldnamekey, opkey, valuekey]]

        if fieldnamekey in querydict and opkey in querydict:
            filter__fieldname = querydict.get(fieldnamekey)
            filter__op = querydict.get(opkey)

            filter__value = False

            if valuekey in querydict:
                filter__value = querydict.get(valuekey)
                filter__value = make_type(filter__fieldname, filter__value)

            if filter__op in ['in', 'range']:
                filter__value = querydict.getlist(valuekey)
                for fidx, fval in enumerate(filter__value):
                    filter__value[fidx] = make_type(filter__fieldname, fval)

            built_query = { filter__fieldname + '__' + filter__op: filter__value }
            try:
                queryset = queryset.filter(**built_query)
            except (ValueError, ValidationError) as e:
                print('Error ', e.__class__.__name__,  e, 'for query: ', built_query)
                queryset = queryset.model.objects.all()
            except (FieldError, ValidationError) as e:
                print('Error ', e.__class__.__name__,  e, 'for query: ', built_query)
                queryset = queryset.model.objects.all()
        return queryset

    if vista_name == '':
        vista_name = querydict.get('vista_name')
        if vista_name is None:
            vista_name = ''


    if 'filter__fieldname' in querydict and 'filter__op' in querydict:
        queryset = queryset_filter(queryset, querydict)


    max_search_keys=10
    if 'max_search_keys' in settings:
        max_search_keys=settings['max_search_keys']


    for indx in range(max_search_keys):
        if 'filter__fieldname__' + str(indx) in querydict and 'filter__op__' + str(indx) in querydict:
            queryset = queryset_filter(queryset, querydict, indx)

    if 'combined_text_search' in querydict and querydict.get('combined_text_search') > '':

        text_query = None
        text_fields_available = [ key for key, value in settings['fields'].items() if 'available_for' in value and 'quicksearch' in value['available_for']]

        if text_fields_available > []:
            combined_text_search = querydict.get('combined_text_search')
            combined_text_fields = text_fields_available
            if 'combined_text_fields' in querydict and querydict.getlist('combined_text_fields'):
                combined_text_fields = list(set(combined_text_fields).intersection(settings['text_fields_avaiable']))

            for fieldname in combined_text_fields:
                if text_query is not None:
                    text_query = text_query | Q(**{fieldname + '__contains':combined_text_search})
                else:
                    text_query = Q(**{fieldname + '__contains':combined_text_search})

        if text_query is not None:
            try:
                queryset = queryset.filter(text_query)
            except FieldError as e:
                print('Field Error at Combined Text Query:', e)
                print(text_query)

    order_by = querydict.getlist('order_by')

    try:
        queryset = queryset.order_by(*order_by)
    except FieldError as e:
        print('Field Error at Order By:', e)

    queryset = queryset.distinct()

    if do_save:
        try:
            vista, created = Vista.objects.get_or_create(name=vista_name, user=user)
        except Vista.MultipleObjectsReturned:
            vista = Vista.objects.filter(name=vista_name, user=user)[0]
            Vista.objects.filter(name=vista_name, user=user).exclude(pk=vista.pk).delete()

        vista.name = vista_name
        vista.user = user
        vista.modified = datetime.date.today()
        vista.is_default = make_default
        vista.filterstring = querydict.urlencode()
        vista.model_name = queryset.model._meta.label_lower

        vista.save()

    return {'querydict': querydict, 'queryset':queryset}


# call this function in a try/except block to catch DoesNotExist.

def get_latest_vista(user, queryset, defaults={}, settings={}):
    model_name = queryset.model._meta.label_lower
    try:
        print('Trying to retrieve latest for user')
        vista = Vista.objects.filter(user=user, model_name=model_name).latest('modified')
        return make_vista(user, queryset, QueryDict(vista.filterstring), vista.name, False, settings, True )
    except Vista.DoesNotExist:
        return default_vista( user, queryset, defaults, settings )


# call this function in a try/except block to catch DoesNotExist.
# def make_vista(user, queryset, querydict, vista_name='', make_default=False, settings = {} ):

def retrieve_vista(user, queryset, model_name, vista_name, settings = {} ):

    try:
        vista = Vista.objects.filter(user=user, name=vista_name, model_name=model_name).latest('modified')
    except:
        vista = Vista.objects.all()

    return make_vista(user, queryset, QueryDict(vista.filterstring), vista_name, False, settings, True )

def get_global_vista(request, settings, queryset, defaults):

    vista = Vista.objects.filter(is_global_default=True).latest('modified')
    return make_vista(request, settings, queryset, defaults, vista)

# does not return anything.  Most likely you'll want to call get_latest_vista after calling this
def delete_vista(request):

    vista_name = request.POST.get('vista_name') if 'vista_name' in request.POST else ''
    vista = Vista.objects.filter(name=vista_name, user=request.user).delete()

def default_vista(user, queryset, defaults={}, settings={}):
    model_name = queryset.model._meta.label_lower
    try:
        print('Trying to retrieve latest is_default for user')
        vista = Vista.objects.filter(user=user, model_name=model_name, is_default=True).latest('modified')
        return make_vista(user, queryset, QueryDict(vista.filterstring), vista.name, False, settings, True )
    except Vista.DoesNotExist:
        try:
            print('Trying to retrieve latest global_default')
            vista = Vista.objects.filter(model_name=model_name, is_global_default=True).latest('modified')
            return make_vista(user, queryset, QueryDict(vista.filterstring), vista.name, False, settings, True )
        except Vista.DoesNotExist:
            print('Trying defaults from settings')
            return make_vista(
                user,
                queryset,
                defaults,
                '',
                True,
                settings
            )


def make_vista_fields(model, field_names=[]):

    vista_fields = {}

    if field_names == []:
        field_names = [ field.name for field in model._meta.get_fields() ]

    for field_name in field_names:
        print('tp 2259h55',)
        chained_label = ''
        if '__' in field_name:
            chain_model = model
            chain = field_name.split('__')
            for l in range( len( chain ) -1 ):
                try:
                    print('tp 2259i03', chain[l])
                    chained_label = chained_label + chain_model._meta.get_field(chain[l]).verbose_name.title() + ' '
                except AttributeError as e:
                    chained_label = chained_label + chain_model._meta.get_field(chain[l]).name.title() + ' '

                chain_model = apps.get_model(app_label=model._meta.app_label, model_name=chain_model._meta.get_field(chain[l]).related_model.__name__)
                model_field = chain_model._meta.get_field(chain[l + 1])

        else:
            model_field = model._meta.get_field(field_name)

        vista_fields[field_name] = {
            'type':type(model_field).__name__,
        }

        if vista_fields[field_name]['type'] == 'ManyToManyField':
            vista_fields[field_name]['label'] = chained_label + model_field.related_model._meta.verbose_name.title()
            vista_fields[field_name]['queryset'] = model_field.related_model.objects.all()
            vista_fields[field_name]['available_for'] = [
                    'fieldsearch',
                    'columns',
                ]
            vista_fields[field_name]['operators'] = [
                    ('in', 'is in')
                ]

            try:
                vista_fields[field_name]['label'] = model_field.verbose_name.title()
            except AttributeError as e:
                print('tp 224hc38', e, f"{getframeinfo(currentframe()).filename}:{getframeinfo(currentframe()).lineno}")
                pass

        elif vista_fields[field_name]['type'] == 'ManyToOneField':
            vista_fields[field_name]['label'] = chained_label + model_field.related_model._meta.verbose_name.title()
            vista_fields[field_name]['queryset'] = model_field.related_model.objects.all()
            vista_fields[field_name]['available_for'] = [
                    'fieldsearch',
                    'columns',
                ]
            vista_fields[field_name]['operators'] = [
                    ('in', 'has')
                ]

            try:
                vista_fields[field_name]['label'] = chained_label + model_field.related_name.title()
            except AttributeError as e:
                print('tp 224hc35', e, f"{getframeinfo(currentframe()).filename}:{getframeinfo(currentframe()).lineno}")
                pass

        elif vista_fields[field_name]['type'] == 'ForeignKey':
            vista_fields[field_name]['label'] = chained_label + model_field.verbose_name.title()
            vista_fields[field_name]['queryset'] = model_field.related_model.objects.all()
            vista_fields[field_name]['available_for'] = [
                    'fieldsearch',
                    'order_by',
                    'columns'
                ]
            vista_fields[field_name]['operators'] = [
                    ('in', 'is in')
                ]

        # now, if not a Rel or ForeignKey
        else:
            vista_fields[field_name]['label'] = chained_label + model_field.verbose_name.title()
            if model_field.choices is not None:
                vista_fields[field_name]['choices'] = model_field.choices
                vista_fields[field_name]['operators'] = [('in', 'is in')]

            if vista_fields[field_name]['type'] in [
                'char',
                'CharField',
                'EmailField',
                'SlugField',
                'URLField',
                'ImageField',
            ]:
                vista_fields[field_name]['available_for'] = [
                    'quicksearch',
                    'fieldsearch',
                    'order_by',
                    'columns'
                ]
                if not 'operators' in vista_fields[field_name]:
                    vista_fields[field_name]['operators'] = [
                        ('icontains', 'contains'),
                        ('iexact', 'is'),
                    ]
            elif vista_fields[field_name]['type'] in [
                'TextField',
            ]:
                vista_fields[field_name]['available_for'] = [
                    'quicksearch',
                    'fieldsearch',
                ]
                vista_fields[field_name]['operators'] = [
                    ('icontains', 'contains'),
                ]
            elif vista_fields[field_name]['type'] in [
                'BooleanField',
            ]:
                vista_fields[field_name]['available_for'] = [
                    'fieldsearch',
                ]
                vista_fields[field_name]['operators'] = [
                    ('exact','is'),
                ]
                vista_fields[field_name]['choices'] = [
                    (True,"True"),
                    (False,"False"),
                ]

            elif vista_fields[field_name]['type'] in [
                'int',
                'AutoField',
                'BigAutoField',
                'BigIntegerField',
                'BinaryField',
                'DecimalField',
                'DurationField',
                'FloatField',
                'IntegerField',
                'PositiveBigIntegerField',
                'PositiveIntegerField',
                'PositiveSmallIntegerField',
                'SmallAutoField',
                'SmallIntegerField',
            ]:
                vista_fields[field_name]['available_for'] = [
                    'fieldsearch',
                    'order_by',
                    'columns'
                ]
                if not 'operators' in vista_fields[field_name]:
                    vista_fields[field_name]['operators'] = [
                        ('exact', 'is'),
                        ('gt', 'greater than'),
                        ('lt', 'less than'),
                    ]
            elif vista_fields[field_name]['type'] in [
                'date',
                'DateField',
                'DateTimeField',
                'TimeField',
            ]:
                vista_fields[field_name]['available_for'] = [
                    'fieldsearch',
                    'order_by',
                    'columns'
                ]
                if not 'operators' in vista_fields[field_name]:
                    vista_fields[field_name]['operators'] = [
                        ('exact', 'is'),
                        ('gt', 'greater than'),
                        ('lt', 'less than'),
                    ]

        if 'id' in vista_fields:
            del vista_fields['id']


    # AutoField
    # BigAutoField
    # BigIntegerField
    # BinaryField
    # BooleanField
    # CharField
    # DateField
    # DateTimeField
    # DecimalField
    # DurationField
    # EmailField
    # FileField
    #     FileField and FieldFile
    # FilePathField
    # FloatField
    # GenericIPAddressField
    # ImageField
    # IntegerField
    # JSONField
    # PositiveBigIntegerField
    # PositiveIntegerField
    # PositiveSmallIntegerField
    # SlugField
    # SmallAutoField
    # SmallIntegerField
    # TextField
    # TimeField
    # URLField
    # UUIDField

    return vista_fields

def vista_context_data(settings, querydict):

    context_data={}

    order_by_fields_forward = [{ 'name':key, 'label':value['label'] } for key, value in settings['fields'].items() if 'order_by' in value['available_for'] ]
    order_by_fields_reverse = [{ 'name':'-' + key, 'label':'-' + value['label'] } for key, value in settings['fields'].items() if 'order_by' in value['available_for'] ]

    context_data['order_by_fields_available'] = order_by_fields_forward + order_by_fields_reverse

    context_data['filter_fields_available'] = []

    for key, value in settings['fields'].items():

        if 'fieldsearch' in value['available_for']:
            filter_field = {
                'name': key,
                'label': value['label'],
                'type': value['type'] if 'type' in value else '',
            }

            for subkey in ['type', 'queryset', 'choices', 'operators']:
                if subkey in value:
                    filter_field[subkey] = value[subkey]

            if not 'operators' in filter_field:
                filter_field['operators'] = [('exact', 'is')]

            context_data['filter_fields_available'].append(filter_field)

    context_data['columns_available'] = [{ 'name':key, 'label':value['label'] } for key, value in settings['fields'].items() if 'columns' in value['available_for'] ]

    context_data['labels'] = { key: value['label'] for key, value in settings['fields'].items() if 'columns' in value['available_for'] }

    context_data['filter'] = []

    for indx in range( settings['max_search_keys']):
        cdfilter = {}
        cdfilter['fieldname'] = querydict.get('filter__fieldname__' + str(indx)) if 'filter__fieldname__' + str(indx) in querydict else ''
        cdfilter['op'] = querydict.get('filter__op__' + str(indx) ) if 'filter__op__' + str(indx) in querydict else ''
        cdfilter['value'] = querydict.get('filter__value__' + str(indx)) if 'filter__value__' + str(indx) in querydict else ''
        if cdfilter['op'] in ['in', 'range']:
            cdfilter['value'] = querydict.getlist('filter__value__' + str(indx)) if 'filter__value__' + str(indx) in querydict else []
        context_data['filter'].append(cdfilter)

    if 'order_by' in querydict:
        context_data['order_by'] = querydict.getlist('order_by')

    if 'show_columns' in querydict:
        context_data['show_columns'] = querydict.getlist('show_columns')

    if not 'order_by' in context_data:
        context_data['order_by'] = []

    if 'combined_text_search' in querydict:
        context_data['combined_text_search'] = querydict.get('combined_text_search')

    if not 'combined_text_search' in context_data:
        context_data['combined_text_search'] = ''


    return context_data
