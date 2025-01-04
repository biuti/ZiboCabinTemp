# ZiboCabinTemp for X-Plane 12
Simple Python script to get a feedback about cabin temperature in Zibo B737-800 modified and LevelUp B737NG Series.

## Features
- As soon as boarding starts, flight assistant will start to report passengers' complains about cabin temperature if it's far from comfort temperature selected in settings (default 21°C)

## Requirements
- MacOS 10.14, Windows 7 and Linux kernel 4.0 and above
- X-Plane 12.1.3 and above (not tested with previous versions, may work)
- pbuckner's [XPPython3 plugin](https://xppython3.readthedocs.io/en/latest/index.html)
- [Zibo B737-800 Modified](https://forums.x-plane.org/index.php?/forums/forum/384-zibo-b738-800-modified/) for X-Plane 12 **ver. 4.3** and above (**may be compatible with some previous versions**) or [LevelUp B737NG Series](https://forum.thresholdx.net/files/file/3865-levelup-737ng-series/) for X-Plane 12 **ver. U1**

> [!IMPORTANT]
> **I strongly suggest to install latest available version of the XPPython3 plugin.
Starting from ver. 4.3.0 it is not needed to install Python3 on your system, and all needed libraries are already installed, so it's a lot easier to manage.
\
Otherwise, in the very unfortunate case you stick with previous versions of the plugin, you'll need to download correct XPPython3 version according to your Python3 installed version.
\
Read [instructions](https://xppython3.readthedocs.io/en/latest/usage/installation_plugin.html) on the website**

## Installation
Just copy or move the file _PI_ZiboCabinTemp.py_ to the folder:

    X-Plane/Resources/plugins/PythonPlugins/