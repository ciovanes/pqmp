from PyQt6.QtCore import QSettings

class RecentFilesManager():
    MAX_RECENT_FILES = 5

    def __init__(self):
        self.settings = QSettings("PQMP", "RecentFiles")
        self.recent_files = self.settings.value("recentFiles", [], str)

    def add_file(self, filepath):
        if filepath in self.recent_files:
            self.recent_files.remove(filepath)
        self.recent_files.insert(0, filepath)
        self.recent_files = self.recent_files[:self.MAX_RECENT_FILES]
        self.settings.setValue('recentFiles', self.recent_files)

    def get_recent_files(self):
        return self.recent_files

    def get_max_recent_files(self):
        return self.MAX_RECENT_FILES
