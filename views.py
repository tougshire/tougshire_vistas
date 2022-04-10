import datetime

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

def get_latest_vista(request, settings, queryset, defaults):

    vista = Vista.objects.filter(user=request.user).latest('modified')

    return make_vista(request, settings, queryset, defaults, vista)


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

def vista_fields(model, rels=False):
    fields = {}

    for field in model._meta.get_fields():
        fields[field.name] = {
            'type':type(field).__name__,
            'available_for':[]
        }
        if fields[field.name]['type'][-3:] == 'Rel':
            if rels:
                fields[field.name]['label'] = field.related_model._meta.verbose_name.title()
                fields[field.name]['queryset'] = field.related_model.objects.all()
                fields[field.name]['available_for'] = [
                    'fieldsearch',
                    'columns'
                ]
        elif fields[field.name]['type'] == 'ForeignKey':
            fields[field.name]['label'] = field.verbose_name.title()
            fields[field.name]['queryset'] = field.related_model.objects.all()
            fields[field.name]['available_for'] = [
                'fieldsearch',
                'order_by',
                'columns'
            ]

        else:
            fields[field.name]['label'] = field.verbose_name.title()
            if field.choices is not None:
                fields[field.name]['choices'] = field.choices
            fields[field.name]['available_for'] = [
                'fieldsearch',
                'order_by',
                'columns'
            ]

        if 'id' in fields:
            del fields['id']

    return fields

def vista_context_data(settings, querydict):

    context_data={}

    context_data['order_by_fields_available'] = [{ 'name':key, 'label':value['label'] } for key, value in settings['fields'].items() if 'order_by' in value['available_for'] ]

    context_data['filter_fields_available'] = [{ 'name':key, 'label':value['label'], 'type':settings['fields'][key]['type'] if 'type' in settings['fields'][key] else '', 'queryset':settings['fields'][key]['queryset'] if 'queryset' in settings['fields'][key] else '', 'choices':settings['fields'][key]['choices'] if 'choices' in settings['fields'][key] else '' } for key, value in settings['fields'].items() if 'fieldsearch' in value['available_for'] ]

    context_data['columns_available'] = [{ 'name':key, 'label':value['label'] } for key, value in settings['fields'].items() if 'columns' in value['available_for'] ]

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

    if not 'order_by' in context_data:
        context_data['order_by'] = []

    if 'combined_text_search' in querydict:
        context_data['combined_text_search'] = querydict.get('combined_text_search')

    if not 'combined_text_search' in context_data:
        context_data['combined_text_search'] = ''


    return context_data
