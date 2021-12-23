import json
from django.shortcuts import render
from .models import Vista
from django.core.exceptions import FieldError
from django.db.models import Q


def get_vista_object(view, queryset, model_name):
    shown_fields=[]
    order_by = []
    filter_object={}
    qtext = None
    new_queryset = None
    common_text_search=''

    def combine_q(text, common_text_fields):
        qtext = None
        for fieldname in common_text_fields:
            if qtext is None:
                qtext = Q(**{fieldname + '__contains':text})
            else:
                qtext = qtext | Q(**{fieldname + '__contains':text})

        return qtext

    if 'query_submitted' in view.request.POST:

        if 'shown_fields' in view.request.POST:
            post_shown_fields = view.request.POST.getlist('shown_fields')

            showable_fields = [ field['name'] for field in view.showable_fields ]
            for shown_field in post_shown_fields:
                if shown_field in showable_fields:
                    shown_fields.append(shown_field)

        if 'order_by' in view.request.POST:
            post_order_by = view.request.POST.getlist('order_by')
            order_by_fields = [ field['name'] for field in view.order_by_fields ]
            for order_by_field in post_order_by:
                if order_by_field in order_by_fields:
                    order_by.append(order_by_field)

        if 'common_text_search' in view.request.POST:
            common_text_search = view.request.POST.get('common_text_search')
            view.common_text_search = common_text_search
            qtext = combine_q(common_text_search, view.common_text_fields)


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


        if qtext or filter_object or order_by or shown_fields:

            vista, created = Vista.objects.get_or_create( user=view.request.user, model_name='libtekin.item', name=vista__name )

            if qtext is not None:
                view.qtext = qtext
                vista.common_text_search=common_text_search
                queryset = queryset.filter(qtext)

            if filter_object:
                view.filter_object = filter_object
                vista.filterstring = json.dumps( filter_object )
                queryset = queryset.filter(**filter_object)

            if order_by:
                view.order_by = order_by
                vista.sortstring = ','.join(order_by)
                queryset = queryset.order_by(*order_by)

            if shown_fields:
                view.shown_fields = shown_fields
                vista.shown_fields = ','.join(shown_fields)

            vista.save()
            new_queryset = queryset

    elif 'get_vista' in view.request.POST:

        vista__name = ''

        if 'vista__name' in view.request.POST and view.request.POST.get('vista__name') > '':
            vista__name = view.request.POST.get('vista__name')

        vista, created = Vista.objects.get_or_create( user=view.request.user, model_name='libtekin.item', name=vista__name )

        try:
            filter_object = json.loads(vista.filterstring)
            common_text_search = vista.common_text_search
            qtext = combine_q(common_text_search, view.common_text_fields)
            order_by = vista.sortstring.split(',')
            shown_fields = vista.shown_fields.split(',')
            queryset = queryset.filter(qtext).filter(**filter_object).order_by(*order_by)

            new_queryset = queryset

        except json.JSONDecodeError:
            pass

        except (ValueError, TypeError, FieldError):
            print('Field/Value/Type Error')

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
            common_text_search = vista.common_text_search
            qtext = combine_q(common_text_search, view.common_text_fields)
            order_by = vista.sortstring.split(',')
            shown_fields = vista.shown_fields.split(',')
            try:
                queryset = queryset.filter(qtext).filter(**filter_object).order_by(order_by)
                new_queryset = queryset

            except (ValueError, TypeError, FieldError):
                print('Field/Value/Type Error')
                vista.delete()

        except json.JSONDecodeError:
            print('deserialization error')
            vista.delete()

    if new_queryset is None:
        new_queryset = queryset

    return {'queryset':new_queryset, 'common_text_search':common_text_search, 'filter_object':filter_object, 'order_by':order_by, 'shown_fields':shown_fields}

