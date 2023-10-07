# tougshire_vistas

Django app for saving sort and filter parameters

Until further notice this project is in development and updates might break older versions
## Requrements

This app depends on touglates available at https://github.com/tougshire/touglates

## Usage

In the list.html, you can include a sort/filter form with the following tag:

```
<script src="{% static 'touglates/touglates.js' %}">

...

{% include 'tougshire_vistas/filter.html' %}

```

The code for the view is more complex.  Below is an example of a ListView 

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
        # This can include related fields such as 'makemodel__name'
        # which, in this example, refers to the name, which is a field
        # of MakeModel
        
        self.vista_settings['fields'] = make_vista_fields(Item, field_names=[
            'common_name',
            'network_name',
            'serial_number',
            'makemodel__name',
            'asset_number',
            'barcode',
            'role',
            'owner',
            'location',
            'status',
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
        self.vista_settings['fields']['makemodel__name']['label']='Model Name'

        # Define the default view.
        # Make sure the fields used here are also in the list of fields above
        # You can leave the trailing __0 out if you only have one fieldname / op / value set
        # but I haven't tested as much without the trailing __0 so it's probably best to leave it in

        self.vista_defaults = QueryDict(urlencode([
            ('filter__fieldname__0', ['status']),
            ('filter__op__0', ['exact']),
            ('filter__value__0', 1),
            ('order_by', ['common_name', 'serial_number',]),
            ('paginate_by',self.paginate_by),
        ],doseq=True), mutable=True )

        return super().setup(request, *args, **kwargs)

    # Redirect POST requests
    # The filter form uses POST as the method, but ListView doesn't process POST requests so redirect post to get
    #
    def post(self, request, *args, **kwargs):
        return super().get(request, *args, **kwargs)

    # Call on Tougshire Vista to process and return the queryset
    # 

    def get_queryset(self, **kwargs):

        queryset = super().get_queryset()

        self.vistaobj = {'querydict':QueryDict(), 'queryset':queryset}

        return get_vista_queryset( self )

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

        if self.request.user.is_authenticated:
            context_data['vistas'] = Vista.objects.filter(user=self.request.user, model_name='libtekin.item').all() # for choosing saved vistas

        if self.request.POST.get('vista_name'):
            context_data['vista_name'] = self.request.POST.get('vista_name')

        context_data['count'] = self.object_list.count()

        return context_data
```
