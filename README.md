Therm_Lidar Python

Group of modules used to process Lidar and LSP data
> Running GUI.py provides simple user-access to the functions provided by the other modules, and thus should be
prefered as the main starting point for new users
>> GUI_subs.py holds some important classes used by GUI.py predominatnly, to help build the GUI. They are separated
to maintain code readability

> post_process.py holds important classes/functions for processing the LSP/lidar data after it has been acquired.
> It is used by GUI.py

> data_handler.py is the main acquisition module, used for combined LSP-lidar acquisitions and saving data

> LSP_control.py Contains a class for socket interfacing with LSP and a class for basic processing of data

> therm_process contains a little more processing detail of LSP data, but should probably be incoorporate into LSP_control

> server contains the main localhost server class, for pulling data from Lidar and LSP programs

> read_lidar contains functinos to process saved lidar data. This may become deprecated if all data is pulled to local
> programs and saved together in a different format

> process_lidar contains a class to process lidar data - basically obsolete now

> main is a general program which in the end will perform central functions, but currently is quite basic - almost obsolete now

STILL TO DO!
> Write method in LSPControl for setting emissivity - add option in GUI