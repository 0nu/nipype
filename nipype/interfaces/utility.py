# emacs: -*- mode: python; py-indent-offset: 4; indent-tabs-mode: nil -*-
# vi: set ft=python sts=4 ts=4 sw=4 et:

from inspect import getsource
import numpy as np

from nipype.utils.filemanip import (filename_to_list, list_to_filename)
from nipype.interfaces.base import (traits, TraitedSpec, DynamicTraitedSpec,
                                    Undefined, isdefined, OutputMultiPath,
    InputMultiPath)
from nipype.interfaces.io import IOBase, add_traits

    
class IdentityInterface(IOBase):
    """Basic interface class generates identity mappings

    Examples
    --------
    
    >>> from nipype.interfaces.utility import IdentityInterface
    >>> ii = IdentityInterface(fields=['a','b'])
    >>> ii.inputs.a
    <undefined>

    >>> ii.inputs.a = 'foo'
    >>> out = ii._outputs()
    >>> out.a
    <undefined>

    >>> out = ii.run()
    >>> out.outputs.a
    'foo'
    
    """
    input_spec = DynamicTraitedSpec
    output_spec = DynamicTraitedSpec
    
    def __init__(self, fields=None, **inputs):
        super(IdentityInterface, self).__init__(**inputs)
        if fields is None or not fields:
            raise Exception('Identity Interface fields must be a non-empty list')
        self._fields = fields
        add_traits(self.inputs, fields)

    def _add_output_traits(self, base):
        undefined_traits = {}
        for key in self._fields:
            base.add_trait(key, traits.Any)
            undefined_traits[key] = Undefined
        base.trait_set(trait_change_notify=False, **undefined_traits)
        return base

    def _list_outputs(self):
        outputs = self._outputs().get()
        for key in self._fields:
            val = getattr(self.inputs, key)
            if isdefined(val):
                outputs[key] = val
        return outputs

class MergeInputSpec(DynamicTraitedSpec):
    axis = traits.Enum('vstack', 'hstack', usedefault=True,
                desc='direction in which to merge, hstack requires same number of elements in each input')
class MergeOutputSpec(TraitedSpec):
    out = traits.List(desc='Merged output')

class Merge(IOBase):
    """Basic interface class to merge inputs into a single list

    Examples
    --------
    
    >>> from nipype.interfaces.utility import Merge
    >>> mi = Merge(3)
    >>> mi.inputs.in1 = 1
    >>> mi.inputs.in2 = [2,5]
    >>> mi.inputs.in3 = 3
    >>> out = mi.run()
    >>> out.outputs.out
    [1, 2, 5, 3]
    
    """
    input_spec = MergeInputSpec
    output_spec = MergeOutputSpec
    
    def __init__(self, numinputs=0, **inputs):
        super(Merge, self).__init__(**inputs)
        self.numinputs = numinputs
        add_traits(self.inputs, ['in%d'%(i+1) for i in range(numinputs)])
        
    def _list_outputs(self):
        outputs = self._outputs().get()
        out = []
        if self.inputs.axis == 'vstack':
            for idx in range(self.numinputs):
                value = getattr(self.inputs, 'in%d'%(idx+1))
                if isdefined(value):
                    if isinstance(value, list):
                        out.extend(value)
                    else:
                        out.append(value)
        else:
            for i in range(len(filename_to_list(self.inputs.in1))):
                out.insert(i,[])
                for j in range(self.numinputs):
                    out[i].append(filename_to_list(getattr(self.inputs, 'in%d'%(j+1)))[i])
        if out:
            outputs['out'] = out
        return outputs

class SplitInputSpec(TraitedSpec):
    inlist = traits.List(traits.Any, mandatory=True,
                  desc='list of values to split')
    splits = traits.List(traits.Int, mandatory=True,
                  desc='Number of outputs in each split - should add to number of inputs')

class Split(IOBase):
    """Basic interface class to split lists into multiple outputs

    Examples
    --------
    
    >>> from nipype.interfaces.utility import Split
    >>> sp = Split()
    >>> _ = sp.inputs.set(inlist=[1,2,3],splits=[2,1])
    >>> out = sp.run()
    >>> out.outputs.out1
    [1, 2]
    
    """

    input_spec = SplitInputSpec
    output_spec = DynamicTraitedSpec
        
    def _add_output_traits(self, base):
        undefined_traits = {}
        for i in range(len(self.inputs.splits)):
            key = 'out%d'%(i+1)
            base.add_trait(key, traits.Any)
            undefined_traits[key] = Undefined
        base.trait_set(trait_change_notify=False, **undefined_traits)
        return base
    
    def _list_outputs(self):
        outputs = self._outputs().get()
        if isdefined(self.inputs.splits):
            if sum(self.inputs.splits) != len(self.inputs.inlist):
                raise RuntimeError('sum of splits != num of list elements')
            splits = [0]
            splits.extend(self.inputs.splits)
            splits = np.cumsum(splits)
            for i in range(len(splits)-1):
                outputs['out%d'%(i+1)] =  np.array(self.inputs.inlist)[splits[i]:splits[i+1]].tolist()
        return outputs

