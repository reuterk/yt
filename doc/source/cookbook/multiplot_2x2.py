from yt.mods import *
import matplotlib.pyplot as plt
from mpl_toolkits.axes_grid1 import AxesGrid

fn = "IsolatedGalaxy/galaxy0030/galaxy0030"
pf = load(fn) # load data

fig = plt.figure()

# See http://matplotlib.org/mpl_toolkits/axes_grid/api/axes_grid_api.html
# These choices of keyword arguments produce a four panel plot that includes
# four narrow colorbars, one for each plot.  Axes labels are only drawn on the 
# bottom left hand plot to avoid repeating information and make the plot less
# cluttered.
grid = AxesGrid(fig, (0.075,0.075,0.85,0.85),
                nrows_ncols = (2, 2),
                axes_pad = 1.0,
                label_mode = "1",
                share_all = True,
                cbar_location="right",
                cbar_mode="each",
                cbar_size="3%",
                cbar_pad="0%")

fields = ['density', 'x-velocity', 'y-velocity', 'VelocityMagnitude']

# Create the plot.  Since SlicePlot accepts a list of fields, we need only
# do this once.
p = SlicePlot(pf, 'z', fields)
p.zoom(2)

# For each plotted field, force the SlicePlot to redraw itself onto the AxesGrid
# axes.
for i, field in enumerate(fields):
    plot = p.plots[field]
    plot.figure = fig
    plot.axes = grid[i].axes
    plot.cax = grid.cbar_axes[i]

# Finally, redraw the plot on the AxesGrid axes.
p._setup_plots()

plt.savefig('multiplot_2x2.png')
