import json
from django.shortcuts import render
from .models import Vista
from django.core.exceptions import FieldError
from django.db.models import Q

def get_vista_object(view, queryset, model_name):
    shown_fields=[]
    order_by = []
    filter_object={}
    text_q = None
    new_queryset = None
    combined_text_search=''

    def combine_q(text, common_text_fields):
        text_q = None
        for fieldname in common_text_fields:
            if text_q is None:
                text_q = Q(**{fieldname + '__contains':text})
            else:
                text_q = text_q | Q(**{fieldname + '__contains':text})

        return text_q

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

        if 'combined_text_search' in view.request.POST:
            combined_text_search = view.request.POST.get('combined_text_search')
            view.combined_text_search = combined_text_search
            text_q = combine_q(combined_text_search, view.common_text_fields)


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


        if text_q or filter_object or order_by or shown_fields:

            vista, created = Vista.objects.get_or_create( user=view.request.user, model_name='libtekin.item', name=vista__name )

            if text_q is not None:
                view.text_q = text_q
                vista.combined_text_search=combined_text_search
                queryset = queryset.filter(text_q)

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
            combined_text_search = vista.combined_text_search
            text_q = combine_q(combined_text_search, view.common_text_fields)
            order_by = vista.sortstring.split(',')
            shown_fields = vista.shown_fields.split(',')
            queryset = queryset.filter(text_q).filter(**filter_object).order_by(*order_by)

            new_queryset = queryset

        except json.JSONDecodeError:
            print('JSONDecodeError')
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
            combined_text_search = vista.combined_text_search
            text_q = combine_q(combined_text_search, view.common_text_fields)
            order_by = vista.sortstring.split(',')
            shown_fields = vista.shown_fields.split(',')
            try:
                queryset = queryset.filter(text_q).filter(**filter_object).order_by(order_by)
                new_queryset = queryset

            except (ValueError, TypeError, FieldError):
                print('Field/Value/Type Error')
                vista.delete()

        except json.JSONDecodeError:
            print('deserialization error')
            vista.delete()

    if new_queryset is None:
        new_queryset = queryset

    return {'queryset':new_queryset, 'combined_text_search':combined_text_search, 'filter_object':filter_object, 'order_by':order_by, 'shown_fields':shown_fields}

