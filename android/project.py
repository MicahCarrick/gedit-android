import os
import imp

class Project(object):

    def __init__(self, path):
        self.set_path(path)
    
    def get_project_name(self):
        # assumes there is NO trailing slash!
        return os.path.basename(self._path)
        
    def get_path(self):
        return self._path
        
    def set_path(self, path):
        if not os.path.exists(path):
            raise IOError("Android project directory does not exist: %s" % path)
        self._path = path
    
    def get_apk_filename(self, mode="debug"):
        """ Return the full filename to the projects APK file. """
        # join project path with "bin", project name, "-debug.apk"
        filename = "%s-%s.apk" % (self.get_project_name(), mode)
        return os.path.join(self._path, "bin", filename)
        
    def get_sdk_path(self):
        """ Return the path to the Android SDK defined in local.properties. """
        filename = os.path.join(self._path, "local.properties")
        if not os.path.exists(filename):
            raise IOError("Could not find local properties file: %s" % filename)
        for line in open(filename, "r"):
            if line[:1] == "#": continue
            if line[:7] == "sdk.dir":
                key, value = line.split("=", 1)
                if value:
                    return value.strip()
        return None
            
        
        
