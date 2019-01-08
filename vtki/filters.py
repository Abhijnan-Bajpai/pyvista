"""
These calsses hold methods to apply general filters to any data type.
By inherritting these classes into the wrapped VTK data structures, a user
can easily apply common filters in an intuitive manner.

Example:

    >>> import vtki
    >>> from vtki import examples
    >>> dataset = examples.load_uniform()
    >>> dataset.set_active_scalar('Spatial Point Data') # Array the filters will use

    >>> # Threshold
    >>> thresh = dataset.threshold([100, 500])
    >>> thresh.plot(scalars='Spatial Point Data')

    >>> # Slice
    >>> slc = dataset.slice()
    >>> slc.plot(scalars='Spatial Point Data')

    >>> # Clip
    >>> clp = dataset.clip(invert=True)
    >>> clp.plot(scalars='Spatial Point Data')

    >>> # Contour
    >>> iso = dataset.contour()
    >>> iso.plot(scalars='Spatial Point Data')
    
"""

import collections
import numpy as np
import vtk


from vtki.utilities import get_scalar, wrap

NORMALS = {
    'x': [1, 0, 0],
    'y': [0, 1, 0],
    'z': [0, 0, 1],
    '-x': [-1, 0, 0],
    '-y': [0, -1, 0],
    '-z': [0, 0, -1],
}


def _generate_plane(normal, origin):
    plane = vtk.vtkPlane()
    plane.SetNormal(normal[0], normal[1], normal[2])
    plane.SetOrigin(origin[0], origin[1], origin[2])
    return plane



class DataSetFilters(object):
    """A set of common filters that can be applied to any vtkDataSet"""


    def clip(dataset, normal='x', origin=None, invert=True):
        """Clip a dataset by a plane by specifying the origin and normal. If no
        parameters are given the clip will occur in the center of that dataset"""
        if isinstance(normal, str):
            normal = NORMALS[normal.lower()]
        # find center of data if origin not specified
        if origin is None:
            origin = dataset.center
        # create the plane for clipping
        plane = _generate_plane(normal, origin)
        # run the clip
        alg = vtk.vtkClipDataSet()
        alg.SetInputDataObject(dataset) # Use the grid as the data we desire to cut
        alg.SetClipFunction(plane) # the the cutter to use the plane we made
        alg.SetInsideOut(invert) # invert the clip if needed
        alg.Update() # Perfrom the Cut
        return wrap(alg.GetOutputDataObject(0)) # wrap the output


    def slice(dataset, normal='x', origin=None):
        """Slice a dataset by a plane at the specified origin and normal vector
        orientation. If no origin is specified, the center of the input dataset will
        be used.
        """
        if isinstance(normal, str):
            normal = NORMALS[normal.lower()]
        # find center of data if origin not specified
        if origin is None:
            origin = dataset.center
        # create the plane for clipping
        plane = _generate_plane(normal, origin)
        # create slice
        alg = vtk.vtkCutter() # Construct the cutter object
        alg.SetInputDataObject(dataset) # Use the grid as the data we desire to cut
        alg.SetCutFunction(plane) # the the cutter to use the plane we made
        alg.Update() # Perfrom the Cut
        return wrap(alg.GetOutputDataObject(0)) # wrap the output



    def threshold(dataset, value, scalars=None, invert=False, continuous=False,
                  preference='cell'):
        """This filter will apply a ``vtkThreshold`` filter to the input dataset and
        return the resulting object. If scalars is None, the inputs active_scalar
        is used.

        """
        alg = vtk.vtkThreshold()
        alg.SetInputDataObject(dataset)
        # set the scalaras to threshold on
        if scalars is None:
            field, scalars = dataset.active_scalar_info
        else:
            _, field = get_scalar(dataset, scalars, preference=preference, info=True)
        alg.SetInputArrayToProcess(0, 0, 0, field, scalars) # args: (idx, port, connection, field, name)
        # set thresholding parameters
        alg.SetUseContinuousCellRange(continuous)
        # check if value is iterable (if so threshold by min max range like ParaView)
        if isinstance(value, collections.Iterable):
            if len(value) != 2:
                raise RuntimeError('Value range must be length one for a float value or two for min/max; not ({}).'.format(value))
            alg.ThresholdBetween(value[0], value[1])
            # NOTE: Invert for ThresholdBetween is coming in vtk=>8.2.x
            #alg.SetInvert(invert)
        else:
            # just a single value
            if invert:
                alg.ThresholdByLower(value)
            else:
                alg.ThresholdByUpper(value)
        # Run the threshold
        alg.Update()
        return wrap(alg.GetOutputDataObject(0)) # port 0



class PointSetFilters(object):
    """Filters that can be applied to point set data objects"""

    def contour(dataset, isosurfaces=10, scalars=None, compute_normals=False,
                compute_gradients=False, compute_scalars=True, preference='point'):
        """Contours an input dataset by an array. ``isosurfaces`` can be an integer
        specifying the number of isosurfaces in the data range or an iterable set of
        values for explicitly setting the isosurfaces.
        """
        alg = vtk.vtkContourFilter() #vtkMarchingCubes
        alg.SetInputDataObject(dataset)
        alg.SetComputeNormals(compute_normals)
        alg.SetComputeGradients(compute_gradients)
        alg.SetComputeScalars(compute_scalars)
        # set the array to contour on
        #dataset.set_active_scalar(scalars, preference=preference)
        if scalars is None:
            field, scalars = dataset.active_scalar_info
        else:
            _, field = get_scalar(dataset, scalars, preference=preference, info=True)
        # NOTE: only point data is allowed
        if field != 0:
            raise RuntimeError('Can only contour by Point data at this time.')
        alg.SetInputArrayToProcess(0, 0, 0, field, scalars) # args: (idx, port, connection, field, name)
        # set the isosurfaces
        if isinstance(isosurfaces, int):
            # generate values
            alg.GenerateValues(isosurfaces, dataset.get_data_range(scalars))
        elif isinstance(value, collections.Iterable):
            alg.SetNumberOfContours(len(isosurfaces))
            for i, val in enumerate(isosurfaces):
                alg.SetValue(i, val)
        else:
            raise RuntimeError('isosurfaces not understood.')
        alg.Update()
        return wrap(alg.GetOutputDataObject(0)) # wrap the output
