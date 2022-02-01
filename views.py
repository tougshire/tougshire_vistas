import datetime
import json

from django.contrib import messages
from django.core.exceptions import FieldError
from django.db.models import Q
from django.http import QueryDict
from django.shortcuts import render

from .models import Vista


def make_vista(request, settings, queryset, retrieved_vista=None):

    saveobj = {
        'filter':{},
        'combined_text_search':'',
        'combined_text_fields':[],
        'order_by':[],
    }

    def make_text_query(combined_text_search, combined_text_fields):
        text_query = None
        for fieldname in combined_text_fields:
            if text_query is not None:
                text_query = text_query | Q(**{fieldname + '__contains':combined_text_search})
            else:
                text_query = Q(**{fieldname + '__contains':combined_text_search})

        return text_query

    def in_both(list_a,list_b):
        return list(set(list_a).intersection(set(list_b)))

    def save_vista(request, saveobj, model_name, resave=False):

        vista__name = local_post.get('vista__name') if 'vista__name' in local_post else ''

        try:
            vista, created = Vista.objects.get_or_create(name=vista__name, user=request.user)
        except Vista.MultipleObjectsReturned:
            vista = Vista.objects.filter(name=vista__name, user=request.user)[0]
            Vista.objects.filter(name=vista__name, user=request.user).exclude(pk=vista.pk).delete()

        vista.modified = datetime.date.today()

        if not resave:

            vista.is_default = True if local_post.get('is_default') else False

            vista.combined_text_search = saveobj['combined_text_search']
            vista.combined_text_fields = ','.join(saveobj['combined_text_fields'])
            vista.sort_string = ','.join(saveobj['order_by'])
            for key in saveobj['filter']:
                if type(saveobj['filter'][key]) != str:
                    for typename in [
                        'datetime',
                        'time'
                    ]:
                        if type(saveobj['filter'][key]).__name__ == typename:
                            saveobj['filter'][key] = str(saveobj['filter'][key])
            vista.filterstring = json.dumps(saveobj['filter'])

            vista.model_name = model_name

        vista.save()

    print('tp m21d39')
    print(request.POST.getlist('filterop__item'))
    local_post = request.POST.copy()
    print(local_post.getlist('filterop__item'))

    if retrieved_vista is not None:
        local_post['combined_text_search'] = retrieved_vista.combined_text_search
        if retrieved_vista.filterstring > '':
            retrieved_filter = json.loads(retrieved_vista.filterstring)
            for key in retrieved_filter:
                local_post.setlist(key,retrieved_filter[key])

    if 'combined_text_search' in local_post and local_post.get('combined_text_search') and 'text_fields_available' in settings:
        saveobj['combined_text_search'] = local_post.get('combined_text_search')
        saveobj['combined_text_fields'] = settings['text_fields_available']
        if 'combined_text_fields' in local_post and local_post.get('combined_text_fields'):
            saveobj['combined_text_fields'] = in_both(settings['text_fields_available'], local_post.get('combined_text_fields'))
        else:
            saveobj['combined_text_fields'] = settings['text_fields_available']


        textquery = make_text_query(saveobj['combined_text_search'], saveobj['combined_text_fields'])
        queryset = queryset.filter(textquery)

    if 'filter_fields_available' in settings:
        filterobj = {}
        for fieldname in settings['filter_fields_available']:

            if 'filterop__' + fieldname in local_post and local_post.getlist('filterop__' + fieldname):

                opers = local_post.getlist('filterop__' + fieldname )
                print('tp m21c57 opers by fieldname')
                print(fieldname)
                print(opers)
                saveobj['filter']['filterop__' + fieldname] = opers[:]
                print(saveobj['filter']['filterop__' + fieldname])

                # the isnull operator doesn't require that there be any field values
                if 'isnull' in opers:
                    opers.remove('isnull')
                    filterobj[fieldname + '__isnull'] = True

                # opers that require values

                if 'filterfield__' + fieldname in local_post and local_post.get('filterfield__' + fieldname):
                    values = local_post.getlist('filterfield__' + fieldname)
                    saveobj['filter']['filterfield__' + fieldname] = values

                    for f in range(len(opers)):

                        if opers[f] == 'in':
                            filterobj[fieldname + '__in'] = values

                        if values[f]:

                            for opname in [
                                'exact',
                                'iexact',
                                'contains',
                                'icontains',
                                'lt',
                                'gt',
                                'lte',
                                'gte',
                                'startswith',
                                'istartswith',
                                'endswith',
                                'iendswith',
                                ]:
                                if opers[f] == opname:
                                    filterobj[fieldname + '__' + opname] = values[f]

                            if opers[f] == 'date':
                                try:
                                    filterobj[fieldname + '__date'] = datetime.datetime.fromisoformat(values[f])
                                except ValueError:
                                    pass

                            for opchain in [
                                'lt',
                                'gt',
                                'lte',
                                'gte',
                            ]:
                                if opers[f] == 'date__' + opchain:
                                    try:
                                        filterobj[fieldname + '__date__' + opchain] = datetime.datetime.fromisoformat(values[f])
                                    except ValueError:
                                        pass

                            if opers[f] == 'time':
                                try:
                                    filterobj[fieldname + '__time'] = datetime.time.fromisoformat(values[f])
                                except ValueError:
                                    pass

                            for opchain in [
                                'lt',
                                'gt',
                                'lte',
                                'gte',
                            ]:
                                if opers[f] == 'time__' + opchain:
                                    try:
                                        filterobj[fieldname + '__time__' + opchain] = datetime.time.fromisoformat(values[f])
                                    except ValueError:
                                        pass

                            for opname in [
                                'year',
                                'iso_year',
                                'month',
                                'day',
                                'week',
                                'week_day',
                                'iso_week_day',
                                'hour',
                                'minute',
                                'second',
                                'quarter',
                            ]:
                                if opers[f] == opname:
                                    try:
                                        filterobj[fieldname + '__' + opname] = int(values[f])
                                    except ValueError:
                                        pass

                                for opchain in [
                                    'lt',
                                    'gt',
                                    'lte',
                                    'gte',
                                ]:
                                    if opers[f] == opname + '__' + opchain:
                                        try:
                                            filterobj[fieldname + '__time__' + opchain] = int(values[f])
                                        except ValueError:
                                            pass

                            for opname in ['regex', 'iregex']:
                                if opers[f] == opname:
                                    filterobj[fieldname + '__' + opname] = values[f]

                        if opers[f] == 'range':
                            try:
                                filterobj[fieldname + '__range'] = [ datetime.datetime.fromisoformat(values[0]), datetime.datetime.fromisoformat(values[-1]) ]
                            except ValueError:
                                try:
                                    filterobj[fieldname + '__gte'] = datetime.datetime.fromisoformat(values[0])
                                except ValueError:
                                    pass
                                try:
                                    filterobj[fieldname + '__lte'] = datetime.datetime.fromisoformat(values[-1])
                                except ValueError:
                                    pass

                        if opers[f] == 'time__range':
                            try:
                                filterobj[fieldname + '__range'] = [ datetime.time.fromisoformat(values[0]), datetime.time.fromisoformat(values[-1]) ]
                            except ValueError:
                                try:
                                    filterobj[fieldname + '__gte'] = datetime.time.fromisoformat(values[0])
                                except ValueError:
                                    pass
                                try:
                                    filterobj[fieldname + '__lte'] = datetime.time.fromisoformat(values[-1])
                                except ValueError:
                                    pass

    if filterobj:
        try:
            queryset = queryset.filter(**filterobj)
        except FieldError as e:
            print(saveobj['filter']['filter'])
            print(e)
            messages.add_message(request, messages.WARNING, 'There was an error running the query.  Results might not be correctly filtered')
            messages.add_message(request, messages.WARNING, e)
        except ValueError as e:
            print(saveobj['filter']['filter'])
            print(e)
            messages.add_message(request, messages.WARNING, 'There was an error running the query.  Results might not be correctly filtered')
            messages.add_message(request, messages.WARNING, e)

    if retrieved_vista is None:
        save_vista(request, saveobj, queryset.model._meta.label_lower)
    else:
        save_vista(request, saveobj, queryset.model._meta.label_lower,resave=True)

    return {'context': saveobj, 'queryset':queryset}

