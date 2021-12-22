import json
from django.shortcuts import render
from .models import Vista
from django.core.exceptions import FieldError

def get_vista_object(view, queryset, model_name):
    order_by = []
    filter_object={}
    new_queryset = None

    if 'query_submitted' in view.request.POST:

        for i in range(0,3):
            order_by_i = 'order_by_{}'.format(i)
            if order_by_i in view.request.POST:
                for field in view.order_by_fields:
                    if view.request.POST.get(order_by_i) == field['name']:
                        order_by.append(field['name'])

        for fieldname in view.filter_fields['in']:
            filterfieldname = 'filter__' + fieldname + '__in'
            if filterfieldname in view.request.POST and view.request.POST.get(filterfieldname) > '':
                postfields = view.request.POST.getlist(filterfieldname)
                fieldlist = []
                for postfield in postfields:
                    if postfield.isdecimal():
                        fieldlist.append(postfield)
                if fieldlist:
                    filter_object[fieldname + '__in'] = postfields

            filterfieldnone = 'filter__' + fieldname + '__none'
            if filterfieldnone in view.request.POST:
                filter_object[fieldname] = None


        vista__name = ''
        if 'vista__name' in view.request.POST and view.request.POST.get('vista__name') > '':
            vista__name = view.request.POST.get('vista__name')


        if filter_object or order_by:

            vista, created = Vista.objects.get_or_create( user=view.request.user, model_name='libtekin.item', name=vista__name )

            if filter_object:
                view.filter_object = filter_object
                vista.filterstring = json.dumps( filter_object )
                queryset = queryset.filter(**filter_object)

            if order_by:
                view.order_by = order_by
                vista.sortstring = ','.join(order_by)
                queryset = queryset.order_by(*order_by)

            vista.save()
            new_queryset = queryset

    elif 'get_vista' in view.request.POST:

        vista__name = ''

        if 'vista__name' in view.request.POST and view.request.POST.get('vista__name') > '':
            vista__name = view.request.POST.get('vista__name')

        vista, created = Vista.objects.get_or_create( user=view.request.user, model_name='libtekin.item', name=vista__name )

        try:
            filter_object = json.loads(vista.filterstring)
            order_by = vista.sortstring.split(',')
            queryset = queryset.filter(**filter_object).order_by(*order_by)

            new_queryset = queryset

        except json.JSONDecodeError:
            pass

    elif 'delete_vista' in view.request.POST:
        vista__name = ''

        if 'vista__name' in view.request.POST and view.request.POST.get('vista__name') > '':

            vista__name = view.request.POST.get('vista__name')
            Vista.objects.filter( user=view.request.user, model_name='libtekin.item', name=vista__name ).delete()


    # this code runs if no queryset has been returned yet
        vista = Vista.objects.filter( user=view.request.user, model_name='Item', is_default=True ).last()
        if vista is None:
            vista = Vista.objects.filter( user=view.request.user, model_name='Item' ).last()
        if vista is None:
            vista, created = Vista.objects.get_or_create( user=view.request.user, model_name='Item' )

        try:
            filter_object = json.loads(vista.filterstring)
            order_by = vista.sortstring.split(',')
            try:
                queryset = queryset.filter(**filter_object).order_by(order_by)
                new_queryset = queryset

            except (ValueError, TypeError, FieldError):
                print('Field/Value/Type Error')
                vista.delete()

        except json.JSONDecodeError:
            print('deserialization error')
            vista.delete()

    if new_queryset is None:
        new_queryset = queryset

    return {'queryset':new_queryset, 'filter_object':filter_object, 'order_by':order_by}

