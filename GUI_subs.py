import tkinter as tk
import tkinter.ttk as ttk
from tkinter import filedialog
from tkinter import messagebox
import tkinter.font as tkFont

import matplotlib
import matplotlib.pyplot as plt
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg, NavigationToolbar2TkAgg
from mpl_toolkits import mplot3d
import matplotlib.cm as cm

from LSP_control import SocketLSP

import numpy as np


class SettingsGUI:
    """Class to hold some settings of the GUI"""
    def __init__(self):
        self.version = '1.0'

        self.bgColour = "#ccd"
        self.style = ttk.Style()
        self.style.configure("TFrame", background=self.bgColour)

        self.font_size = 12
        self.mainFont = tkFont.Font(family='Helvetica', size=self.font_size)
        self.mainFontBold = tkFont.Font(family='Helvetica', size=self.font_size, weight='bold')

        # Relating to instrument orientation
        self.lid_first = ['Lidar First', -1]       # List holding string for GUI and associated value for ProcessInfo
        self.lsp_first = ['LSP First', 1]          # Ditto


class MessagesGUI:
    """Class to control messages in the GUI"""
    def __init__(self, frame):
        self.num_messages = 50
        self.setts = SettingsGUI()

        self.mess_sep = '\n'
        self.mess_start = '>> '

        # Frame setup
        self.frame = ttk.Frame(frame, relief=tk.GROOVE, borderwidth=2)
        self.messTitle = tk.Label(self.frame, text='Messages:', font=self.setts.mainFont,
                                  anchor="w").pack(side="top", fill='both')

        self.canvas = tk.Canvas(self.frame, borderwidth=0, background=self.setts.bgColour)
        self.canv_frame = tk.Frame(self.canvas, background=self.setts.bgColour)
        self.vsb = tk.Scrollbar(self.frame, orient="vertical", command=self.canvas.yview)
        self.canvas.configure(yscrollcommand=self.vsb.set)
        self.vsb_x = tk.Scrollbar(self.frame, orient="horizontal", command=self.canvas.xview)
        self.canvas.configure(xscrollcommand=self.vsb_x.set)

        self.vsb.pack(side="right", fill="y")
        self.vsb_x.pack(side="bottom", fill="x")
        self.canvas.pack(side="left", fill="both", expand=True)
        self.canvas.create_window((1, 5), window=self.canv_frame, anchor="nw", tags=self.frame)

        self.canv_frame.bind("<Configure>", self.__onFrameConfigure__)

        self.init_message()

    def __onFrameConfigure__(self, event):
        """Not sure what this does, but it does something important..."""
        self.canvas.configure(scrollregion=self.canvas.bbox('all'))

    def init_message(self):
        """Setup message box with initial messages"""
        row_mess = 0
        tk.Label(self.canv_frame, text='Welcome to 3DTherm', background=self.setts.bgColour,
                 font=self.setts.mainFontBold).grid(row=row_mess, column=0, sticky='w')
        row_mess += 1
        tk.Label(self.canv_frame, text='3DTherm v' + self.setts.version,
                 background=self.setts.bgColour, font=self.setts.mainFont).grid(row=row_mess, column=0, sticky='w')
        row_mess += 1

        self.message_holder = self.mess_start + self.mess_sep
        for i in range(self.num_messages):
            self.message_holder += self.mess_start + self.mess_sep

        self.label = tk.Label(self.canv_frame, text=self.message_holder, background=self.setts.bgColour,
                              font=self.setts.mainFontBold, justify=tk.LEFT)
        self.label.grid(row=row_mess, column=0, sticky='w')

    def message(self, mess_new):
        """Update message list"""
        mess_new = self.mess_start + mess_new + self.mess_sep
        self.message_holder = mess_new + self.message_holder.rsplit(self.mess_start, 1)[
            0]  # Remove first line and append new one
        self.label.configure(text=self.message_holder)


