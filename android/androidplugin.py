import os
import logging
import re
import subprocess
from gi.repository import GObject, Gtk, Gedit, Gio, GdkPixbuf
from project import Project
from console import Console

logging.basicConfig()
LOG_LEVEL = logging.DEBUG
logger = logging.getLogger(__name__)
logger.setLevel(LOG_LEVEL)

SETTINGS_SCHEMA = "org.gnome.gedit.plugins.android"
DATA_DIR = os.path.join(os.path.dirname(__file__), 'data')
STOCK_SDK = "sdk-manager"
STOCK_AVD = "avd-manager"
STOCK_CONSOLE = "console"
STOCK_DEVICE = "device"
STOCK_EMULATOR = "emulator"

class AndroidPlugin(GObject.Object, Gedit.WindowActivatable):
    __gtype_name__ = "GeditAndroidPlugin"
    window = GObject.property(type=Gedit.Window)
    
    def __init__(self):
        GObject.Object.__init__(self)
        self._ui_merge_id = None
        self._console = None
        self._project = None
    
    def _add_console(self):
        """ Adds a widget to the bottom pane for command output. """
        self._console = Console()
        self._console.set_font(self._settings.get_string("console-font"))
        panel = self.window.get_bottom_panel()
        panel.add_item_with_stock_icon(self._console, "AndroidConsole", 
                                       "Console", STOCK_CONSOLE)
        
            
    def _add_ui(self):
        """ Merge the 'Android' menu into the gedit menubar. """
        ui_file = os.path.join(DATA_DIR, 'menu.ui')
        manager = self.window.get_ui_manager()
        
        # global actions are always sensitive
        self._global_actions = Gtk.ActionGroup("AndroidGlobal")
        self._global_actions.add_actions([
            ('Android', None, "_Android", None, None, None),
            ('AndroidNewProject', Gtk.STOCK_NEW, "_New Project...", 
                "<Shift><Control>N", "Start a new Android project.", 
                self.on_new_project_activate),
            ('AndroidOpenProject', Gtk.STOCK_OPEN, "_Open Project", 
                "<Shift><Control>O", "Open an existing Android project.", 
                self.on_open_project_activate),
            ('AndroidSdk', STOCK_SDK, "Android _SDK Manager", 
                None, "Launch the Android SDK manager.", 
                self.on_android_sdk_activate),
            ('AndroidAvdManager', STOCK_AVD, "_AVD Manager", 
                None, "Launch the Android AVD manager.", 
                self.on_android_avd_manager_activate),
        ])     
        manager.insert_action_group(self._global_actions)
        
        # project actions are sensitive when a project is open
        self._project_actions = Gtk.ActionGroup("AndroidProject")
        self._project_actions.add_actions([
            ('AndroidCloseProject', Gtk.STOCK_CLOSE, "_Close Project...", 
                "", "Close the current Android project.", 
                self.on_close_project_activate),
            ('AndroidRun', None, "_Run...", 
                "", "Run the current project in debug mode.", 
                self.on_run_activate),
        ])
        self._project_actions.set_sensitive(False)
        manager.insert_action_group(self._project_actions)   
        
        self._ui_merge_id = manager.add_ui_from_file(ui_file)
        manager.ensure_update()
    
    def build_project(self, mode="debug"):
        try:
            self._console.run("%s %s" % 
                              (self._settings.get_string("ant-command"), mode), 
                              self._project.get_path())
        except Exception as e:
            self.error_dialog(str(e))
            
    def close_project(self):
        self._project = None
        self._project_actions.set_sensitive(False)
    
    def do_activate(self):
        """ Plugin activates at startup and/or gedit preferences. """
        # make sure we can use settings
        schemas = Gio.Settings.list_schemas()
        if not SETTINGS_SCHEMA in schemas:
            self.error_dialog("Could not find settings schema:\n %s" % SETTINGS_SCHEMA)
            return
        self._settings = Gio.Settings.new(SETTINGS_SCHEMA)
        
        self._install_stock_icons()
        self._add_ui()
        self._add_console()

    def do_deactivate(self):
        """ Plugin deactivates at startup and/or gedit preferences. """
        self._settings = None
        self._remove_ui()
        self._remove_console()

    def do_update_state(self):
        pass
    
    def error_dialog(self, message):
        """ Display a very basic error dialog. """
        logger.warn(message)
        dialog = Gtk.MessageDialog(self.window,
                                   Gtk.DialogFlags.MODAL | 
                                   Gtk.DialogFlags.DESTROY_WITH_PARENT,
                                   Gtk.MessageType.ERROR, Gtk.ButtonsType.OK, 
                                   message)
        dialog.set_title("Android Development Plugin")
        dialog.run()
        dialog.destroy()
    
    def _get_builder(self, filename):
        builder = Gtk.Builder()
        try:
            builder.add_from_file(filename)
        except Exception as e:
            logger.error("Failed to load %s: %s." % (filename, str(e)))
            return None
        
        return builder
    
    def install_apk(self, device_serial):
        cwd = os.path.join(self._project.get_sdk_path(), "platform-tools")
        command = "%s -s %s install %s" % (os.path.join(cwd, "adb"), 
                                           device_serial, 
                                           self._project.get_apk_filename())
        try:
            self._console.run(command, cwd)
        except Exception as e:
            self.error_dialog(str(e))
        
    def _install_stock_icons(self):
        """ Register custom stock icons. """
        icons = (STOCK_AVD, STOCK_SDK, STOCK_CONSOLE, STOCK_DEVICE, STOCK_CONSOLE)
        factory = Gtk.IconFactory()
        for name in icons:
            filename = name + ".png"
            pixbuf = GdkPixbuf.Pixbuf.new_from_file(os.path.join(DATA_DIR, "icons", filename))
            iconset = Gtk.IconSet.new_from_pixbuf(pixbuf)
            factory.add(name, iconset)
        factory.add_default()

    def new_project(self, target, name, path, activity, package):
        """ Create and open a new Android project """
        command = "%s create project --target %s --name '%s' --path '%s'" \
                  " --activity %s --package %s" % (
                  self._settings.get_string("android-command"),
                  target, name, path, activity, package)
        try:
            self._console.run(command)
        except Exception as e:
            self.error_dialog(str(e))
            return
        
        self.open_project(path)
  
    def on_android_avd_manager_activate(self, action, data=None):
        """ Launch android AVD manager """
        command = "%s %s" % (self._settings.get_string("android-command"), "avd")
        os.system(command + " &")
        
    def on_android_sdk_activate(self, action, data=None):
        """ Launch android SDK manager """
        command = "%s %s" % (self._settings.get_string("android-command"), "sdk")
        os.system(command + " &")
    
    def on_close_project_activate(self, action, data=None):
        pass
    
    def on_new_project_activate(self, action, data=None):

        filename = os.path.join(DATA_DIR, 'dialogs.ui')
        builder = self._get_builder(filename)
        path = name = None
        dialog = builder.get_object('new_project_dialog')
        dialog.set_default_response(Gtk.ResponseType.OK)
        name_widget = builder.get_object("project_name")
        activity_widget = builder.get_object("project_activity")
        path_widget = builder.get_object("project_path")
        path_widget.set_current_folder(self._settings.get_string("default-project-path"))
        package_widget = builder.get_object("project_package")
        package_widget.set_text(self._settings.get_string("default-package-namespace"))
        
        # create the list of android build targets
        target_widget = builder.get_object("project_target")
        targets = self.parse_targets()
        model = Gtk.ListStore(GObject.TYPE_STRING, GObject.TYPE_STRING)
        for target in targets:
            if 'Name' in target:
                if 'API level' in target:
                    name = "%s (API Level %s)" % (target['Name'], target['API level'])
                else:
                    name = target['Name']
                model.append((target['id'], name))
        cell = Gtk.CellRendererText()
        target_widget.pack_start(cell, True)
        target_widget.add_attribute(cell, "text", 1)
        target_widget.set_model(model)
        target_widget.set_id_column(0)
        target_widget.set_active_id(self._settings.get_string("default-build-target"))
        # auto-fill package name using project name
        name_widget.connect("changed", self.on_project_name_entry_typing, 
                            (package_widget, activity_widget))
        
        # run the dialog
        response = dialog.run()
        if response == Gtk.ResponseType.OK:
            path = os.path.join(path_widget.get_filename(), name_widget.get_text())
            self.new_project(target_widget.get_active_id(),
                             name_widget.get_text(), 
                             path, 
                             activity_widget.get_text(), 
                             package_widget.get_text())
        dialog.destroy()
    
    def on_open_project_activate(self, action, data=None):
        path = None
        dialog = Gtk.FileChooserDialog("Select project folder...", self.window,
                                       Gtk.FileChooserAction.SELECT_FOLDER,
                                       (Gtk.STOCK_CANCEL, Gtk.ResponseType.CANCEL, 
                                        Gtk.STOCK_OPEN, Gtk.ResponseType.OK))
        dialog.set_current_folder(self._settings.get_string("default-project-path"))
        response = dialog.run()
        if response == Gtk.ResponseType.OK: 
            path = dialog.get_filename()
        dialog.destroy()
        if path:
            self.open_project(path)
        
    def on_project_name_entry_typing(self, entry, data):
        """
        If the user has not yet modified the default package namespace, then
        we auto-generate the remaining portion of the package using the project
        name.
        """
        package_entry, activity_entry = data
        namespace = self._settings.get_string("default-package-namespace")
        package = entry.get_text().lower()
        package = re.sub(r'\W+', '', package)
        package_entry.set_text("%s.%s" % (namespace, package))
        activity_entry.set_text(entry.get_text() + "Activity")
    
    def on_run_activate(self, entry, data=None):
        # pick a device
        device_serial = self.select_device_dialog()
        if device_serial:
            # build
            self.build_project()
        
            # install
            self.install_apk(device_serial)        
    
    def open_project(self, path):
        logger.debug("Opening project: %s" % path)
        if self._project:
            self.close_project()
        try:
            self._project = Project(path)
        except IOError as e:
            self.error_dialog("Could not open project: %s" % str(e))
            return
            
        self._project_actions.set_sensitive(True)
    
    def parse_devices(self):
        """
        Parse the list of Android devices from 'adb'. 
        """
        #command = self._settings.get_string("android-command")
        cwd = os.path.join(self._project.get_sdk_path(), "platform-tools")
        command = os.path.join(cwd, "adb")
        p = subprocess.Popen([command, "devices"], stdout=subprocess.PIPE, cwd=cwd)
        output, err = p.communicate()
        devices = []
        # TODO: skip any line beginning with * or "List"
        for line in output.splitlines(False)[1:]:
            device = line[:line.find("\t")].strip()
            if device:
                devices.append(device)
        return devices
        
    def parse_targets(self):
        """
        Parse the list of build targets from the 'android' tool and load them
        into a list of dicts containing the key value pairs. 
        """
        command = self._settings.get_string("android-command")
        p = subprocess.Popen([command, "list", "targets"], stdout=subprocess.PIPE)
        output, err = p.communicate()
        sep = "----------"
        targets = []
        current = {}
        for line in output.splitlines(False):
            if line == sep:
                targets.append(current)
                current = {}
                continue
            if line[:3] == "id:":
                current['id'] = line.split(" ")[1]
            elif 'id' in current:
                sliced = line.split(":", 1)
                if len(sliced) > 1:
                    key = sliced[0].strip()
                    current[key] = sliced[1].strip()
        targets.append(current) # don't forget last in list!

        return targets
    
    def _remove_console(self):
        """ Remove the output box from the bottom panel. """
        if self._console:
            panel = self.window.get_bottom_panel()
            panel.remove_item(self._console)
            self._console = None
            
    def _remove_ui(self):
        """ Remove the 'Android' menu from the the gedit menubar. """
        if self._ui_merge_id:
            manager = self.window.get_ui_manager()
            manager.remove_ui(self._ui_merge_id)
            manager.remove_action_group(self._global_actions)
            manager.remove_action_group(self._project_actions)
            manager.ensure_update()
    
    def select_device_dialog(self):
        """
        Presents a list of connected Android devices/emulators for the user
        to choose.
        """
        # create dialog from builder
        filename = os.path.join(DATA_DIR, 'dialogs.ui')
        builder = self._get_builder(filename)
        dialog = builder.get_object('device_selection_dialog')
        
        # icons for devices in the treeview
        icon_file = os.path.join(DATA_DIR, "icons", STOCK_DEVICE + ".png")
        device_pixbuf = GdkPixbuf.Pixbuf.new_from_file(icon_file)
        icon_file = os.path.join(DATA_DIR, "icons", STOCK_EMULATOR + ".png")
        emulator_pixbuf = GdkPixbuf.Pixbuf.new_from_file(icon_file)
        
        # build the treeview
        treeview = builder.get_object('device_treeview')
        devices = self.parse_devices()
        
        if not devices:
            self.error_dialog("Could not find any Android devices.\nUse the AVD Manager to start a virtual device or connect an Android device to the computer.")
            return None
        
        model = Gtk.ListStore(GdkPixbuf.Pixbuf, GObject.TYPE_STRING)
        for device in devices:
            if device[:8] == "emulator":
                model.append((emulator_pixbuf, device))
            else:
                model.append((device_pixbuf, device))
        treeview.set_model(model)
        column = Gtk.TreeViewColumn("Device")
        cell = Gtk.CellRendererPixbuf()
        column.pack_start(cell, False)
        column.add_attribute(cell, 'pixbuf', 0)
        cell = Gtk.CellRendererText()
        column.pack_start(cell, True)
        column.add_attribute(cell, 'text', 1)
        treeview.append_column(column)
        
        # run the dialog
        device_serial = None
        response = dialog.run()
        if response == Gtk.ResponseType.OK:
            # get selected device
            model, titer = treeview.get_selection().get_selected()
            device_serial = model.get_value(titer, 1)
        dialog.destroy()
        
        return device_serial
        
        
