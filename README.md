# tougshire_vistas

Django app for saving sort and filter parameters

Until further notice this project is in initial development and updates might break older versions

This is not complete and it requires a lot from the view that contains it.  Documentation pending

## Usage

In the list.html, you can include a sort/filter form with the following tag:
```
{% include 'tougshire_vistas/filter.html' %}
```
Or you can write your own

The code for the view is more complex.  Below is an example of a ListView which makes use of tougshire_vistas

```
class ItemList(ListView):

    model = Item
    paginate_by = 30

    def setup(self, request, *args, **kwargs):

        self.vista_settings={
            'max_search_keys':5,
            'fields':[],
        }

        # Define the fields that you want to be available to the view
        # This can include related fields such as 'status__is_active'
        # which, in this example, refers to a field named "is_active" which
        # is part of the Status class which is related to Item by the ForeignKey "status"
        #
        self.vista_settings['fields'] = make_vista_fields(Item, field_names=[
            'common_name',
            'mmodel',
            'network_name',
            'serial_number',
            'service_number',
            'asset_number',
            'barcode',
            'phone_number',
            'role',
            'connected_to',
            'essid',
            'owner',
            'assignee',
            'borrower',
            'home',
            'location',
            'status',
            'connected_to__mmodel',
            'connection__mmodel',
            'latest_inventory',
            'status__is_active',
            'notes',
        ])

        # Override the avaiable_for and label for fields as desired
        # available_for can include: 'quicksearch', 'fieldsearch','order_by', and 'columns'
        #    quicksearch: Included in a search that spans multiple fields looking for a single text string
        #    fieldsearch: Included in a list of fields to search in which one field is chosen to be searched for a value
        #    order_by: Included in a choice of fields for ordering
        #    columns: Available to be displayed in the list view
        #
        # Tougshire_vistas will guess at what you want, for example, TextFields are searchable but not, by default, displayed in the results

        self.vista_settings['fields']['notes']['available_for'].append('columns')
        self.vista_settings['fields']['status__is_active']['label']='In Use'

        # Define the default view if, for example, you want users to be able to press a "default"
        # button on an HTML form and get this view, or have a view that comes up if no other views are saved
        # Make sure the fields used here are also in the list of fields above
        # You can leave the trailing __0 out if you only have one fieldname / op / value set
        # but I haven't tested as much without the trailing __0 so it's probably best to leave it in
        #

        self.vista_defaults = QueryDict(urlencode([
            ('filter__fieldname__0', ['status__is_active']),
            ('filter__op__0', ['exact']),
            ('filter__value__0', [True]),
            ('order_by', ['common_name', 'serial_number',]),
            ('paginate_by',self.paginate_by),
        ],doseq=True) )

        return super().setup(request, *args, **kwargs)

    # Redirect POST requests
    # In my HTML, the form that the user fills out uses POST as the method, but ListView doesn't process POST requests
    #
    def post(self, request, *args, **kwargs):
        return super().get(request, *args, **kwargs)

    def get_queryset(self, **kwargs):

        queryset = super().get_queryset()

        self.vistaobj = {'querydict':QueryDict(), 'queryset':queryset}

        # Figure out what functon the user wants and return the appropriate value
        #
        if 'delete_vista' in self.request.POST:
            delete_vista(self.request)

        if 'query' in self.request.session:
            querydict = QueryDict(self.request.session.get('query'))
            self.vistaobj = make_vista(
                self.request.user,
                queryset,
                querydict,
                '',
                False,
                self.vista_settings
            )
            del self.request.session['query']

        elif 'vista_query_submitted' in self.request.POST:

            self.vistaobj = make_vista(
                self.request.user,
                queryset,
                self.request.POST,
                self.request.POST.get('vista_name') if 'vista_name' in self.request.POST else '',
                self.request.POST.get('make_default') if ('make_default') in self.request.POST else False,
                self.vista_settings
            )
        elif 'retrieve_vista' in self.request.POST:

            self.vistaobj = retrieve_vista(
                self.request.user,
                queryset,
                'libtekin.item',
                self.request.POST.get('vista_name'),
                self.vista_settings

            )
        elif 'default_vista' in self.request.POST:

            self.vistaobj = default_vista(
                self.request.user,
                queryset,
                self.vista_defaults,
                self.vista_settings
            )
        else:
            self.vistaobj = get_latest_vista(
                self.request.user,
                queryset,
                self.vista_defaults,
                self.vista_settings
            )

        return self.vistaobj['queryset']

    def get_paginate_by(self, queryset):

        if 'paginate_by' in self.vistaobj['querydict'] and self.vistaobj['querydict']['paginate_by']:
            return self.vistaobj['querydict']['paginate_by']

        return super().get_paginate_by(self)


    def get_context_data(self, **kwargs):

        context_data = super().get_context_data(**kwargs)

        # Get parameters from tougshire_vista mainly to redisplay the sort/filter form with the parameters
        # that the user entered
        #
        vista_data = vista_context_data(self.vista_settings, self.vistaobj['querydict'])

        context_data = {**context_data, **vista_data}

        context_data['vistas'] = Vista.objects.filter(user=self.request.user, model_name='libtekin.item').all() # for choosing saved vistas

        if self.request.POST.get('vista_name'):
            context_data['vista_name'] = self.request.POST.get('vista_name')

        context_data['count'] = self.object_list.count()

        return context_data
```