class SelectInputSpec(TraitedSpec):
    inlist = InputMultiPath(traits.Any, mandatory=True,
                  desc='list of values to choose from')
    index = InputMultiPath(traits.Int, mandatory=True,
                  desc='0-based indices of values to choose')
    
class SelectOutputSpec(TraitedSpec):
    out = OutputMultiPath(traits.Any,
                          desc='list of selected values')
    
class Select(IOBase):
    """Basic interface class to select specific elements from a list

    Examples
    --------
    
    >>> from nipype.interfaces.utility import Select
    >>> sl = Select()
    >>> _ = sl.inputs.set(inlist=[1,2,3,4,5],index=[3])
    >>> out = sl.run()
    >>> out.outputs.out
    4
    
    >>> _ = sl.inputs.set(inlist=[1,2,3,4,5],index=[3,4])
    >>> out = sl.run()
    >>> out.outputs.out
    [4, 5]
    
    """

    input_spec = SelectInputSpec
    output_spec = SelectOutputSpec
    
    def _list_outputs(self):
        outputs = self._outputs().get()
        out = np.array(self.inputs.inlist)[np.array(self.inputs.index)].tolist()
        outputs['out'] = out
        return outputs

class FunctionInputSpec(DynamicTraitedSpec):
    function_str = traits.Str(mandatory=True, desc='code for function')

class Function(IOBase):
    """Runs arbitrary function as an interface

    Examples
    --------

    >>> func = 'def func(arg1, arg2=5): return arg1 + arg2'
    >>> fi = Function(input_names=['arg1', 'arg2'], output_names=['out'])
    >>> fi.inputs.function_str = func
    >>> res = fi.run(arg1=1)
    >>> res.outputs.out
    6

    """
    
    input_spec = FunctionInputSpec
    output_spec = DynamicTraitedSpec

    def __init__(self, input_names, output_names, function=None, **inputs):
        """

        Parameters
        ----------

        input_names: single str or list
            names corresponding to function inputs
        output_names: single str or list
            names corresponding to function outputs. has to match the number of outputs
        """
        
        super(Function, self).__init__(**inputs)
        if function:
            if hasattr(function, '__call__'):
                try:
                    self.inputs.function_str = getsource(function)
                except IOError:
                    raise Exception('Interface Function does not accept ' \
                                        'function objects defined interactively in a python session')
            elif isinstance(function, str):
                self.inputs.function_str = function
            else:
                raise Exception('Unknown type of function')
        self._input_names = filename_to_list(input_names)
        self._output_names = filename_to_list(output_names)
        add_traits(self.inputs, [name for name in self._input_names])
        self._out = {}
        for name in self._output_names:
            self._out[name] = None

    def _add_output_traits(self, base):
        undefined_traits = {}
        for key in self._output_names:
            base.add_trait(key, traits.Any)
            undefined_traits[key] = Undefined
        base.trait_set(trait_change_notify=False, **undefined_traits)
        return base

    def _run_interface(self, runtime):
        try:
            ns = {}
            exec self.inputs.function_str in ns
            args = {}
            for name in self._input_names:
                value = getattr(self.inputs, name)
                if isdefined(value):
                    args[name] = value
            function_name = [name for name in ns.keys() if not name == '__builtins__'][0]
            out = ns[function_name](**args)
            if len(self._output_names) == 1:
                self._out[self._output_names[0]] = out
            else:
                if isinstance(out, tuple) and (len(out) != len(self._output_names)):
                    raise Exception('Mismatch in number of outputs')
                for idx, name in enumerate(self._output_names):
                    self._out[name] = out[idx]
        except TypeError, msg :
            print 'Error: %s'%msg
            runtime.returncode = 1
        finally:
            runtime.returncode = 0
        return runtime

    def _list_outputs(self):
        outputs = self._outputs().get()
        for key in self._output_names:
            outputs[key] = self._out[key]
        return outputs

'''
class SubstringMatch(BasicInterface):
    """Basic interface class to match list items containing specific substrings

    Examples
    --------
    
    >>> from nipype.interfaces.utility import SubstringMatch
    >>> match = SubstringMatch()
    >>> match.inputs.update(inlist=['foo', 'goo', 'zoo'], substrings='oo')
    >>> out = match.run()
    >>> out.outputs.out
    ['foo', 'goo', 'zoo']
    >>> match.inputs.update(inlist=['foo', 'goo', 'zoo'], substrings=['foo'])
    >>> out = match.run()
    >>> out.outputs.out
    'foo'
    
    """
    def __init__(self):
        self.inputs = Bunch(inlist=None,
                            substrings=None)
        
    def outputs(self):
        outputs = Bunch(out=None)
        return outputs
    
    def aggregate_outputs(self):
        outputs = self.outputs()
        outputs.out = []
        for val in filename_to_list(self.inputs.inlist):
            match = [val for pat in filename_to_list(self.inputs.substrings) if val.find(pat) >= 0]
            if match:
                outputs.out.append(val)
        if not outputs.out:
            outputs.out = None
        else:
            outputs.out = list_to_filename(outputs.out)
        return outputs
'''