def retrieve_vista(request, settings, queryset):

    vista__name = request.POST.get('vista__name') if 'vista__name' in request.POST else ''
    vista, created = Vista.objects.get_or_create(name=vista__name, user=request.user)

    return make_vista(request, settings, queryset, vista)

def retrieve_vista_m21b37(request, settings, queryset):

    vista__name = request.POST.get('vista__name') if 'vista__name' in request.POST else ''
    vista, created = Vista.objects.get_or_create(name=vista__name, user=request.user)

    contextobj = {}

    queryobj = {
        'text':'',
        'filter':{},
    }

    def make_text_query(combined_text_search, combined_text_fields):
        text_query = None

        for fieldname in combined_text_fields:
            if text_query is not None:
                text_query = text_query | Q(**{fieldname + '__contains':combined_text_search})
            else:
                text_query = Q(**{fieldname + '__contains':combined_text_search})

        return text_query

    def in_both(list_a,list_b):
        return list(set(list_a).intersection(set(list_b)))

    if vista.combined_text_search > '' and 'text_fields_available' in settings:

        contextobj['combined_text_search'] = vista.combined_text_search
        combined_text_fields = settings['text_fields_available']

        if vista.combined_text_fields > '':
            combined_text_fields = in_both(vista.combined_text_fields.split(','), combined_text_fields)
        contextobj['combined_text_fields'] = combined_text_fields

        queryobj['text'] = make_text_query(contextobj['combined_text_search'], combined_text_fields)

        if str(queryobj['text']) > '':
            queryset = queryset.filter(queryobj['text'])

    filterobj = None
    try:
        filterobj = json.loads(vista.filterstring)
        queryset = queryset.filter(**filterobj)
        contextobj['filter'] = {}
        for key in filterobj:
            contextobj['filter'][key]=filterobj[key]

    except json.JSONDecodeError:
        print('JSONDecodeError')

    vista.modified = datetime.date.today()
    vista.save()

    return {'context':contextobj, 'queryset':queryset}


