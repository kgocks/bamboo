
import pandas as pd
from pandas.core.groupby import GroupBy

from inspect import getmembers, isfunction

import bamboo.bamboo
import bamboo, groups, frames

_bamboo_methods = {name:func  for name, func in getmembers(bamboo.bamboo) if isfunction(func)}
_frames_methods = {name:func  for name, func in getmembers(bamboo.frames) if isfunction(func)}
_groups_methods = {name:func  for name, func in getmembers(bamboo.groups) if isfunction(func)}


def _create_bamboo_wrapper(obj, func):
    def callable(*args, **kwargs):
        res = func(obj, *args, **kwargs)
        if isinstance(res, pandas.DataFrame):
            return BambooDataFrame(res)
        elif isinstance(res, pandas.core.groupby.GroupBy):
            return BambooGroupBy(res)
        else:
            return res
    return callable


# This is obsolete
class Bamboo(object):
    """
    A class designed to wrap a Pandas object and dispatch
    bamboo functions (when available).  Else, it falls
    back to the object's original methods
    """

    def __init__(self, obj):
        self.obj = obj
        self._is_data_frame = isinstance(self.obj, pandas.DataFrame)
        self._is_group_by = isinstance(self.obj, pandas.core.groupby.GroupBy)


    def __getattr__(self, *args, **kwargs):

        name, args = args[0], args[1:]

        isinstance(self.obj, pandas.DataFrame)

        if (self._is_data_frame or self._is_group_by ) and name in _bamboo_methods:
            return _create_bamboo_wrapper(self, _bamboo_methods[name])

        if self._is_data_frame and name in _frames_methods:
            return _create_bamboo_wrapper(self, _frames_methods[name])

        if self._is_group_by and name in _groups_methods:
            return _create_bamboo_wrapper(self, _groups_methods[name])

        return self.obj.__getattribute__(*args, **kwargs)


class BambooDataFrame(pandas.DataFrame):

    def __init__(self, *args, **kwargs):
        super(BambooDataFrame, self).__init__(*args, **kwargs)

    def __getattr__(self, *args, **kwargs):

        name, pargs = args[0], args[1:]

        if name in _bamboo_methods:
            return _create_bamboo_wrapper(self, _bamboo_methods[name])

        if name in _frames_methods:
            return _create_bamboo_wrapper(self, _frames_methods[name])

        return super(BambooDataFrame, self).__getattribute__(*args, **kwargs)




class BambooGroupBy(pandas.core.groupby.GroupBy):

    def __init__(self, other):
        if not isinstance(other, pandas.core.groupby.GroupBy):
            raise TypeError()
        super(BambooGroupBy, self).__init__(
                                             other.obj,
                                             other.keys,
                                             other.axis,
                                             other.level,
                                             other.grouper,
                                             other.exclusions,
                                             other._selection,
                                             other.as_index,
                                             other.sort,
                                             other.group_keys,
                                             other.squeeze)

    def head(self, *args, **kwargs):
        return bamboo.bamboo.head(self, *args, **kwargs)

    def __getattr__(self, *args, **kwargs):

        name, pargs = args[0], args[1:]

        if name in _bamboo_methods:
            print "Using bamboo"
            return _create_bamboo_wrapper(self, _bamboo_methods[name])

        if name in _groups_methods:
            print "Using groups"
            return _create_bamboo_wrapper(self, _groups_methods[name])

        return super(BambooGroupBy, self).__getattribute__(*args, **kwargs)

