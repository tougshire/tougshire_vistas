import datetime
import json, urllib
from xml.dom import ValidationErr

from django.contrib import messages
from django.core.exceptions import FieldError
from django.db.models import Q
from django.forms import ValidationError
from django.http import QueryDict
from django.shortcuts import render

from .models import Vista

def make_vista(user, queryset, querydict=QueryDict(), vista_name='', make_default=False, settings = {}, do_save=True ):

    def make_type(field_name, field_value):

        field_type=''
        if 'field_types' in settings and field_name in settings['field_types']:
            field_type = settings['field_types'][field_name]
            if field_type == 'date':
                try:
                    field_value = datetime.date.fromisoformat(field_value)
                except ValueError:
                    try:
                        field_value = datetime.datetime.strptime(field_value, '%Y%m%d')
                    except ValueError:
                        field_value = datetime.datetime.now()
            elif field_type == 'boolean':
                if field_value:
                    field_value = True
                else:
                    field_value = False

        if field_value == '[None]':
            field_value = None
        elif '[[None]]' in str(field_value):
            field_value = field_value.replace('[[None]]', '[None]')

        print('tp m3ah43 returning ', field_value, ' for ', field_name, ': ', field_type)
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
                for fval in filter__value:
                    fval = make_type(filter__fieldname, fval)

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

    if 'combined_text_search' in querydict and querydict.get('combined_text_search') > '' and 'text_fields_available' in settings and settings['text_fields_available']:
        combined_text_search = querydict.get('combined_text_search')
        combined_text_fields = settings['text_fields_available']
        if 'combined_text_fields' in querydict and querydict.getlist('combined_text_fields'):
            combined_text_fields = list(set(combined_text_fields).intersection(settings['text_fields_avaiable']))

        text_query = None
        for fieldname in combined_text_fields:
            if text_query is not None:
                text_query = text_query | Q(**{fieldname + '__contains':combined_text_search})
            else:
                text_query = Q(**{fieldname + '__contains':combined_text_search})

        queryset = queryset.filter(text_query)

    order_by = querydict.getlist('order_by')
    queryset = queryset.order_by(*order_by)

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
        print('tp m39843')
        vista = Vista.objects.filter(user=user, model_name=model_name, is_default=True).latest('modified')
        return make_vista(user, queryset, QueryDict(vista.filterstring), vista.vista_name, False, settings, True )
    except Vista.DoesNotExist:
        try:
            print('tp m39844')
            vista = Vista.objects.filter(user=user,  model_name=model_name, is_global_default=True).latest('modified')
            return make_vista(user, queryset, QueryDict(vista.filterstring), vista.vista_name, False, settings, True )
        except Vista.DoesNotExist:
            print('tp m39845')
            return make_vista(
                user,
                queryset,
                QueryDict(urllib.parse.urlencode(defaults)),
                '',
                True,
                settings
            )


