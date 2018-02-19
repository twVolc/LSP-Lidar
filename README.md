Therm_Lidar Python

Group of modules used to process Lidar and LSP data
> GUI.py provides simple user-access to the functions provided by the other modules, and thus should be prefered
 as the main starting point for new users

> data_handler.py is the main acquisition module, used for combined LSP-lidar acquisitions and saving data

> LSP_control.py Contains a class for socket interfacing with LSP and a class for basic processing of data

> therm_process contains a little more processing detail of LSP data, but should probably be incoorporate into LSP_control

> server contains the main localhost server class, for pulling data from Lidar and LSP programs

> read_lidar contains functinos to process saved lidar data. This may become deprecated if all data is pulled to local
> programs and saved together in a different format

> process_lidar contains a class to process lidar data

> main is a general program which in the end will perform central functions, but currently is quite basic

