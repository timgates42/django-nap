from functools import partial

from django.core.exceptions import ValidationError
from django.db.models.fields import NOT_PROVIDED

from nap.utils import digattr


class field(property):
    '''A base class to compare against.'''
    def __new__(cls, *args, **kwargs):
        '''
        Allow specifying keyword arguments when used as a decorator.
        '''
        if not args:
            return partial(field, **kwargs)
        return super().__new__(cls, *args, **kwargs)

    def __init__(self, *args, **kwargs):
        self.required = kwargs.pop('required', False)
        self.default = kwargs.pop('default', NOT_PROVIDED)
        self.readonly = kwargs.pop('readonly', False)
        super().__init__(*args, **kwargs)

    def __get__(self, instance, cls=None):
        if instance is None:
            return self
        return self.fget(instance._obj)

    def __set__(self, instance, value):
        if self.fset is None:
            return
        self.fset(instance._obj, value)


class context_field(field):
    '''Special case of field that allows access to the Mapper itself'''
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.context = kwargs

    def __get__(self, instance, cls=None):
        if instance is None:
            return self
        return self.fget(self, instance._obj)

    def __set__(self, instance, value):
        if self.fset is None:
            return
        return self.fset(self, instance._obj, value)


# Generic field properties:
# - name
# - default
# - required
# - read-only

class Field(field):
    '''
    class V(Mapper):
        foo = Field('bar', default=1)
    '''
    def __init__(self, name, default=NOT_PROVIDED, required=True, readonly=False):
        self.name = name
        self.default = default
        if readonly and required:
            raise ValueError("Field can not be both readonly and required.")
        self.required = required
        self.readonly = readonly

    def __get__(self, instance, cls=None):
        if instance is None:
            return self
        value = getattr(instance._obj, self.name, self.default)
        return value

    def __set__(self, instance, value):
        setattr(instance._obj, self.name, value)


class DigField(Field):
    '''
    Use digattr to resolve values in a DTL compatible syntax.
    '''
    def __init__(self, *args, **kwargs):
        kwargs.setdefault('readonly', True)
        super().__init__(*args, **kwargs)

    def __get__(self, instance, cls=None):
        if instance is None:
            return self
        return digattr(instance._obj, self.name, self.default)


class MapperField(Field):
    '''
    A field that passes data through a Mapper.

    Useful for handling nested models.
    '''
    def __init__(self, *args, **kwargs):
        self.mapper = kwargs.pop('mapper')
        super().__init__(*args, **kwargs)

    def __get__(self, instance, cls=None):
        if instance is None:
            return self
        value = super().__get__(instance, cls)
        mapper = self.mapper()
        return mapper << value

    def __set__(self, instance, value):
        mapper = self.mapper(instance)
        mapper._update(value, update=True)
