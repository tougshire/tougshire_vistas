import datetime
import json

from django.contrib import messages
from django.core.exceptions import FieldError
from django.db.models import Q
from django.http import QueryDict
from django.shortcuts import render

from .models import Vista

def make_vista(user, queryset, querydict, combined_text_search = '', combined_text_fields=[], order_by=[], vista_name='',  make_default=False, settings = {} ):

    def make_type(field, datatype):
        if datatype=='date':
            try:
                field = datetime.date.fromisoformat(field)
            except ValueError:
                try:
                    field = datetime.datetime.strptime(field, '%Y%m%d')
                except ValueError:
                    field = datetime.datetime.now()
        return field


    def queryset_filter(queryset, querydict, indx = None):

        fieldnamekey = 'filter__fieldname'
        opkey = 'filter__op'
        valuekey = 'filter__value'

        if indx is not None:
            [fieldnamekey, opkey, valuekey] = [key + '__' + str(indx) for key in [fieldnamekey, opkey, valuekey]]


        if fieldnamekey in querydict and opkey in querydict:
            filter__fieldname = querydict.get(fieldnamekey)
            filter__op = querydict.get(opkey)
            filter__value = querydict.get(valuekey)
            if filter__op in ['in']:
                filter__value = querydict.getlist(valuekey)
                for fval in filter__value:
                    if fval == '[None]':
                        fval = None
                    elif '[[None]]' in fval:
                        fval = fval.replace('[[None]]', '[None]')

            print('tp m36k11', filter__fieldname + '__' + filter__op,    filter__value)
            built_query = { filter__fieldname + '__' + filter__op: filter__value }
            queryset = queryset.filter(**built_query)


        return queryset

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

    try:
        vista, created = Vista.objects.get_or_create(name=vista_name, user=user)
    except Vista.MultipleObjectsReturned:
        vista = Vista.objects.filter(name=vista_name, user=user)[0]
        Vista.objects.filter(name=vista_name, user=user).exclude(pk=vista.pk).delete()


    vista.modified = datetime.date.today()

    vista.is_default = make_default

    vista.filterstring = querydict.urlencode()
    vista.combined_text_search = combined_text_search
    vista.combined_text_fields = ','.join(combined_text_fields)
    vista.sort_string = ','.join(order_by)

    vista.model_name = queryset.model.__module__[:-6] + queryset.model.__name__

    vista.save()

    return {'querydict': querydict, 'queryset':queryset}


# call this function in a try/except block to catch DoesNotExist.

def get_latest_vista(request, settings, queryset, defaults):

    vista = Vista.objects.filter(user=request.user).latest('modified')

    return make_vista(request, settings, queryset, defaults, vista)



# call this function in a try/except block to catch DoesNotExist.
def retrieve_vista(request, settings, queryset, defaults):

    vista__name = request.POST.get('vista__name') if 'vista__name' in request.POST else ''
    print(vista__name)
    vista = Vista.objects.filter(name=vista__name, user=request.user).latest('modified')
    print(vista)
    return make_vista(request, settings, queryset, defaults, vista)


def get_global_vista(request, settings, queryset, defaults):

    vista = Vista.objects.filter(is_global_default=True).latest('modified')
    return make_vista(request, settings, queryset, defaults, vista)

# does not return anything.  Most likely you'll want to call get_latest_vista after calling this
def delete_vista(request):

    vista__name = request.POST.get('vista__name') if 'vista__name' in request.POST else ''
    vista = Vista.objects.filter(name=vista__name, user=request.user).delete()