class LSPConfigGUI:
    """Class to build LSP configuration frame for GUI"""
    def __init__(self, holder_frame, gui_message=None):
        self.gui_message = gui_message
        self.setts = SettingsGUI()
        self.frame = tk.LabelFrame(holder_frame, text='LSP Configuration', relief=tk.GROOVE, borderwidth=2,
                                   font=self.setts.mainFontBold)

        lab = tk.Label(self.frame, text='Emissivity:', font=self.setts.mainFont)
        lab.grid(row=0, column=0)

        self.min_emiss = 0.2
        self.max_emis = 1.0
        self.emiss = tk.DoubleVar()
        self.emiss = tk.StringVar()
        self.emiss.set('1.0')
        self.emiss_box = tk.Spinbox(self.frame, textvariable=self.emiss, font=self.setts.mainFont)
        self.emiss_box.configure(from_=0.2, to=1.0, increment=0.01, width=4)
        self.emiss_box.grid(row=0, column=1)

        self.update_butt = tk.Button(self.frame, text='Update Device', font=self.setts.mainFontBold,
                                     command=self.update_LSP)
        self.update_butt.grid(row=1, column=1)

    def get_emis(self):
        """Retrieve emissivity"""
        emiss = float(self.emiss.get())
        if emiss > self.max_emis:
            emiss = self.max_emis
        elif emiss < self.min_emiss:
            emiss = self.min_emiss
        return emiss

    def update_LSP(self):
        emiss = self.get_emis()

        # Connect LSP and change emissivity
        lsp_comms = SocketLSP('10.1.10.1', gui_message=self.gui_message)  # Instantiate communications object
        lsp_comms.init_comms()
        message = lsp_comms.recv_resp()
        message_list = message.split(' ')
        if message_list[1] != '0':
            if self.gui_message is not None:
                self.gui_message.message('Error code [%s] returned by LSP. Closing connections...' % message_list[1])
            else:
                print('Error code [%s] returned by LSP. Closing connections...' % message_list[1])
            lsp_comms.close_socket()
            return
        lsp_comms.query_emissivity()

        lsp_comms.set_emissivity(emiss)
        return_code = lsp_comms.set_emissivity_resp()

        lsp_comms.close_socket()



class FileSelector:
    """Class to build frame for selecting a file path
    -> Label for title, label for pathname, button for file selection"""
    # Enumerators for type (save/load)
    LOAD = 0
    SAVE = 1

    def __init__(self, holder_frame, type=LOAD, title='File:', initdir='C:\\'):
        self._len_str = 43  # Length of displayed string in widget
        self._pad = 2

        self.title = title
        self.initdir = initdir
        self.filename = None
        self.filetypes = [('All files', '*.*')]


        # Setup file choice and associated button
        self.frame = tk.Frame(holder_frame)
        lab = ttk.Label(self.frame, text=self.title)
        lab.grid(row=0, column=0)
        self.filename_lab = ttk.Label(self.frame, text='No file selected')
        self.filename_lab.grid(row=0, column=1)

        if type == self.LOAD:
            file_butt = ttk.Button(self.frame, text='Choose file', command=self.select_file)
        elif type == self.SAVE:
            file_butt = ttk.Button(self.frame, text='Choose file', command=self.make_file)
        else:
            print('Warning!!! <type> incorrectly defined in FileSelector, reverting to default [LOAD]')
            file_butt = ttk.Button(self.frame, text='Choose file', command=self.select_file)
        file_butt.grid(row=0, column=2)

    def select_file(self):
        """Create navigation box for selection of file and set filename when chosen"""
        self.filename = filedialog.askopenfilename(initialdir=self.initdir,
                                                    filetypes=self.filetypes,
                                                    title='Select data file')
        self.__config_file_lab__()

    def make_file(self):
        """Create navigation box for creation of new file and update filename when chosen"""
        self.filename = filedialog.asksaveasfilename(initialdir=self.initdir,
                                                    filetypes=self.filetypes,
                                                    title='Define save file')
        self.__config_file_lab__()

    def __config_file_lab__(self):
        """Configure filename label"""
        if not self.filename:
            return
        if len(self.filename) > self._len_str:
            self.filename_lab.configure(text='...' + self.filename[-(self._len_str - 3):])
        else:
            self.filename_lab.configure(text=self.filename)


