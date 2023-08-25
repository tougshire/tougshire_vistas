from django.db import models
from django.conf import settings

class Vista(models.Model):
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        verbose_name='user',
        on_delete=models.CASCADE,
        help_text='The user of this search'
    )
    model_name = models.CharField(
        'model name',
        max_length=50,
        help_text='The name of the model to which this view applies'
    )
    name = models.CharField(
        'name',
        max_length=50,
        help_text="The name of the search"
    )
    modified = models.DateTimeField(
        auto_now=True,
        help_text='The date this search was saved'
    )
    filterstring = models.TextField(
        blank=True,
        help_text='The filter string'
    )
    combined_text_search = models.TextField(
        blank=True,
        help_text='The text to search on common text fields'
    )
    combined_text_fields = models.TextField(
        blank=True,
        help_text='The list of fields to use for the combined_text_search'
    )
    sortstring = models.CharField(
        max_length=100,
        blank=True,
        help_text='The sort string'
    )
    show_columns = models.CharField(
        max_length=500,
        blank=True,
        help_text='The list of fields to show'
    )

    def __str__(self):
        return '{} {}'.format(self.user, self.name)

    class Meta:
        ordering = ['modified', 'user', 'name']
        constraints = [
            models.UniqueConstraint(
                fields=['user', 'model_name', 'name'], name='unique_vista'
            )
        ]
