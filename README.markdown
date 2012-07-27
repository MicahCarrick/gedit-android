Gedit Android Development Plugin
================================

This plugin is still in early development. Check back later for a stable release.


Installation
------------

1. Download this repository by clicking the Downloads button at the top of the 
   github page or issue the following command in a terminal:

    git clone git://github.com/MicahCarrick/gedit-android.git

2. Copy the file `android.plugin` and the folder `android` to
   `~/.local/share/gedit/plugins/`.

3. Install and compile the GLib schema as root:
        cp /home/&lt;YOUR USER NAME&gt;/.local/share/gedit/plugins/android/data/org.gnome.gedit.plugins.android.gschema.xml /usr/share/glib-2.0/schemas/
        glib-compile-schemas /usr/share/glib-2.0/schemas/
            
3. Restart Gedit.

4. Activate the plugin in Gedit by choosing 'Edit > Preferences', the selecting
   the 'Plugins' tab, and checking the box next to 'Android Development'.