class PlottingGUI:
    """Class to help with plotting of data in GUI
    ->instantiated by being passed the axis_label argument, defining the labelling of the plot"""
    def __init__(self, frame, axis_label):
        self.frame = tk.Frame(frame, relief=tk.RAISED, borderwidth=5)   # tk frame
        self.axis_label = axis_label    # Axis label (e.g. 'Distance [mm]')
        # self.cmap = 'nipy_spectral'     # Colourmap
        self.cmap = 'magma'     # Colourmap
        self.img_size = [1000, 1000]    # Dimensions of image

        self.cmap_list = ['magma', 'nipy_spectral']

        self.__setup_plots__()  # Setup plot areas

    def __setup_plots__(self):
        """Performs initial plot setup"""
        dummy = np.zeros(self.img_size)

        self.fig, self.ax = plt.subplots()
        self.img = self.ax.imshow(dummy, cmap=self.cmap)
        self.ax.set_xlabel('Scan Angle [arbitrary unit]')
        self.ax.set_ylabel('Scan Number')
        self.cbar = self.fig.colorbar(self.img)
        self.cbar.set_label(self.axis_label)

        col_frame = tk.Frame(self.frame)
        col_frame.pack(side=tk.TOP)
        color_lab = ttk.Label(col_frame, text='Colourmap:')
        color_lab.grid(row=0, column=0)
        self.cmap_var = tk.StringVar()
        self.cmap_var.set(self.cmap_list[0])
        options = ttk.OptionMenu(col_frame, self.cmap_var, self.cmap_var.get(), *self.cmap_list)
        options.grid(row=0, column=1)

        self.canv = FigureCanvasTkAgg(self.fig, master=self.frame)
        self.__draw_canv__()
        self.canv.get_tk_widget().pack(side=tk.TOP, fill=tk.BOTH, expand=True)

        self.toolbar = NavigationToolbar2TkAgg(self.canv, self.frame)
        self.toolbar.update()
        self.canv._tkcanvas.pack(side=tk.TOP)

    def update_cmap(self, data):
        """Updates axis with with new data"""
        self.img.set_data(data)                                             # Update data
        if self.axis_label == 'Distance [mm]':
            print('Updating lidar colormap')
            self.img.set_clim(vmin=0, vmax=np.nanmax(data))     # If lidar data we want to set the distance to 0 minimum
        else:
            self.img.set_clim(vmin=np.nanmin(data), vmax=np.nanmax(data))       # Set colour scale limits
        self.cmap = self.cmap_var.get()
        self.img.set_cmap(cm.get_cmap(self.cmap))                               # Update colourmap
        self.__draw_canv__()                                                    # Draw new plot

    def __draw_canv__(self):
        """Draw canvas"""
        self.canv.show()


class Plot3DGUI:
    """Class for hcreating 3D plot of lidar/thermal data in a frame"""
    def __init__(self, frame):
        self.frame = tk.Frame(frame, relief=tk.RAISED, borderwidth=5)
        self.cmap = 'magma'

        dummy = np.zeros([1, 1, 1])
        foo = np.arange(5)

        self.fig = plt.figure()
        self.ax = self.fig.add_subplot(111, projection='3d')
        self.plot = self.ax.scatter3D(foo, foo, foo, c=foo, cmap=self.cmap, s=1)

        self.canv = FigureCanvasTkAgg(self.fig, master=self.frame)
        self.__draw_canv__()
        self.canv.get_tk_widget().pack(side=tk.TOP, fill=tk.BOTH, expand=True)

        self.toolbar = NavigationToolbar2TkAgg(self.canv, self.frame)
        self.toolbar.update()
        self.canv._tkcanvas.pack(side=tk.TOP)

    def update_plot(self, x_dat, y_dat, z_dat, temp_dat):
        self.ax.remove()        # Think I have to remove previous plot to make new one for 3D plots in matplotlib
        self.ax = self.fig.add_subplot(111, projection='3d')
        self.ax.scatter3D(x_dat, y_dat, z_dat, c=temp_dat, cmap=self.cmap, s=1)
        self.ax.set_xlabel('X')
        self.ax.set_ylabel('Y')
        self.ax.set_zlabel('Z')
        self.ax.set_zlim([np.nanmax(z_dat), 0])
        self.__draw_canv__()

    def __draw_canv__(self):
        """Draw canvas"""
        self.canv.show()
