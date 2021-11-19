import os
import weakref

import numpy as np

from yt.data_objects.index_subobjects.grid_patch import AMRGridPatch
from yt.data_objects.static_output import Dataset
from yt.funcs import setdefaultattr
from yt.geometry.grid_geometry_handler import GridIndex
from yt.utilities.on_demand_imports import _h5py as h5py

from .fields import ChollaFieldInfo


class ChollaGrid(AMRGridPatch):
    _id_offset = 0

    def __init__(self, id, index, level, dims):
        super().__init__(id, filename=index.index_filename, index=index)
        self.Parent = None
        self.Children = []
        self.Level = level
        self.ActiveDimensions = dims

    def __repr__(self):
        return "ChollaGrid_%04i (%s)" % (self.id, self.ActiveDimensions)


class ChollaHierarchy(GridIndex):
    grid = ChollaGrid

    def __init__(self, ds, dataset_type="cholla"):
        self.dataset_type = dataset_type
        self.dataset = weakref.proxy(ds)
        # for now, the index file is the dataset!
        self.index_filename = self.dataset.parameter_filename
        self.directory = os.path.dirname(self.index_filename)
        # float type for the simulation edges and must be float64 now
        self.float_type = np.float64
        super().__init__(ds, dataset_type)

    def _detect_output_fields(self):
        h5f = h5py.File(self.index_filename, mode="r")
        self.field_list = [("cholla", k) for k in h5f.keys()]
        h5f.close()

    def _count_grids(self):
        # This needs to set self.num_grids (int)
        # Probably need to change this.
        self.num_grids = 1

    def _parse_index(self):
        self.grid_left_edge[0][:] = self.ds.domain_left_edge[:]
        self.grid_right_edge[0][:] = self.ds.domain_right_edge[:]
        self.grid_dimensions[0][:] = self.ds.domain_dimensions[:]
        self.grid_particle_count[0][0] = 0
        self.grid_levels[0][0] = 1
        self.max_level = 1

    def _populate_grid_objects(self):
        self.grids = np.empty(self.num_grids, dtype="object")
        for i in range(self.num_grids):
            g = self.grid(i, self, self.grid_levels.flat[i], self.grid_dimensions[i])
            g._prepare_grid()
            g._setup_dx()
            self.grids[i] = g


class ChollaDataset(Dataset):
    _index_class = ChollaHierarchy
    _field_info_class = ChollaFieldInfo

    def __init__(
        self,
        filename,
        dataset_type="cholla",
        storage_filename=None,
        units_override=None,
    ):
        self.fluid_types += ("cholla",)
        super().__init__(filename, dataset_type, units_override=units_override)
        self.storage_filename = storage_filename

    def _set_code_unit_attributes(self):
        # This is where quantities are created that represent the various
        # on-disk units.  These are the currently available quantities which
        # should be set, along with examples of how to set them to standard
        # values.
        #
        self.length_unit = self.quan(1.0, "pc")
        self.mass_unit = self.quan(1.0, "Msun")
        self.time_unit = self.quan(1000, "yr")
        self.velocity_unit = self.quan(1.0, "cm/s")
        self.magnetic_unit = self.quan(1.0, "gauss")

        # this minimalistic implementation fills the requirements for
        # this frontend to run, change it to make it run _correctly_ !
        for key, unit in self.__class__.default_units.items():
            setdefaultattr(self, key, self.quan(1, unit))

    def _parse_parameter_file(self):

        h5f = h5py.File(self.parameter_filename, mode="r")
        attrs = h5f.attrs
        self.parameters = {k: v for (k, v) in attrs.items()}
        self.domain_left_edge = attrs["bounds"][:].astype("=f8")
        self.domain_right_edge = attrs["domain"][:].astype("=f8")
        self.dimensionality = len(attrs["dims"][:])
        self.domain_dimensions = attrs["dims"][:].astype("=f8")
        self.current_time = attrs["t"][:]
        self._periodicity = (False, False, False)
        h5f.close()

        # CHOLLA cannot yet be run as a cosmological simulation
        self.cosmological_simulation = 0
        self.current_redshift = 0.0
        self.omega_lambda = 0.0
        self.omega_matter = 0.0
        self.hubble_constant = 0.0

        # CHOLLA datasets are always unigrid cartesian
        self.geometry = "cartesian"

    @classmethod
    def _is_valid(cls, filename, *args, **kwargs):
        # This accepts a filename or a set of arguments and returns True or
        # False depending on if the file is of the type requested.
        #
        # The functionality in this method should be unique enough that it can
        # differentiate the frontend from others. Sometimes this means looking
        # for specific fields or attributes in the dataset in addition to
        # looking at the file name or extension.
        try:
            fileh = h5py.File(filename, mode="r")
        except (ImportError, OSError):
            return False
        
        try:
            attrs = fileh.attrs
        except AttributeError:
            return False
        else:
            return "bounds" in attrs and "domain" in attrs
        finally:
            fileh.close()
